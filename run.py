"""TMN Quant Engine — command line.

  python run.py check              connectivity, API key, balances, fees, allowed markets, LLM
  python run.py backtest           walk-forward backtest of the arbitrage (downloads 10 days of candles)
  python run.py shadow             live books, simulated fills (shadow test, no orders)
  python run.py live --yes         REAL trading on the challenge account
  python run.py flatten            emergency: cancel everything, sell all coins + USDT back to Toman
  python run.py report             logs/report.md + charts from decision logs and equity curve
  python run.py probe              read-only market snapshot for research -> logs/probe/
  python run.py backtest-mm        backtest of the market maker on the shipped 1-minute data
  python run.py test               offline end-to-end tests of both engines (fake exchange, no network)
  python run.py backtest-book      market-maker backtest on the recorded 10-second order books (data/books_10s_*)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

import yaml
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from bot.wallex_client import WallexClient, WallexError  # noqa: E402


def setup_logging(name):
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.FileHandler(f"logs/{name}.log", encoding="utf-8"),
                                  logging.StreamHandler(sys.stdout)])


def cmd_check(cfg):
    key = os.getenv("WALLEX_API_KEY")
    c = WallexClient(key)
    ok = True
    print("== public API")
    try:
        mk = c.markets()
        books = c.depth_all()
        print(f"  OK  {len(mk)} markets, {len(books)} order books in one call")
        pkg = c.prop_package(cfg["challenge"]["package_id"])
        unav = set(pkg.get("unavailableMarkets") or [])
        print(f"  OK  package {pkg['detail']['id']} '{pkg['detail']['title']}' loan={pkg['detail']['loan']} "
              f"unavailable markets={len(unav)}")
        from bot.arb import deviation
        for coin in cfg["arb"]["coins"]:
            st = "ALLOWED" if f"{coin}TMN" not in unav and f"{coin}USDT" not in unav else "NOT ALLOWED"
            d = deviation(books, coin)
            print(f"     {coin:5s} {st:12s} toman-bid vs liquidation value: {d*100:+.3f}%" if d is not None
                  else f"     {coin:5s} {st}")
    except WallexError as e:
        ok = False
        print("  FAIL", e)
    print("== private API")
    if not key:
        print("  SKIP  WALLEX_API_KEY not set")
    else:
        try:
            b = c.balances()
            print("  OK  balances:", json.dumps({k: v for k, v in b.items() if v["total"] > 0}, ensure_ascii=False))
        except WallexError as e:
            ok = False
            print("  FAIL balances:", e)
        try:
            f = c.fees()
            show = {s: f[s] for s in ["USDTTMN"] + [f"{x}TMN" for x in cfg["arb"]["coins"][:2]] +
                    [f"{x}USDT" for x in cfg["arb"]["coins"][:2]] if s in f}
            print("  OK  fees:", json.dumps(show))
        except WallexError as e:
            print("  WARN fees:", e)
        try:
            print("  OK  open orders:", len(c.open_orders()))
        except WallexError as e:
            print("  WARN open orders:", e)
    print("== LLM providers")
    import requests
    for p in cfg["agent"]["providers"]:
        base, k = os.getenv(p["base_url_env"]), os.getenv(p["api_key_env"])
        if not (base and k):
            print(f"  SKIP {p['name']} (env not set)")
            continue
        try:
            r = requests.post(f"{base.rstrip('/')}/chat/completions", timeout=40,
                              headers={"Authorization": f"Bearer {k}"},
                              json={"model": p["model"], "messages": [{"role": "user", "content": "say ok"}]})
            print(f"  {'OK ' if r.ok else 'FAIL'} {p['name']} {r.status_code} {r.text[:120]}")
        except Exception as e:
            print(f"  FAIL {p['name']} {e}")
    print("== news feeds")
    from bot.agent import fetch_headlines
    for h in fetch_headlines(cfg["agent"]["news_feeds"], "all", 2)[:8]:
        print("   ", h)
    print("\nRESULT:", "READY" if ok else "PROBLEMS FOUND")


def cmd_backtest(cfg, args):
    """Walk-forward backtest. --cached uses the two research datasets shipped in data/ (real Wallex
    1-minute data aggregated to 5 minutes, 2026-10-12..22); otherwise fresh data is downloaded.
    pooled_by_margin = [margin %, mean net bps per fill, fills per coin per 10 days] over all coins."""
    import numpy as np
    import pandas as pd
    from bot.data import load_or_fetch
    from bot.backtest_arb import run_arb_backtest
    from bot.arb import Fees
    f = cfg["fees"]
    fees = Fees(f["tmn_maker"], f["tmn_taker"], f["usdt_maker"], f["usdt_taker"])
    datasets = []
    if args.cached:
        for path in ("data/m5_all.json", "data/m5_extra.json"):
            raw = json.load(open(path))
            datasets.append((path, {s: pd.DataFrame({k: raw[s][k] for k in "ohlcv"},
                                                    index=np.array(raw[s]["t"], dtype="int64")) for s in raw}))
    else:
        coins = sorted(set(cfg["arb"]["coins"]) | {"BTC", "ETH", "XRP", "PEPE"})
        syms = ["USDTTMN"] + [f"{c}TMN" for c in coins] + [f"{c}USDT" for c in coins]
        datasets.append(("download", load_or_fetch(WallexClient(os.getenv("WALLEX_API_KEY")), syms,
                                                   cache="data/m5_fresh.json", days=args.days)))
    combined = {"datasets": {}, "priors": {}}
    for name, frames in datasets:
        coins = sorted({s[:-3] for s in frames if s.endswith("TMN") and s != "USDTTMN" and f"{s[:-3]}USDT" in frames})
        out = os.path.join("logs", "backtest", os.path.splitext(os.path.basename(name))[0])
        res = run_arb_backtest(frames, coins, fees, out_dir=out)
        combined["datasets"][name] = res["summary"]
        combined["priors"][name] = res["priors"]["_pooled"]
        print(f"\n=== {name} ===")
        print(json.dumps({k: res["summary"][k] for k in ("chosen_margins_from_train", "test_days", "test_fills",
                          "test_avg_net_bps_per_fill", "test_win_rate_pct", "test_return_pct",
                          "test_max_drawdown_pct", "pooled_by_margin")}, indent=2, ensure_ascii=False))
    os.makedirs("logs/backtest", exist_ok=True)
    json.dump({"summary": combined["datasets"], "priors": combined["priors"]},
              open("logs/backtest/arb_summary.json", "w"), indent=2, ensure_ascii=False)
    print("\nSaved per-dataset results under logs/backtest/<dataset>/ and logs/backtest/arb_summary.json")


def cmd_flatten(cfg):
    from bot.arb_engine import ArbEngine
    eng = ArbEngine(cfg, "live", os.environ["WALLEX_API_KEY"])
    eng.setup()
    books = eng.client.depth_all()
    for o in eng.client.open_orders():
        eng.ex.cancel(o.get("clientOrderId"))
    eng.flatten(books, "manual_flatten_command")
    print("flatten done:", eng.ex.balances())


def main():
    load_dotenv(os.path.join(ROOT, ".env"))
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["check", "backtest", "backtest-mm", "backtest-book", "test", "shadow", "live", "flatten", "report", "probe"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--days", type=float, default=10)
    ap.add_argument("--cached", action="store_true", help="backtest on data/m5_all.json without downloading")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    setup_logging(args.command)
    if args.command == "check":
        cmd_check(cfg)
    elif args.command == "backtest":
        cmd_backtest(cfg, args)
    elif args.command == "flatten":
        cmd_flatten(cfg)
    elif args.command == "backtest-book":
        import glob
        from bot.backtest_book import run_book_backtest
        res = run_book_backtest(sorted(glob.glob("data/books_10s_*.csv")))
        print(json.dumps(res["by_setting"], indent=2, ensure_ascii=False))
        print("saved logs/backtest_book/book_summary.json")
    elif args.command == "test":
        from tests.test_engines import main as run_tests
        sys.exit(run_tests())
    elif args.command == "backtest-mm":
        from bot.backtest_mm import run_mm_backtest
        res = run_mm_backtest("data/m1_tmn_2026-10-20_22.json", "data/m1_usdt_2026-10-20_22.json")
        print(json.dumps(res["by_half_spread"], indent=2, ensure_ascii=False))
        print("saved logs/backtest_mm/mm_summary.json")
    elif args.command == "probe":
        from bot.probe import run_probe
        meta = run_probe(cfg, os.getenv("WALLEX_API_KEY"), days=min(args.days, 2))
        print("probe done:", meta.get("finished"), "errors:", meta.get("errors"))
    elif args.command == "report":
        from bot.report import build_report
        print("written:", build_report(cfg))
    else:
        from bot.arb_engine import ArbEngine
        if args.command == "live":
            if not os.getenv("WALLEX_API_KEY"):
                sys.exit("WALLEX_API_KEY missing")
            if not args.yes and input("LIVE trading with real orders. Type LIVE: ").strip() != "LIVE":
                sys.exit("aborted")
        if cfg.get("strategy", "arb") == "mm":
            from bot.mm_engine import MMEngine
            MMEngine(cfg, args.command, os.getenv("WALLEX_API_KEY")).run()
        else:
            ArbEngine(cfg, args.command, os.getenv("WALLEX_API_KEY")).run()


if __name__ == "__main__":
    main()
