"""Walk-forward backtest on historical Wallex candles.

* Model is re-trained only on data strictly before each test fold (+ embargo),
  so there is no look-ahead.
* Same features, same thresholds, same risk engine and exit rules as live.
* Entries fill at the NEXT bar's open + slippage with taker fee (pessimistic).
* The LLM agent is replaced by its documented fallback policy (fixed stricter
  threshold, 0.6x size); the full agent is evaluated in shadow mode.
"""
from __future__ import annotations

import json
import os
import logging

import numpy as np
import pandas as pd

from .features import FEATURES
from .model import SignalModel
from .risk import RiskManager, Position

log = logging.getLogger("backtest")


def run_backtest(frames: dict[str, pd.DataFrame], cfg: dict, universe: list[str], fee: float,
                 out_dir: str = "logs/backtest", train_days: float = 6.0, fold_days: float = 1.0,
                 slippage: float = 0.001, threshold_adj: float = 0.03, size_mult: float = 0.6,
                 seed: int = 42) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    mcfg, rcfg = cfg["model"], cfg["risk"]
    res = cfg["data"]["resolution_min"]
    cost = 2 * fee
    model = SignalModel(mcfg, cost, seed=seed)
    data = model.dataset(frames)
    if data.empty:
        raise ValueError("no data for backtest")
    data = data[data["symbol"].isin(universe)].copy()
    data["p"] = np.nan
    t0, t1 = data["t"].min(), data["t"].max()
    start = t0 + train_days * 86400
    embargo = mcfg["horizon_bars"] * res * 60
    folds = []
    fs = start
    while fs < t1:
        fe = min(t1 + 1, fs + fold_days * 86400)
        tr = data[data["t"] < fs - embargo]
        if len(tr) >= mcfg.get("min_train_samples", 1000) and tr["y"].nunique() > 1:
            clf = model._make().fit(tr[FEATURES], tr["y"].astype(int))
            mask = (data["t"] >= fs) & (data["t"] < fe)
            if mask.any():
                data.loc[mask, "p"] = clf.predict_proba(data.loc[mask, FEATURES])[:, 1]
                folds.append({"fold_start": int(fs), "n_train": len(tr), "n_test": int(mask.sum())})
        fs = fe

    # --------------------------------------------------- event-driven simulation
    test = data[data["t"] >= start]
    bars = {s: frames[s].set_index("t") for s in universe if s in frames}
    times = sorted(test["t"].unique())
    pmap = {(r.t, r.symbol): r.p for r in test[["t", "symbol", "p"]].itertuples()}
    ch = dict(cfg["challenge"])
    ch["end_time"] = pd.Timestamp(times[-1] + 10 * 86400, unit="s", tz="UTC").isoformat()
    risk = RiskManager(rcfg, ch)
    risk.breakeven_frac = cost + 0.001
    cash = float(cfg["challenge"]["initial_capital_tmn"])
    positions: dict[str, Position] = {}
    trades, curve = [], []
    th = mcfg["base_prob_threshold"] + threshold_adj
    max_hold = mcfg["horizon_bars"] * res * 60 * 1.5
    step = res * 60

    def mark(t):
        eq = cash
        for s, p in positions.items():
            b = bars[s]
            px = b["c"].get(t, np.nan)
            eq += p.qty * (px if px == px else p.entry_price)
        return eq

    for t in times:
        nxt = t + step
        # 1) exits evaluated on bar t (intrabar high/low)
        for s, pos in list(positions.items()):
            b = bars[s]
            if t not in b.index:
                continue
            hi, lo, cl = b.at[t, "h"], b.at[t, "l"], b.at[t, "c"]
            px = None
            if lo <= pos.sl_price:
                px, why = pos.sl_price * (1 - slippage), "stop_loss"
            elif hi >= pos.tp_price:
                px, why = pos.tp_price, "take_profit"
            else:
                why = risk.exit_reason(pos, cl, t, max_hold)
                if why:
                    px = cl * (1 - slippage)
            if px:
                proceeds = pos.qty * px * (1 - fee)
                cash += proceeds
                pnl = proceeds - pos.cost_tmn
                trades.append({"symbol": s, "entry_t": pos.entry_time, "exit_t": t, "entry": pos.entry_price,
                               "exit": px, "pnl_tmn": pnl, "pnl_pct": pnl / pos.cost_tmn * 100, "reason": why})
                if pnl < 0:
                    risk.on_loss_exit(s, t)
                del positions[s]
        eq = mark(t)
        risk.on_equity(eq, t)
        exposure = eq - cash
        curve.append({"t": t, "equity": eq, "exposure": exposure, "open": len(positions)})
        if risk.state.killed:
            continue
        # 2) entries: signal on close of t, fill at open of t+1
        cands = sorted(((pmap.get((t, s)), s) for s in universe
                        if pmap.get((t, s)) is not None and pmap.get((t, s)) == pmap.get((t, s))
                        and pmap.get((t, s)) >= th), reverse=True)
        for p, s in cands:
            ok, _ = risk.can_open(s, eq, exposure, len(positions), s in positions, t)
            if not ok or nxt not in bars[s].index:
                continue
            size = risk.size_tmn(eq, exposure, cash, p, th, size_mult, 1.0)
            if size < rcfg["min_order_tmn"]:
                continue
            px = bars[s].at[nxt, "o"] * (1 + slippage)
            qty = size / px * (1 - fee)
            cash -= size
            exposure += size
            positions[s] = Position(s, qty, px, nxt, size, px * (1 + mcfg["take_profit_pct"] / 100),
                                    px * (1 - mcfg["stop_loss_pct"] / 100), px)

    # close leftovers at last close (challenge rule: end in TMN)
    for s, pos in list(positions.items()):
        b = bars[s]
        px = b["c"].iloc[-1] * (1 - slippage)
        proceeds = pos.qty * px * (1 - fee)
        cash += proceeds
        trades.append({"symbol": s, "entry_t": pos.entry_time, "exit_t": int(b.index[-1]), "entry": pos.entry_price,
                       "exit": px, "pnl_tmn": proceeds - pos.cost_tmn,
                       "pnl_pct": (proceeds - pos.cost_tmn) / pos.cost_tmn * 100, "reason": "end_flatten"})
    curve_df = pd.DataFrame(curve)
    tr_df = pd.DataFrame(trades)
    init = cfg["challenge"]["initial_capital_tmn"]
    curve_df["peak"] = curve_df["equity"].cummax()
    curve_df["dd_pct"] = (1 - curve_df["equity"] / curve_df["peak"]) * 100
    days = (times[-1] - times[0]) / 86400 if len(times) > 1 else 0
    # baseline: equal-weight buy & hold of the universe over the same window
    bh = []
    for s in universe:
        b = bars[s]
        seg = b[(b.index >= times[0]) & (b.index <= times[-1])]["c"]
        if len(seg) > 1:
            bh.append(seg.iloc[-1] / seg.iloc[0] - 1)
    wins = tr_df[tr_df["pnl_tmn"] > 0] if not tr_df.empty else tr_df
    losses = tr_df[tr_df["pnl_tmn"] <= 0] if not tr_df.empty else tr_df
    r = curve_df["equity"].pct_change().dropna()
    summary = {
        "period_days": round(days, 2),
        "folds": len(folds),
        "final_equity_tmn": round(cash),
        "return_pct": round((cash / init - 1) * 100, 3),
        "return_per_3days_pct": round(((cash / init) ** (3 / days) - 1) * 100, 3) if days > 0 else None,
        "max_drawdown_pct": round(float(curve_df["dd_pct"].max()), 3),
        "trades": int(len(tr_df)),
        "trades_per_day": round(len(tr_df) / days, 2) if days else None,
        "win_rate_pct": round(len(wins) / len(tr_df) * 100, 2) if len(tr_df) else None,
        "avg_trade_pnl_pct": round(float(tr_df["pnl_pct"].mean()), 3) if len(tr_df) else None,
        "profit_factor": round(float(wins["pnl_tmn"].sum() / -losses["pnl_tmn"].sum()), 3)
        if len(losses) and losses["pnl_tmn"].sum() < 0 else None,
        "sharpe_per_bar_annualised": round(float(r.mean() / r.std() * np.sqrt(365 * 24 * 60 / res)), 3)
        if len(r) > 2 and r.std() > 0 else None,
        "exit_reasons": tr_df["reason"].value_counts().to_dict() if len(tr_df) else {},
        "buy_and_hold_equal_weight_pct": round(float(np.mean(bh)) * 100, 3) if bh else None,
        "threshold": th, "fee_per_side": fee, "slippage": slippage,
        "universe": universe,
    }
    curve_df.to_csv(os.path.join(out_dir, "equity_curve.csv"), index=False)
    tr_df.to_csv(os.path.join(out_dir, "trades.csv"), index=False)
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "folds": folds}, f, indent=2, default=str)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        x = pd.to_datetime(curve_df["t"], unit="s")
        ax[0].plot(x, curve_df["equity"] / init * 100 - 100, color="#1f6feb", lw=1.6, label="Strategy")
        ax[0].axhline(0, color="#888", lw=0.8)
        ax[0].set_ylabel("Return %")
        ax[0].set_title(f"Walk-forward backtest: {summary['return_pct']}% | maxDD {summary['max_drawdown_pct']}% | "
                        f"{summary['trades']} trades")
        ax[0].legend(loc="upper left")
        ax[1].fill_between(x, -curve_df["dd_pct"], 0, color="#d1242f", alpha=0.5)
        ax[1].set_ylabel("Drawdown %")
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "backtest.png"), dpi=130)
        plt.close(fig)
    except Exception as e:
        log.info("plot skipped: %s", e)
    return summary
