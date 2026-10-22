"""Backtest of the market maker (bot/mm_engine.py) on 1-minute candles.

Data: data/m1_tmn_*.json + data/m1_usdt_*.json — 2 days of real Wallex 1-minute bars (2026-10-20..22)
collected by the server probe for the 20 most active Toman markets and their USDT pairs.

Per minute, per market (same rules as the live engine, at candle resolution):
  FV      = COIN/USDT close x USDT/TMN close x (1 + 30-min median Toman premium)   [previous bar]
  bid     = FV x (1 - h - skew),  ask = max(FV x (1 + h - skew), cost x (1 + 2 maker fees + 10 bps))
  fill    = the bar trades THROUGH our price (low < bid, high > ask) and has volume
  guards  = no buying if FV fell > 0.4% in the last bar or the premium slid > 0.3% below its baseline
  exits   = stop-loss 1.2% below cost, time stop 90 min (taker, at the bar close minus 0.1%)
Limits of a candle backtest (both directions): queue position and the bid/ask bounce inside a minute
are invisible, and COIN/USDT closes are often stale (most USDT bars have no trade). The shadow test
with trade-tape fills is the real test; this backtest is a sanity check of the rules.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

MAKER, TAKER = 0.0025, 0.003


def load(tmn_path: str, usdt_path: str) -> dict[str, pd.DataFrame]:
    raw = json.load(open(tmn_path))
    raw.update(json.load(open(usdt_path)))
    return {s: pd.DataFrame({k: d[k] for k in "ohlcv"}, index=np.array(d["t"], dtype="int64")) for s, d in raw.items()}


def simulate(fr: dict[str, pd.DataFrame], coin: str, h: float, quote_tmn=900_000.0, stop=0.012, max_hold=90,
             skew_k=0.5, max_inv=1_250_000.0):
    u = fr["USDTTMN"]
    t = fr[f"{coin}TMN"].reindex(u.index).ffill()
    tv = fr[f"{coin}TMN"]["v"].reindex(u.index).fillna(0).to_numpy()
    cu = fr[f"{coin}USDT"].reindex(u.index).ffill()
    fv_u = (cu["c"] * u["c"]).to_numpy()
    prem = (t["c"].to_numpy() / fv_u - 1)
    prem_med = pd.Series(np.where(np.abs(prem) < 0.05, prem, np.nan)).rolling(30, min_periods=5).median().to_numpy()
    lo, hi, cl = t["l"].to_numpy(), t["h"].to_numpy(), t["c"].to_numpy()
    qty = cost = 0.0
    t0 = 0
    trips, eq_curve, pnl = [], [], 0.0
    for i in range(32, len(u) - 1):
        if not np.isfinite(fv_u[i - 1]) or not np.isfinite(prem_med[i - 1]):
            continue
        fv = fv_u[i - 1] * (1 + prem_med[i - 1])
        inv_val = qty * fv
        skew = min(1.0, inv_val / max_inv) * h * skew_k
        # exits first (taker)
        if qty > 0 and (fv < cost / qty * (1 - stop) or i - t0 >= max_hold):
            proceeds = qty * cl[i] * 0.999 * (1 - TAKER)
            trips.append(proceeds / cost - 1)
            pnl += proceeds - cost
            qty = cost = 0.0
            continue
        # sell
        if qty > 0 and tv[i] > 0:
            ask = max(fv * (1 + h - skew), cost / qty * (1 + 2 * MAKER + 0.001))
            if hi[i] > ask:
                proceeds = qty * ask * (1 - MAKER)
                trips.append(proceeds / cost - 1)
                pnl += proceeds - cost
                qty = cost = 0.0
        # buy (guards)
        falling = np.isfinite(fv_u[i - 2]) and fv_u[i - 1] / fv_u[i - 2] - 1 < -0.004
        sliding = prem[i - 1] < prem_med[i - 1] - 0.003
        if not falling and not sliding and inv_val < max_inv - 100_000 and tv[i] > 0:
            bid = fv * (1 - h - skew)
            if lo[i] < bid:
                if qty == 0:
                    t0 = i
                q = min(quote_tmn, max_inv - inv_val) / bid
                qty += q * (1 - MAKER)
                cost += q * bid
        eq_curve.append(pnl + (qty * cl[i] - cost if qty else 0.0))
    return np.array(trips), np.array(eq_curve)


def run_mm_backtest(tmn_path: str, usdt_path: str, out_dir="logs/backtest_mm", hs=(0.005, 0.007, 0.01, 0.013)):
    os.makedirs(out_dir, exist_ok=True)
    fr = load(tmn_path, usdt_path)
    coins = sorted(s[:-3] for s in fr if s.endswith("TMN") and s != "USDTTMN" and f"{s[:-3]}USDT" in fr)
    days = len(fr["USDTTMN"]) / 1440
    rows, per_coin = [], {}
    for h in hs:
        all_trips, total = [], 0.0
        for co in coins:
            trips, eq = simulate(fr, co, h)
            all_trips += list(trips)
            total += eq[-1] if len(eq) else 0.0
            per_coin.setdefault(co, {})[f"h={h*100:.1f}%"] = {"round_trips": len(trips),
                                                              "avg_bps": round(float(trips.mean()) * 1e4, 1) if len(trips) else None}
        tr = np.array(all_trips)
        rows.append({"half_spread_pct": h * 100, "round_trips": len(tr),
                     "round_trips_per_day": round(len(tr) / days, 1),
                     "avg_net_bps": round(float(tr.mean()) * 1e4, 1) if len(tr) else None,
                     "win_rate_pct": round(float((tr > 0).mean()) * 100, 1) if len(tr) else None,
                     "pnl_tmn_all_markets": round(total)})
    summary = {"data_days": round(days, 2), "markets": coins, "by_half_spread": rows, "per_market": per_coin,
               "caveat": "candle resolution: no queue, no intra-minute bounce, stale USDT closes; shadow test decides"}
    json.dump(summary, open(os.path.join(out_dir, "mm_summary.json"), "w"), indent=2, ensure_ascii=False)
    return summary
