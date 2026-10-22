"""Walk-forward backtest of the hedged fair-value arbitrage on 5-minute candles.

Correction (2026-10-22): the Wallex coin/USDT books are thin — most 5-minute bars have NO trade, so
their candle close is a price from tens of minutes earlier. The first version of this backtest also
priced the HEDGE at that stale close, i.e. it sold at a price that no longer existed right after the
crash that filled us. That artefact produced the +21/+39 bps, 80-90% win numbers. Hedging at the next
REAL coin/USDT trade instead, the same fills lose 60-70 bps on average at 0.4-1.3% margins.

Model now (pessimistic where data is missing):
  * our resting bid on XTMN is set from the PREVIOUS bar's fair value (coinUSDT close x USDTTMN close)
  * it only counts as filled if the Toman low trades THROUGH it by 0.1%
  * FLASH-DIP GUARD (as in the live engine): only quote while the Toman price was not already below
    fair value (previous bar close >= FV x (1 - calm_min_dev)); a Toman book that is already sliding is
    informed selling, not a hasty seller
  * the hedge is priced at the FIRST bar (this one or later, max 2h) in which coin/USDT really traded,
    at the worse of that bar's close and low, times USDTTMN at the same bar; no real trade -> no fill
  * full fees on every leg (maker entry, taker hedge, taker conversion); one fill per 15-min episode

Walk-forward: the margin per market is chosen on the first half (train) and evaluated on the second
half (test) so the reported test result is out-of-sample.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from .arb import Fees

MARGINS = [0.013, 0.020, 0.030, 0.040]
CALM_MIN_DEV = 0.002          # previous Toman close must be >= FV * (1 - 0.2%)
EPISODE_BARS = 3              # count at most one fill per 15 minutes per market/margin
HEDGE_LOOKAHEAD = 24          # bars (2h) to find the next real coin/USDT trade


def fills_table(frames: dict[str, pd.DataFrame], coins: list[str], fees: Fees) -> pd.DataFrame:
    u = frames["USDTTMN"]
    rows = []
    cost = fees.round_trip
    uc, ul = u["c"].to_numpy(), u["l"].to_numpy()
    for co in coins:
        if f"{co}TMN" not in frames or f"{co}USDT" not in frames:
            continue
        t = frames[f"{co}TMN"].reindex(u.index).ffill()
        cu = frames[f"{co}USDT"].reindex(u.index)
        cu_v = cu["v"].fillna(0).to_numpy()
        cu = cu.ffill()
        tl, tc = t["l"].to_numpy(), t["c"].to_numpy()
        tvq = (t["v"] * t["c"]).to_numpy()          # Toman volume traded in the bar
        cuc, cul = cu["c"].to_numpy(), cu["l"].to_numpy()
        n = len(uc)
        for m in MARGINS:
            i = 1
            while i < n - 1:
                fv = cuc[i - 1] * uc[i - 1]
                if not np.isfinite(fv) or tc[i - 1] < fv * (1 - CALM_MIN_DEV):
                    i += 1
                    continue
                bid = fv * (1 - cost - m)
                if tl[i] <= bid * 0.999:
                    j = next((k for k in range(i, min(n, i + HEDGE_LOOKAHEAD)) if cu_v[k] > 0), None)
                    if j is not None:
                        h = min(cuc[j], cul[j]) * min(uc[j], ul[j])
                        r = h * (1 - fees.usdt_taker) * (1 - fees.tmn_taker) / (bid / (1 - fees.tmn_maker)) - 1
                        rows.append({"coin": co, "margin": m, "i": i, "t": int(u.index[i]), "r": r,
                                     "bar_vol_tmn": float(tvq[i]), "hedge_wait_bars": j - i})
                    i += EPISODE_BARS
                else:
                    i += 1
    return pd.DataFrame(rows, columns=["coin", "margin", "i", "t", "r", "bar_vol_tmn", "hedge_wait_bars"])


def run_arb_backtest(frames: dict[str, pd.DataFrame], coins: list[str], fees: Fees,
                     capital: float = 5_000_000, quote_tmn: float = 1_000_000,
                     out_dir: str = "logs/backtest", min_edge_bps: float = 10.0) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    ft = fills_table(frames, coins, fees)
    n_bars = len(frames["USDTTMN"])
    half = n_bars // 2
    days = n_bars * 5 / 1440
    tr, te = ft[ft.i < half], ft[ft.i >= half]

    # pooled stats per margin over ALL coins (per-coin samples are far too small to trust): used as
    # the bandits' default prior -> [margin %, mean net bps per fill, fills per coin per 10 days]
    n_coins = max(1, ft.coin.nunique()) if len(ft) else 1
    pooled = ft.groupby("margin").r.agg(["count", "mean"]).reset_index() if len(ft) else pd.DataFrame()
    priors = {"_pooled": [[round(m * 100, 2), round(mu * 1e4, 1), round(c * 10 / days / n_coins, 2)]
                          for m, c, mu in zip(pooled.margin, pooled["count"], pooled["mean"])] if len(pooled) else []}

    # walk-forward: pick the smallest margin with mean > min_edge on TRAIN, apply on TEST
    choice = {}
    for co, g in tr.groupby(["coin", "margin"]).r.mean().reset_index().groupby("coin"):
        ok = g[g.r > min_edge_bps / 1e4]
        if len(ok):
            choice[co] = float(ok.sort_values("margin").iloc[0].margin)

    def portfolio(sub: pd.DataFrame, start_i: int, end_i: int):
        sel = sub[sub.apply(lambda r: choice.get(r.coin) == r.margin, axis=1)] if len(sub) else sub
        eq = capital
        curve = []
        by_i = (sel.groupby("i")[["r", "bar_vol_tmn"]].apply(lambda g: list(zip(g.r, g.bar_vol_tmn))).to_dict()
                if len(sel) else {})
        for i in range(start_i, end_i):
            for r, vol in by_i.get(i, []):
                # we can only buy what was actually sold in that bar: cap at 25% of the bar's Toman volume
                size = min(quote_tmn, eq / max(1, len(choice)), 0.25 * vol)
                eq += size * r
            curve.append(eq)
        curve = np.array(curve) if curve else np.array([capital])
        peak = np.maximum.accumulate(curve)
        return sel, curve, float(((peak - curve) / peak).max() * 100)

    sel_te, curve_te, dd_te = portfolio(te, half, n_bars)
    test_days = (n_bars - half) * 5 / 1440
    summary = {
        "data_days": round(days, 2),
        "fees": fees.__dict__, "round_trip_cost_pct": round(fees.round_trip * 100, 3),
        "chosen_margins_from_train": {k: round(v * 100, 2) for k, v in choice.items()},
        "test_days": round(test_days, 2),
        "test_fills": int(len(sel_te)),
        "test_fills_per_day": round(len(sel_te) / test_days, 1) if test_days else None,
        "test_avg_net_bps_per_fill": round(float(sel_te.r.mean()) * 1e4, 1) if len(sel_te) else None,
        "test_win_rate_pct": round(float((sel_te.r > 0).mean()) * 100, 1) if len(sel_te) else None,
        "test_return_pct": round((curve_te[-1] / capital - 1) * 100, 3),
        "test_return_per_3_days_pct": round(((curve_te[-1] / capital) ** (3 / test_days) - 1) * 100, 3) if test_days else None,
        "test_max_drawdown_pct": round(dd_te, 3),
        "per_coin_test": {co: {"fills": int(len(g)), "avg_bps": round(float(g.r.mean()) * 1e4, 1)}
                          for co, g in sel_te.groupby("coin")} if len(sel_te) else {},
        "pooled_by_margin": priors["_pooled"],
        "assumptions": "flash-dip guard; trade-through fills; fill size <= 25% of the bar's Toman volume; "
                       "hedge at the next REAL coin/USDT trade (worst of close/low); full taker fees on hedge",
    }
    ft.to_csv(os.path.join(out_dir, "arb_fills_all.csv"), index=False)
    json.dump({"summary": summary, "priors": priors}, open(os.path.join(out_dir, "arb_summary.json"), "w"),
              indent=2, ensure_ascii=False)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        x = pd.to_datetime(frames["USDTTMN"].index[half:n_bars], unit="s")
        fig, ax = plt.subplots(figsize=(11, 4))
        ax.plot(x[:len(curve_te)], curve_te / capital * 100 - 100, lw=1.6, color="#1f6feb")
        ax.axhline(0, color="#888", lw=0.8)
        ax.set_ylabel("Return % (out-of-sample)")
        ax.set_title(f"Hedged fair-value arbitrage — walk-forward test: {summary['test_return_pct']}% in "
                     f"{summary['test_days']}d, maxDD {summary['test_max_drawdown_pct']}%, {summary['test_fills']} fills")
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "arb_backtest.png"), dpi=130)
        plt.close(fig)
    except Exception:
        pass
    return {"summary": summary, "priors": priors}
