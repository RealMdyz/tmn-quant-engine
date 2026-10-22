"""Backtest of the market maker on REAL 10-second order-book snapshots recorded by the server.

Data: data/books_10s_*.csv — top of book (best bid/ask) of every COIN/TMN, COIN/USDT and USDT/TMN
market every 10 s, recorded live on 2026-10-22 (arbitrage-engine file 12:34-14:17, market-maker file
from 14:29). Unlike 1-minute candles this sees the real bid/ask, so the spread rule can be tested.

Same rules as bot/mm_engine.py, per market, at 10-second resolution:
  FV        = mid(COIN/USDT) x mid(USDT/TMN) x (1 + 30-min median Toman premium)
  bid       = min(FV x (1 - h - skew), best bid)            [we join the best bid]
  ask       = max(FV x (1 + h - skew), best ask, cost x (1 + 2 maker fees + 10 bps))  [break-even after 30 min]
  guards    = no buying if FV fell > 0.4% in 60 s, or the premium slid 0.3% under its baseline in 2 min
  spread    = (optional) no buying while best ask / best bid - 1 < min_spread
  exits     = stop-loss 1.2% under cost, time stop 90 min: taker sell at the best bid
Fill model (deliberately PESSIMISTIC for profit):
  our bid fills if the NEXT snapshot's best bid is below it (sellers went through our price, the adverse
  case, always counted) or its best ask is at/below it; our ask fills ONLY if the next best BID is at/above
  it. A best ask that merely moves up is not a fill: thin books flicker as other bots cancel and re-place
  (the loose model that counted it showed an impossible +15% in 4 hours). Benign fills at an unchanged
  touch are not counted, so this is a lower bound on the strategy.
"""
from __future__ import annotations

import io
import json
import os

import numpy as np
import pandas as pd

MAKER, TAKER = 0.0025, 0.003


def load_books(paths: list[str]) -> list[pd.DataFrame]:
    out = []
    for p in paths:
        lines = open(p, encoding="utf-8").read().splitlines()
        hdr = lines[0].split(",")
        ok = [x for x in lines[1:] if len(x.split(",")) == len(hdr)]
        df = pd.read_csv(io.StringIO("\n".join([lines[0]] + ok))).apply(pd.to_numeric, errors="coerce")
        out.append(df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True))
    return out


def simulate(b: pd.DataFrame, coin: str, h: float, min_spread: float | None, quote=900_000.0,
             max_inv=1_250_000.0, stop=0.012, max_hold_s=5400, skew_k=0.5, strict=True):
    tb, ta = b[f"{coin}TMN_bid"].to_numpy(), b[f"{coin}TMN_ask"].to_numpy()
    ub, ua = b[f"{coin}USDT_bid"].to_numpy(), b[f"{coin}USDT_ask"].to_numpy()
    ut = ((b["USDTTMN_bid"] + b["USDTTMN_ask"]) / 2).to_numpy()
    ts = b["ts"].to_numpy()
    fv_u = (ub + ua) / 2 * ut
    prem = ((tb + ta) / 2) / fv_u - 1
    prem = np.where(np.abs(prem) < 0.05, prem, np.nan)
    pm = pd.Series(prem).rolling(180, min_periods=6).median().to_numpy()
    pmin2 = pd.Series(prem).rolling(12, min_periods=1).min().to_numpy()
    fv = fv_u * (1 + pm)
    qty = cost = 0.0
    t0 = 0.0
    trips, buys, n_block_spread = [], 0, 0
    mark = []
    for i in range(7, len(ts) - 1):
        if not (np.isfinite(fv[i]) and np.isfinite(tb[i]) and np.isfinite(ta[i]) and tb[i] > 0):
            continue
        if ts[i + 1] - ts[i] > 30:                         # gap in the recording
            continue
        inv_val = qty * fv[i]
        skew = min(1.0, inv_val / max_inv) * h * skew_k
        # exits
        if qty > 0 and (fv[i] < cost / qty * (1 - stop) or ts[i] - t0 > max_hold_s):
            proceeds = qty * tb[i] * (1 - TAKER)
            trips.append(("exit", proceeds / cost - 1, proceeds - cost))
            qty = cost = 0.0
            continue
        # sell side
        if qty > 0:
            floor = cost / qty * (1 + 2 * MAKER + (0.001 if ts[i] - t0 < 1800 else 0))
            ask = max(fv[i] * (1 + h - skew), ta[i], floor)
            # strict: only when buyers themselves bid at/above our ask (a moving best ask can be a cancel)
            if tb[i + 1] >= ask or (not strict and ta[i + 1] > ask):
                proceeds = qty * ask * (1 - MAKER)
                trips.append(("maker", proceeds / cost - 1, proceeds - cost))
                qty = cost = 0.0
        # buy side
        falling = np.isfinite(fv[i - 6]) and fv[i] / fv[i - 6] - 1 < -0.004
        sliding = np.isfinite(pm[i]) and pmin2[i] < pm[i] - 0.003
        spread = ta[i] / tb[i] - 1
        if min_spread is not None and spread < min_spread:
            n_block_spread += 1
            continue
        if not falling and not sliding and inv_val < max_inv - 100_000:
            bid = min(fv[i] * (1 - h - skew), tb[i])
            if tb[i + 1] < bid or ta[i + 1] <= bid:
                q = min(quote, max_inv - inv_val) / bid
                if qty == 0:
                    t0 = ts[i]
                qty += q * (1 - MAKER)
                cost += q * bid
                buys += 1
        mark.append(qty * tb[i] - cost if qty else 0.0)
    unreal = (qty * tb[-1] * (1 - TAKER) - cost) if qty else 0.0
    return trips, buys, unreal, n_block_spread


