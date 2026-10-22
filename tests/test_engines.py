"""Offline end-to-end tests of both engines against a scripted fake Wallex (no network, no keys).

    python run.py test            (or: python -m pytest tests/ if pytest is installed)

The fake exchange serves order books and a trade tape; PaperExec (the shadow executor) fills
our orders exactly as in the shadow test. The engines' clocks are simulated, so 30 minutes run
in a few seconds.
"""
from __future__ import annotations

import json
import os
import random
import sys
import tempfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from bot import arb_engine, brokers, decision_log, mm_engine  # noqa: E402
from bot.instance import InstanceLock  # noqa: E402
from bot.wallex_client import MarketInfo  # noqa: E402

CLOCK = [1_790_000_000.0]
for _mod in (arb_engine, mm_engine, brokers, decision_log):
    _mod.time.time = lambda: CLOCK[0]
mm_engine.time.sleep = lambda s: None

USDT = 270_000.0


def _mk(sym, base, quote, price_dec, qty_dec, min_notional, vol=1e10):
    return MarketInfo(sym, base, quote, qty_dec, price_dec, 0.0, min_notional, 0, 0, 0, vol)


class FakeWallex:
    def __init__(self, coins: dict[str, float]):
        self.usd = dict(coins)
        self.dev = {c: 0.002 for c in coins}      # Toman premium over the global fair value
        self.tape: dict[str, list] = {}
        self.random_flow = True
        self.v1_usdt = None

    def markets(self):
        m = {"USDTTMN": _mk("USDTTMN", "USDT", "TMN", 0, 2, 50_000, 1e12)}
        for c, p in self.usd.items():
            m[f"{c}TMN"] = _mk(f"{c}TMN", c, "TMN", 0 if p * USDT > 100 else 4, 8, 50_000)
            m[f"{c}USDT"] = _mk(f"{c}USDT", c, "USDT", 4, 4, 1.0, 1e6)
        return m

    def prop_package(self, pid):
        return {"unavailableMarkets": []}

    def depth_all(self):
        b = {"USDTTMN": {"bids": [(USDT, 1e4)], "asks": [(USDT + 100, 1e4)]}}
        for c, p in self.usd.items():
            b[f"{c}USDT"] = {"bids": [(round(p * 0.9995, 4), 50 + random.random())], "asks": [(round(p * 1.0005, 4), 50)]}
            fv = p * USDT * (1 + self.dev[c])
            nd = 0 if fv > 100 else 4
            depth = 5e8 / fv                                   # ~500M TMN on each side
            b[f"{c}TMN"] = {"bids": [(round(fv * 0.995, nd), depth)], "asks": [(round(fv * 1.005, nd), depth)]}
        return b

    def depth(self, sym):
        bid = self.v1_usdt or USDT
        return {"bids": [(bid, 1e4)], "asks": [(bid + 100, 1e4)]}

    def trades(self, sym):
        if sym == "USDTTMN":
            bid = self.v1_usdt or USDT
            return [{"price": bid + 50, "quantity": 5, "timestamp": CLOCK[0] - 5}]
        t = list(self.tape.get(sym, []))[-40:]
        if self.random_flow:
            c = sym[:-3]
            fv = self.usd[c] * USDT * (1 + self.dev[c])
            for _ in range(2):
                side = random.choice([-1, 1])
                t.append({"price": round(fv * (1 + side * random.uniform(0.004, 0.012)), 0 if fv > 100 else 4), "quantity": 5.0,
                          "timestamp": CLOCK[0] - 0.5, "isBuyOrder": side > 0})
        self.tape[sym] = t
        return t


def _cfg(tmp, coins, strategy):
    cfg = yaml.safe_load(open(os.path.join(ROOT, "config.yaml"), encoding="utf-8"))
    cfg["agent"]["enabled"] = False
    cfg["logging"]["dir"] = tmp
    cfg["challenge"]["end_time"] = "2027-01-01T00:00:00+03:30"
    cfg["strategy"] = strategy
    cfg["mm"]["coins"] = list(coins)
    cfg["arb"]["coins"] = list(coins)
    return cfg


