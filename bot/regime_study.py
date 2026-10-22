"""Backtest of the holding sleeves (rial / beta) and of the 3-strategy portfolio on hourly Wallex data.

    python run.py regime-study

Data: data/hourly.json — 29 days of hourly Toman prices (USDT and 13 coins), shipped with the repo.
Every hour a 27-hour holding window starts (the time left in the challenge when the portfolio went live).
A sleeve is entered only under the regime rule of the live engine (USDT/TMN 48 h change >= +1% ->
full, 0..1% -> half, < 0 -> none), pays 0.25% to enter (maker) and 0.30% to leave (taker), and is
checked hourly against its stop-loss and trailing stop (same parameters as config.yaml). The market-
maker third is counted at 0% (the order-book backtest put it between -0.3% and +0.4% at h 0.7-1.0%).
Windows overlap, so the effective sample is small (~29 days, a few independent regime episodes).
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ENTRY, EXIT = 0.0025, 0.003


def load_hourly(path="data/hourly.json") -> pd.DataFrame:
    h = json.load(open(path))
    out = {}
    for s, d in h.items():
        if s.endswith("TMN"):
            t = pd.to_datetime(d["t0"] + np.array(d["t"]) * 3600, unit="s")
            out[s[:-3]] = pd.Series(d["c"], index=t)
    return pd.DataFrame(out).ffill()


def sleeve_path(px, i, weights, hours, stop, trail_start, trail_gap):
    """Return of a sleeve entered at hour i and held up to `hours`, with hourly stop checks."""
    w = {a: x for a, x in weights.items() if a in px.columns and x > 0}
    tot = sum(w.values())
    base = px.iloc[i]
    peak = 0.0
    r = 0.0
    for k in range(1, hours + 1):
        if i + k >= len(px):
            return None
        r = sum(x / tot * (px[a].iloc[i + k] / base[a] - 1) for a, x in w.items())
        peak = max(peak, r)
        if r < -stop or (peak >= trail_start and r <= peak - trail_gap):
            break
    return (1 + r) * (1 - ENTRY) * (1 - EXIT) - 1


def run_regime_study(cfg: dict, out_dir="logs/regime_study", hours=27):
    os.makedirs(out_dir, exist_ok=True)
    px = load_hourly()
    pf = cfg["portfolio"]
    usd48 = px["USDT"] / px["USDT"].shift(48) - 1
    sl = pf["sleeves"]
    rows = {"rial": [], "beta": [], "portfolio": [], "rial_always": [], "beta_always": []}
    for i in range(48, len(px) - hours):
        g = usd48.iloc[i]
        cap = 1.0 if g >= pf["regime_full_pct"] / 100 else (0.5 if g >= pf["regime_half_pct"] / 100 else 0.0)
        res = {}
        for name in ("rial", "beta"):
            s = sl[name]
            r = sleeve_path(px, i, s["assets"], hours, s["stop_pct"] / 100, s["trail_start_pct"] / 100,
                            s["trail_gap_pct"] / 100)
            if r is None:
                continue
            rows[f"{name}_always"].append(r)
            res[name] = r * cap
            rows[name].append(r * cap)
        if len(res) == 2:
            rows["portfolio"].append((res["rial"] + res["beta"]) * 0.33)     # MM third counted at 0
    summary = {}
    for k, v in rows.items():
        a = np.array(v)
        summary[k] = {"windows": len(a), "mean_pct": round(float(a.mean()) * 100, 2),
                      "median_pct": round(float(np.median(a)) * 100, 2),
                      "p_loss_pct": round(float((a < 0).mean()) * 100), "p10_pct": round(float(np.percentile(a, 10)) * 100, 2),
                      "worst_pct": round(float(a.min()) * 100, 2), "best_pct": round(float(a.max()) * 100, 2)}
    out = {"hours_held": hours, "data": f"{px.index[0]:%Y-%m-%d} .. {px.index[-1]:%Y-%m-%d}", "results": summary,
           "notes": "rial/beta = regime-gated sleeve return; *_always = without the regime rule; portfolio = "
                    "1/3 rial + 1/3 beta + 1/3 market maker at 0%, as a share of total capital; net of fees"}
    json.dump(out, open(os.path.join(out_dir, "regime_summary.json"), "w"), indent=2)
    return out
