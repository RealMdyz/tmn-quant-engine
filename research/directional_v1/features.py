"""Feature engineering + triple-barrier labelling.

All features are scale-free (returns, ratios, z-scores) so one model can be
trained on several TMN markets pooled together.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = [
    "r1", "r3", "r6", "r12", "r24", "r48",
    "vol12", "vol48", "vol_ratio",
    "rsi14", "ema20_dist", "ema50_dist", "ema_slope20",
    "bb_z20", "range_pos48", "hl_range", "macd_hist",
    "vlm_ratio", "vlm_trend",
    "hour_sin", "hour_cos",
    "mkt_r6", "mkt_r12", "usdt_r12",
]


def candles_to_df(c: dict) -> pd.DataFrame:
    df = pd.DataFrame({"t": c["t"], "o": c["o"], "h": c["h"], "l": c["l"],
                       "c": c["c"], "v": c["v"]})
    if df.empty:
        return df
    df["t"] = df["t"].astype("int64")
    df = df.drop_duplicates("t").sort_values("t").reset_index(drop=True)
    df = df[(df["c"] > 0) & (df["h"] > 0) & (df["l"] > 0)]
    return df.reset_index(drop=True)


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def build_features(df: pd.DataFrame, market_df: pd.DataFrame | None = None,
                   usdt_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """df: one symbol's candles. market_df: BTCTMN candles (market factor).
    usdt_df: USDTTMN candles (Toman/dollar factor)."""
    out = df.copy()
    c = out["c"]
    lr = np.log(c).diff()
    for n in (1, 3, 6, 12, 24, 48):
        out[f"r{n}"] = np.log(c / c.shift(n))
    out["vol12"] = lr.rolling(12).std()
    out["vol48"] = lr.rolling(48).std()
    out["vol_ratio"] = out["vol12"] / out["vol48"].replace(0, np.nan)
    out["rsi14"] = _rsi(c) / 100.0
    ema20 = c.ewm(span=20, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()
    out["ema20_dist"] = c / ema20 - 1
    out["ema50_dist"] = c / ema50 - 1
    out["ema_slope20"] = ema20 / ema20.shift(6) - 1
    ma20 = c.rolling(20).mean()
    sd20 = c.rolling(20).std()
    out["bb_z20"] = (c - ma20) / sd20.replace(0, np.nan)
    hh = out["h"].rolling(48).max()
    ll = out["l"].rolling(48).min()
    out["range_pos48"] = (c - ll) / (hh - ll).replace(0, np.nan)
    out["hl_range"] = (out["h"] - out["l"]) / c
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd_hist"] = (macd - macd.ewm(span=9, adjust=False).mean()) / c
    vq = out["v"] * c
    out["vlm_ratio"] = vq / vq.rolling(48).mean().replace(0, np.nan)
    out["vlm_trend"] = vq.rolling(6).mean() / vq.rolling(48).mean().replace(0, np.nan)
    hour = ((out["t"] + 3.5 * 3600) // 3600) % 24  # Tehran hour
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    def _factor(fdf, n):
        if fdf is None or fdf.empty:
            return pd.Series(0.0, index=out.index)
        s = np.log(fdf.set_index("t")["c"]).diff(n)
        return out["t"].map(s).astype(float).fillna(0.0)

    out["mkt_r6"] = _factor(market_df, 6)
    out["mkt_r12"] = _factor(market_df, 12)
    out["usdt_r12"] = _factor(usdt_df, 12)
    out[FEATURES] = out[FEATURES].replace([np.inf, -np.inf], np.nan)
    return out


def triple_barrier_labels(df: pd.DataFrame, horizon: int, tp: float, sl: float,
                          cost: float) -> pd.Series:
    """1 if price hits +tp before -sl within `horizon` bars (entry at close),
    else 0. If neither barrier is hit, 1 only if the final return beats `cost`.
    Same-bar double touch is labelled 0 (conservative). tp/sl/cost are fractions."""
    c = df["c"].to_numpy()
    h = df["h"].to_numpy()
    l = df["l"].to_numpy()
    n = len(df)
    y = np.full(n, np.nan)
    for i in range(n - horizon):
        e = c[i]
        up, dn = e * (1 + tp), e * (1 - sl)
        lab = None
        for j in range(i + 1, i + horizon + 1):
            hit_up, hit_dn = h[j] >= up, l[j] <= dn
            if hit_dn:
                lab = 0
                break
            if hit_up:
                lab = 1
                break
        if lab is None:
            lab = 1 if c[i + horizon] / e - 1 > cost else 0
        y[i] = lab
    return pd.Series(y, index=df.index)