def _events(tmp, mode="shadow"):
    with open(os.path.join(tmp, f"decisions_{mode}.jsonl"), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def test_market_maker_end_to_end():
    random.seed(3)
    tmp = tempfile.mkdtemp()
    fake = FakeWallex({"SOL": 180.0, "SUI": 3.2, "LTC": 95.0})
    e = mm_engine.MMEngine(_cfg(tmp, fake.usd, "mm"), "shadow", None, client=fake)
    e.setup()

    def run(n):
        for _ in range(n):
            for c in fake.usd:
                fake.usd[c] *= 1 + random.gauss(0, 0.0003)
            e.step()
            CLOCK[0] += 2

    run(30)
    assert e.policy["source"] == "fallback" and e.policy["markets"], "fallback policy picks markets"
    assert any(o for v in e.orders.values() for o in v.values()), "two-sided quotes are resting"
    run(600)
    assert e.stats["buys"] > 0 and e.stats["sells"] > 0 and e.stats["round_trips"] > 0, "fills on both sides"
    fake.usd["SOL"] *= 0.97                                   # crash: stop-loss + buy guard
    run(5)
    assert "SOL" in e.blocked, "falling fair value blocks buying"
    assert any(x["event"] == "exit" and x["coin"] == "SOL" for x in _events(tmp)), "stop-loss exit fired"
    e.risk.end_ts = CLOCK[0] + 30 * 60                        # inside the forced-flatten window
    run(3)
    assert e.equity(e._books)[1] < 50_000, "inventory flattened before the end"
    InstanceLock(e.lock.path).claim()                         # a newer deployment takes over
    try:
        e.step()
        raise AssertionError("old instance must stop")
    except SystemExit:
        pass


def test_portfolio_three_sleeves():
    random.seed(5)
    tmp = tempfile.mkdtemp()
    coins = {"SOL": 180.0, "SUI": 3.2, "BTC": 108000.0, "ETH": 3900.0, "ADA": 0.65, "PEPE": 0.00001, "SHIB": 0.000012,
             "DOGE": 0.19, "LINK": 17.5}
    fake = FakeWallex(coins)
    fake.candles = lambda sym, res, a, b: {"t": [b - 3600 * k for k in range(60, -1, -1)],
                                           "c": [USDT * (1 - 0.0004 * k) for k in range(60, -1, -1)]}
    cfg = _cfg(tmp, coins, "mm")
    cfg["portfolio"]["sleeves"]["rial"]["usdt_exit_at"] = "2027-01-01T00:00:00+03:30"
    cfg["risk"]["max_drawdown_pct"] = 10.0          # isolate the sleeve's own stop from the account breaker
    cfg["risk"]["daily_loss_limit_pct"] = 10.0
    e = mm_engine.MMEngine(cfg, "shadow", None, client=fake)
    e.setup()
    assert "BTC" not in e.coins and "ADA" not in e.coins, "sleeve assets are excluded from the market maker"
    CLOCK[0] = 1_790_000_000.0 + 3600 * 19.5     # 12:23 Tehran: USDT/TMN market open (08:00-21:00)

    def run(n):
        for _ in range(n):
            e.step()
            CLOCK[0] += 2
    run(400)                                      # makers time out -> taker top-ups
    assert e.regime["cap"] == 1.0, "USDT/TMN +2.4% in 48h -> full exposure"
    eq, _ = e.equity(e._books)
    for name in ("rial", "beta"):
        v, c = e.sleeves[name].value(e._books)
        assert v > 0.8 * e.sleeves[name].capital, f"{name} sleeve built (value {v:,.0f})"
    held = sum(e.sleeves[k].value(e._books)[0] for k in ("rial", "beta"))
    assert eq >= e.bal()["TMN"]["total"] + held - 1, "equity counts every held asset"
    for c in ("ADA", "PEPE", "LINK", "SHIB", "DOGE"):         # beta crash beyond its 7% disaster stop
        fake.usd[c] *= 0.91
    run(15)
    ev = _events(tmp)
    assert e.sleeves["beta"].stopped and any(x["event"] == "sleeve_stop" and x["sleeve"] == "beta" for x in ev)
    assert e.sleeves["beta"].value(e._books)[0] < 100_000, "beta holdings sold"
    assert not e.sleeves["rial"].stopped, "the other sleeve is untouched"
    e.sleeves["rial"].cfg["usdt_exit_at"] = "2026-01-01T00:00:00+03:30"   # USDT deadline passed
    run(15)
    assert e.sleeves["rial"].pos.get("USDT", {}).get("qty", 0) * USDT < 60_000, "USDT closed by its deadline"


def test_end_of_challenge_wind_down_in_steps():
    random.seed(7)
    tmp = tempfile.mkdtemp()
    coins = {"SOL": 180.0, "SUI": 3.2, "BTC": 108000.0, "ETH": 3900.0, "ADA": 0.65, "PEPE": 0.00001, "LINK": 17.5}
    fake = FakeWallex(coins)
    fake.candles = lambda sym, res, a, b: {"t": [b - 3600 * k for k in range(60, -1, -1)],
                                           "c": [USDT * (1 - 0.0004 * k) for k in range(60, -1, -1)]}
    e = mm_engine.MMEngine(_cfg(tmp, coins, "mm"), "shadow", None, client=fake)
    e.setup()
    CLOCK[0] = 1_790_000_000.0 + 3600 * 19.5

    def run(n, dt=2):
        for _ in range(n):
            e.step()
            CLOCK[0] += dt
    run(400)
    built = {k: e.sleeves[k].value(e._books)[0] for k in ("rial", "beta")}
    assert all(v > 0.8 * e.sleeves[k].capital for k, v in built.items()), built
    stop = CLOCK[0] + 3 * 3600 + 20 * 60 - 30            # 4 h before the end: first step (75% still held)
    e.risk.end_ts = stop + 40 * 60
    n_ev = len(_events(tmp))
    run(1)
    assert e.risk.wind_down(CLOCK[0]) == 0.75
    run(45, dt=30)                                        # 22 min: maker asks, then taker after 15 min
    ev = _events(tmp)[n_ev:]
    assert any(x["event"] == "wind_down_step" and x["share_still_held"] == 0.75 for x in _events(tmp))
    assert any(x["event"] == "sleeve_order" and x["side"] == "SELL" and not x["taker"] for x in ev), "maker asks first"
    assert not any(x["event"] == "sleeve_order" and x["side"] == "BUY" for x in ev), "no buying in the wind-down"
    for k, v in built.items():
        now_v = e.sleeves[k].value(e._books)[0]
        assert 0.6 * v < now_v < 0.85 * v, f"{k}: {now_v:,.0f} of {v:,.0f} still held after the first step"
    CLOCK[0] = stop - 45 * 60                             # last step: 0% held, 50 min of selling before the flatten
    run(45, dt=30)
    assert not e.risk.must_flatten(CLOCK[0])
    for k in ("rial", "beta"):
        assert e.sleeves[k].value(e._books)[0] < 100_000, f"{k} sold before the forced flatten"


def test_live_self_test_with_paper_executor():
    tmp = tempfile.mkdtemp()
    fake = FakeWallex({"SOL": 180.0})
    real = mm_engine.LiveExec
    mm_engine.LiveExec = lambda c, f: brokers.PaperExec({"TMN": 5e6}, {}, {"tmn_maker": 0.0025, "tmn_taker": 0.003,
                                                                           "usdt_maker": 0.001, "usdt_taker": 0.0013})
    fake.fees = lambda: {}
    try:
        e = mm_engine.MMEngine(_cfg(tmp, fake.usd, "mm"), "live", None, client=fake)
        e.setup()
    finally:
        mm_engine.LiveExec = real
    st = [x for x in _events(tmp, "live") if x["event"] == "live_self_test"][0]
    assert st["ok"] and st["listed_in_open_orders"] and st["active_after_cancel"] is False


def test_arbitrage_engine_end_to_end():
    random.seed(1)
    tmp = tempfile.mkdtemp()
    fake = FakeWallex({"TRX": 0.33, "ADA": 0.23})
    fake.random_flow = False
    fake.dev = {c: 0.0 for c in fake.usd}
    e = arb_engine.ArbEngine(_cfg(tmp, fake.usd, "arb"), "shadow", None, client=fake)
    e.setup()

    def run(n):
        for _ in range(n):
            e.step()
            CLOCK[0] += 2

    run(40)
    q = e.quotes.get("TRX")
    assert q, "calm market -> resting deep bid"
    fake.tape["TRXTMN"] = [{"price": q["price"] * 0.995, "quantity": 50, "timestamp": CLOCK[0] + 1}]
    run(5)
    assert e.stats["fills"] == 1 and e.stats["hedges"] == 1, "flash dip filled and hedged"
    fake.tape["TRXTMN"] = []
    for k in range(30):                                       # sliding Toman book
        fake.dev["ADA"] = -0.0002 * k
        run(1)
    assert "ADA" in e.blocked, "sliding Toman book blocks the quote"
    fake.v1_usdt = USDT * 1.01                                # /v2 USDT book stale vs /v1
    CLOCK[0] += 61
    run(2)
    assert e.usdt_override is not None, "stale USDT/TMN book replaced by /v1"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as ex:  # noqa: BLE001
            failed += 1
            print(f"FAIL {t.__name__}: {ex!r}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(main())
