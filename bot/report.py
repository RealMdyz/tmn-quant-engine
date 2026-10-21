"""logs/report.md + charts from the decision log, equity curve and backtest —
for the demo video and the judges' technical review."""
from __future__ import annotations

import json
import os
from collections import Counter

import pandas as pd


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _plot_equity(eq, init, path, title):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(11, 5.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        x = pd.to_datetime(eq["time"])
        ax[0].plot(x, eq["equity"] / init * 100 - 100, lw=1.6, color="#1f6feb")
        ax[0].axhline(0, color="#888", lw=0.8)
        ax[0].set_ylabel("Return %")
        ax[0].set_title(title)
        ax[1].fill_between(x, -eq["drawdown_pct"], 0, color="#d1242f", alpha=0.5)
        ax[1].set_ylabel("DD %")
        fig.tight_layout()
        fig.savefig(path, dpi=120)
        plt.close(fig)
        return True
    except Exception:
        return False


def _section(mode, cfg, ld):
    recs = _load(os.path.join(ld, f"decisions_{mode}.jsonl"))
    if not recs:
        return f"## {mode.upper()}\n\n_No records yet._\n"
    init = cfg["challenge"]["initial_capital_tmn"]
    ev = Counter(r["event"] for r in recs)
    fills = [r for r in recs if r["event"] == "fill_hedged"]
    pols = [r for r in recs if r["event"] == "policy"]
    lines = [f"## {mode.upper()}", ""]
    eq_path = os.path.join(ld, f"equity_{mode}.csv")
    if os.path.exists(eq_path):
        eq = pd.read_csv(eq_path)
        if not eq.empty:
            last = eq["equity"].iloc[-1]
            lines += [f"- Equity: **{last:,.0f} TMN** ({(last / init - 1) * 100:+.3f}%)",
                      f"- Max drawdown: **{eq['drawdown_pct'].max():.3f}%**",
                      f"- Traded volume: {eq['volume_tmn'].iloc[-1]:,.0f} TMN"]
            if _plot_equity(eq, init, os.path.join(ld, f"equity_{mode}.png"), f"{mode} equity"):
                lines.append(f"\n![equity](equity_{mode}.png)\n")
    if fills:
        df = pd.DataFrame(fills)
        lines += [f"- Hedged fills: **{len(df)}**, win rate {(df.net_return_bps > 0).mean() * 100:.1f}%, "
                  f"avg {df.net_return_bps.mean():.1f} bps, realised PnL {df.pnl_tmn.sum():,.0f} TMN", "",
                  "| coin | fills | avg bps | PnL TMN |", "|---|---|---|---|"]
        for c, g in df.groupby("coin"):
            lines.append(f"| {c} | {len(g)} | {g.net_return_bps.mean():.1f} | {g.pnl_tmn.sum():,.0f} |")
        lines.append("")
    lines += [f"- AI supervisor decisions: {len(pols)} (sources: {dict(Counter(p['policy'].get('source') for p in pols))})",
              f"- Events: {dict(ev)}", ""]
    if pols:
        p = pols[-1]["policy"]
        lines += ["### Latest AI decision", "```json",
                  json.dumps({k: p.get(k) for k in ("enabled_coins", "margin_mult", "usdt_hold_frac", "pause",
                                                     "reasoning", "tool_trace", "source")},
                             ensure_ascii=False, indent=2), "```", ""]
    if fills:
        f = fills[-1]
        lines += ["### Example trade decision chain", "```json",
                  json.dumps({k: f.get(k) for k in ("time", "coin", "quote_price", "liquidation_value_at_quote",
                                                     "margin", "hedge_avg_usdt", "usdt_tmn_bid", "net_return_bps",
                                                     "pnl_tmn", "why")}, ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def build_report(cfg) -> str:
    ld = cfg["logging"]["dir"]
    parts = ["# TMN Quant Engine — run report", ""]
    bt = os.path.join(ld, "backtest", "arb_summary.json")
    if os.path.exists(bt):
        s = json.load(open(bt, encoding="utf-8"))["summary"]
        parts += ["## Walk-forward backtest (out-of-sample half)", "", "```json",
                  json.dumps(s, indent=2, ensure_ascii=False, default=str), "```", ""]
        for name in s:
            d = os.path.splitext(os.path.basename(name))[0]
            parts.append(f"![backtest {d}](backtest/{d}/arb_backtest.png)")
        parts.append("")
    for mode in ("shadow", "live"):
        parts.append(_section(mode, cfg, ld))
    path = os.path.join(ld, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return path