def run_book_backtest(paths: list[str], out_dir="logs/backtest_book", hs=(0.002, 0.003, 0.005, 0.007, 0.01),
                      min_spread=0.005, strict=True):
    os.makedirs(out_dir, exist_ok=True)
    frames = load_books(paths)
    hours = sum((f.ts.max() - f.ts.min()) / 3600 for f in frames)
    rows, per_coin = [], {}
    for h in hs:
        for rule in (None, min_spread):
            trips, buys, pnl, unreal = [], 0, 0.0, 0.0
            for b in frames:
                coins = sorted(c[:-7] for c in b.columns if c.endswith("TMN_bid") and c != "USDTTMN_bid"
                               and f"{c[:-7]}USDT_bid" in b.columns)
                for co in coins:
                    tr, nb, ur, _ = simulate(b, co, h, rule, strict=strict)
                    trips += tr
                    buys += nb
                    pnl += sum(x[2] for x in tr)
                    unreal += ur
                    if rule is not None and abs(h - 0.003) < 1e-9:
                        pc = per_coin.setdefault(co, {"trips": 0, "pnl": 0.0})
                        pc["trips"] += len(tr)
                        pc["pnl"] += sum(x[2] for x in tr) + ur
            r = np.array([x[1] for x in trips]) if trips else np.array([])
            mk = [x for x in trips if x[0] == "maker"]
            rows.append({"half_spread_pct": round(h * 100, 2), "spread_rule": f">= {min_spread*1e4:.0f} bps" if rule else "off",
                         "buy_fills": buys, "round_trips": len(trips), "maker_exits": len(mk),
                         "risk_exits": len(trips) - len(mk),
                         "avg_round_trip_bps": round(float(r.mean()) * 1e4, 1) if len(r) else None,
                         "win_rate_pct": round(float((r > 0).mean()) * 100, 1) if len(r) else None,
                         "pnl_tmn": round(pnl + unreal), "pnl_pct_of_5m": round((pnl + unreal) / 5e6 * 100, 3)})
    summary = {"hours_of_data": round(hours, 2), "files": paths, "by_setting": rows,
               "per_market_h0.3_rule_on": {k: {"trips": v["trips"], "pnl_tmn": round(v["pnl"])} for k, v in
                                          sorted(per_coin.items(), key=lambda kv: kv[1]["pnl"])},
               "fill_model": ("strict: a bid fills when the next best bid drops below it or the best ask reaches it "
                              "(adverse fills always counted); an ask fills only when the next best BID reaches it"
                              if strict else "loose: a moving best ask also counts as a fill (flicker-prone)")}
    json.dump(summary, open(os.path.join(out_dir, "book_summary.json"), "w"), indent=2, ensure_ascii=False)
    return summary
