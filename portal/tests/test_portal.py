"""Offline tests of the portal (no network): risk scoring, the paper bot, the founder telemetry parser and the
whole user flow through the API.  Run from the repo root:  python -m portal.tests.test_portal  (or pytest)."""
from __future__ import annotations

import os
import sys
import tempfile
import traceback

_TMP = tempfile.mkdtemp(prefix="portal-test-")
os.environ.update({"PORTAL_DATA_DIR": _TMP, "MARKET_SOURCE": "replay", "RUN_WORKER": "0", "PORTAL_SECRET": "test",
                   "FOUNDER_EMAIL": "founder@example.com", "FOUNDER_PASSWORD": "Founder-pass1", "PAYMENT_PROVIDER": "demo",
                   "SEED_DEMO": "0", "WALLEX_API_KEY": "", "BOT_STATUS_URL": "", "BOT_LOGS_DIR": "", "GITHUB_TOKEN": ""})

from portal.app import risk, simulator  # noqa: E402
from portal.app.db import BotAccount  # noqa: E402
from portal.app.telemetry import parse_equity_csv, parse_sleeves_csv, render_event  # noqa: E402

H = {"X-Requested-With": "tmn"}


def answers(*vals):
    return {q["id"]: v for q, v in zip(risk.QUESTIONS, vals)}


# ------------------------------------------------------------------ risk
def test_score_extremes_and_profiles():
    lo = risk.score(answers(*[0] * 10))
    hi = risk.score(answers(*[4] * 10))
    assert lo["score"] == 0 and lo["profile_key"] == "conservative"
    assert hi["score"] == 100 and hi["profile_key"] == "aggressive"
    assert lo["allocation"] == {"low": 85, "medium": 15, "high": 0}
    assert hi["allocation"] == {"low": 5, "medium": 25, "high": 70}


def test_low_capacity_caps_the_score():
    r = risk.score(answers(0, 0, 0, 0, 0, 4, 4, 4, 4, 4))     # wants risk, cannot afford it
    assert r["capacity"] == 0 and r["willingness"] == 100
    assert r["score"] == 10, r["score"]                      # min(50, 0 + 10)


def test_founder_anchor_and_allocations_sum_to_100():
    assert risk.allocation_for(70) == {"low": 20, "medium": 35, "high": 45}
    assert risk.founder_allocation() == (20, 35, 45)        # read from config.yaml
    for s in range(0, 101):
        a = risk.allocation_for(s)
        assert a["low"] + a["medium"] + a["high"] == 100 and min(a.values()) >= 0, (s, a)
    highs = [risk.allocation_for(s)["high"] for s in range(0, 101)]
    assert highs == sorted(highs), "high-risk share must grow with the score"


def test_custom_allocation_only_more_conservative():
    rec = {"low": 20, "medium": 35, "high": 45}
    assert risk.check_custom_allocation(rec, {"low": 40, "medium": 30, "high": 30}) is None
    assert risk.check_custom_allocation(rec, {"low": 10, "medium": 35, "high": 55})          # riskier
    assert risk.check_custom_allocation(rec, {"low": 10, "medium": 45, "high": 45})          # more medium+high
    assert risk.check_custom_allocation(rec, {"low": 20, "medium": 35, "high": 40})          # sum 95
    assert risk.validate_answers({"horizon": 9})


# ------------------------------------------------------------------ paper bot
def _snap(prices, ch48, fresh=True):
    return {"fresh": fresh, "prices": prices,
            "regime": {"on": ch48 >= 1.0, "ch48_pct": ch48, "threshold_pct": 1.0}}


PRICES = {a: {"bid": p * 0.999, "ask": p * 1.001} for a, p in
          {"BTC": 2.2e10, "ETH": 6.5e8, "PEPE": 2.5, "ADA": 1.9e5, "LINK": 4.6e6, "USDT": 2.7e5}.items()}


def test_bot_waits_then_enters_then_stops_out():
    bot = BotAccount(id=1, mode="paper")
    simulator.start(bot, 10_000_000, {"low": 20, "medium": 35, "high": 45})
    ctx = simulator.step(bot, _snap(PRICES, 0.4))
    assert not ctx.trades and ctx.events[0].kind == "wait"
    assert simulator.valuation(bot.state, PRICES)["equity"] == 10_000_000
    ctx = simulator.step(bot, _snap(PRICES, 2.0))
    assert {(t.sleeve, t.asset) for t in ctx.trades} == {("medium", "BTC"), ("medium", "ETH"), ("high", "PEPE"),
                                                        ("high", "ADA"), ("high", "LINK")}
    v = simulator.valuation(bot.state, PRICES)
    assert 9_950_000 < v["equity"] < 10_000_000                       # only fees + spread lost
    assert v["low"] == 2_000_000
    crash = {a: {"bid": x["bid"] * (0.9 if a in ("PEPE", "ADA", "LINK") else 1), "ask": x["ask"]} for a, x in PRICES.items()}
    ctx = simulator.step(bot, _snap(crash, 2.0))                      # beta -10% < -7% disaster stop
    assert any(e.kind == "stop" for e in ctx.events)
    st = bot.state["sleeves"]
    assert st["high"]["stopped"] and not st["high"]["pos"] and st["medium"]["pos"]
    simulator.stop(bot, crash)
    assert bot.status == "stopped" and not bot.state["sleeves"]["medium"]["pos"]
    assert bot.state["sleeves"]["medium"]["cash"] > 3_400_000


