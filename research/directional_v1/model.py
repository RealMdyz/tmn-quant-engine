"""ML signal model: gradient-boosted trees predicting P(take-profit before stop-loss).

Trained on pooled TMN markets with walk-forward validation. The model is the
quantitative "eyes" of the system; the LLM agent sits on top as the policy layer.
"""
from __future__ import annotations

import json
import time
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from .features import FEATURES, build_features, triple_barrier_labels

log = logging.getLogger("model")


@dataclass
class ModelReport:
    trained_at: float = 0.0
    n_train: int = 0
    n_valid: int = 0
    base_rate: float = 0.0
    valid_auc: float = float("nan")
    precision_at_threshold: dict = field(default_factory=dict)
    feature_importance: dict = field(default_factory=dict)

    def to_dict(self):
        return self.__dict__.copy()


class SignalModel:
    def __init__(self, cfg: dict, cost_frac: float, seed: int = 42):
        self.cfg = cfg
        self.cost = cost_frac
        self.seed = seed
        self.clf: HistGradientBoostingClassifier | None = None
        self.report = ModelReport()

    def _make(self):
        return HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=250, min_samples_leaf=60,
            l2_regularization=1.0, random_state=self.seed)

    def dataset(self, frames: dict[str, pd.DataFrame], market_sym: str = "BTCTMN",
                usdt_sym: str = "USDTTMN") -> pd.DataFrame:
        m = self.cfg
        mk = frames.get(market_sym)
        us = frames.get(usdt_sym)
        parts = []
        for sym, df in frames.items():
            if len(df) < 120:
                continue
            f = build_features(df, None if sym == market_sym else mk,
                               None if sym == usdt_sym else us)
            f["y"] = triple_barrier_labels(df, m["horizon_bars"], m["take_profit_pct"] / 100,
                                           m["stop_loss_pct"] / 100, self.cost)
            f["symbol"] = sym
            parts.append(f)
        if not parts:
            return pd.DataFrame()
        data = pd.concat(parts, ignore_index=True)
        data = data.dropna(subset=FEATURES + ["y"])
        return data.sort_values("t").reset_index(drop=True)

    def fit(self, data: pd.DataFrame, valid_frac: float = 0.25) -> ModelReport:
        if len(data) < self.cfg.get("min_train_samples", 1000):
            raise ValueError(f"not enough samples to train: {len(data)}")
        # time-based split (no shuffling -> no look-ahead)
        cut_t = data["t"].quantile(1 - valid_frac)
        # embargo: drop training rows whose label window overlaps validation
        embargo = self.cfg["horizon_bars"] * 300
        tr = data[data["t"] < cut_t - embargo]
        va = data[data["t"] >= cut_t]
        clf = self._make().fit(tr[FEATURES], tr["y"].astype(int))
        p = clf.predict_proba(va[FEATURES])[:, 1]
        rep = ModelReport(trained_at=time.time(), n_train=len(tr), n_valid=len(va),
                          base_rate=float(va["y"].mean()))
        if va["y"].nunique() > 1:
            rep.valid_auc = float(roc_auc_score(va["y"], p))
        for th in (0.5, 0.55, 0.58, 0.6, 0.65, 0.7):
            sel = p >= th
            rep.precision_at_threshold[str(th)] = {
                "n": int(sel.sum()),
                "precision": float(va["y"][sel].mean()) if sel.sum() else None}
        # final model on all data (validation was only for reporting/threshold choice)
        self.clf = self._make().fit(data[FEATURES], data["y"].astype(int))
        try:
            from sklearn.inspection import permutation_importance
            sub = va.sample(min(len(va), 3000), random_state=self.seed)
            pi = permutation_importance(clf, sub[FEATURES], sub["y"].astype(int),
                                        n_repeats=3, random_state=self.seed, scoring="roc_auc")
            imp = dict(zip(FEATURES, pi.importances_mean))
            rep.feature_importance = {k: round(float(v), 4) for k, v in
                                      sorted(imp.items(), key=lambda kv: -kv[1])[:10]}
        except Exception as e:  # importance is cosmetic
            log.debug("importance failed: %s", e)
        self.report = rep
        log.info("model trained: %s", json.dumps(rep.to_dict(), default=str)[:400])
        return rep

    def predict_latest(self, feats: pd.DataFrame) -> float | None:
        if self.clf is None or feats.empty:
            return None
        row = feats[FEATURES].iloc[[-1]]
        if row.isna().any(axis=None):
            return None
        return float(self.clf.predict_proba(row)[:, 1][0])

    def predict_frame(self, feats: pd.DataFrame) -> np.ndarray:
        X = feats[FEATURES]
        ok = ~X.isna().any(axis=1)
        p = np.full(len(feats), np.nan)
        if self.clf is not None and ok.any():
            p[ok.to_numpy()] = self.clf.predict_proba(X[ok])[:, 1]
        return p