def test_stale_prices_do_not_trade():
    bot = BotAccount(id=2, mode="paper")
    simulator.start(bot, 5_000_000, {"low": 0, "medium": 50, "high": 50})
    assert not simulator.step(bot, _snap(PRICES, 3.0, fresh=False)).trades


def test_replay_feed():
    from portal.app.market import ReplayFeed
    f = ReplayFeed(speed=60)
    s = f.snapshot(1.0, now=1_800_000_000)
    assert s["prices"]["BTC"]["bid"] < s["prices"]["BTC"]["ask"]
    assert s["regime"]["ch48_pct"] is not None


# ------------------------------------------------------------------ telemetry
def test_telemetry_parsers():
    rows = parse_equity_csv("ts,time,equity,drawdown_pct,fills,pnl_tmn,volume_tmn,usdt_tmn,coins_tmn\n"
                            "100,t,5000000,0,0,0,0,0,0\n160,t,4990000,0.2,2,-500,800000,0,300000\n")
    assert rows[-1]["equity"] == 4_990_000 and rows[-1]["fills"] == 2
    sl = parse_sleeves_csv("ts,time,equity,mm_realised_pnl,beta_value,beta_pnl,beta_ret_pct,beta_scale,rial_value,rial_pnl,"
                           "rial_ret_pct,rial_scale\n1,t,5,0,1985303,-15762,-0.788,0.8,1751504,342,0.020,1.0\n")
    assert sl["beta"]["ret_pct"] == -0.788 and sl["rial"]["scale"] == 1.0
    assert render_event({"event": "quote"}) is None
    e = render_event({"event": "policy", "ts": 1, "policy": {"markets": {"FIL": 0.9}, "sleeves": {"rial": 1, "beta": 0.8},
                                                             "beta_assets": ["PEPE"], "source": "llm", "reasoning": "x"}})
    assert e["kind"] == "ai" and "FIL" in e["text"] and e["detail"] == "x"


# ------------------------------------------------------------------ API flow
def test_api_flow():
    from fastapi.testclient import TestClient
    from portal.app.main import app
    from portal.app import worker
    with TestClient(app) as c:
        worker.market_tick()
        assert c.post("/api/auth/signup", json={"name": "a", "email": "x@example.com", "password": "abc12345"}).status_code == 403
        r = c.post("/api/auth/signup", json={"name": "a", "email": "x@example.com", "password": "short"}, headers=H)
        assert r.status_code == 400
        r = c.post("/api/auth/signup", json={"name": "a", "email": "x@example.com", "password": "abc12345"}, headers=H)
        assert r.status_code == 200, r.text
        assert c.post("/api/auth/signup", json={"name": "a", "email": "X@example.com", "password": "abc12345"},
                      headers=H).status_code == 400                                    # duplicate (case-insensitive)
        assert c.post("/api/bot/start", json={"capital_tmn": 5e6}, headers=H).status_code == 400   # no profile yet
        r = c.post("/api/risk/submit", json={"answers": answers(*[3] * 10)}, headers=H)
        assert r.status_code == 200 and r.json()["profile"]["score"] == 75
        assert c.post("/api/bot/start", json={"capital_tmn": 5e6}, headers=H).status_code == 402   # no subscription
        assert c.post("/api/allocation", json={"low": 0, "medium": 30, "high": 70}, headers=H).status_code == 400
        assert c.post("/api/allocation", json={"low": 40, "medium": 30, "high": 30}, headers=H).status_code == 200
        assert c.post("/api/billing/checkout", json={"plan": "monthly"}, headers=H).json()["paid"]
        assert c.get("/api/me").json()["subscription"]["plan"] == "monthly"
        assert c.post("/api/bot/start", json={"capital_tmn": 1000}, headers=H).status_code == 400  # below minimum
        r = c.post("/api/bot/start", json={"capital_tmn": 5e6}, headers=H)
        assert r.status_code == 200 and r.json()["bot"]["status"] == "running"
        assert r.json()["bot"]["allocation"] == {"low": 40, "medium": 30, "high": 30}
        worker.market_tick()
        assert c.get("/api/bot/activity").json()["events"]
        assert c.get("/api/founder/overview").status_code == 403
        assert c.post("/api/bot/stop", headers=H).json()["bot"]["status"] == "stopped"
        c.post("/api/auth/logout", headers=H)
        assert c.get("/api/bot").status_code == 401
        for _ in range(8):
            c.post("/api/auth/login", json={"email": "founder@example.com", "password": "wrong"}, headers=H)
        assert c.post("/api/auth/login", json={"email": "founder@example.com", "password": "Founder-pass1"},
                      headers=H).status_code == 429                                    # rate limited
        from portal.app.security import login_limit
        login_limit.hits.clear()
        r = c.post("/api/auth/login", json={"email": "founder@example.com", "password": "Founder-pass1"}, headers=H)
        assert r.json()["role"] == "founder"
        o = c.get("/api/founder/overview").json()
        assert o["platform"]["users"] == 2 and o["platform"]["active_subscriptions"] == 1
        assert o["allocation"] == {"low": 20, "medium": 35, "high": 45}
        assert c.post("/api/bot/start", json={"capital_tmn": 5e6}, headers=H).status_code == 400   # master bot
        assert len(c.get("/api/founder/users").json()["users"]) == 2
        assert "سه‌سبد" in c.get("/").text and c.get("/static/app.js").status_code == 200


def main() -> int:
    tests = [(k, v) for k, v in globals().items() if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:                                     # noqa: BLE001
            failed += 1
            print(f"FAIL {name}\n{traceback.format_exc()}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
