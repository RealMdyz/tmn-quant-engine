"""Fair-value market maker on Wallex Toman books, steered by the AI supervisor.

Why: instant Toman<->USDT arbitrage is negative after fees on all 61 allowed markets (probe,
2026-10-22), but the Toman books are busy (10-660 trades/hour, trades of 2-50M TMN) and several
alt markets quote spreads wider than the 0.5% maker round trip. A maker that buys below and sells
above a fair value earns that spread; its risk is adverse selection (being filled just before the
price moves through us), which the fair value, the guards, the inventory caps and the exits limit.

Fair value (per coin, every cycle, from ONE /v2/depth/all request):
    FV_usdt = mid(COIN/USDT) x mid(USDT/TMN)            -- the global price, moves first
    premium = median over 30 min of mid(COIN/TMN) / FV_usdt - 1   -- the coin's local Toman premium
    FV      = FV_usdt x (1 + premium)
Quotes (both sides are maker orders, never crossing the book):
    bid = FV x (1 - h - skew)      ask = FV x (1 + h - skew)      skew = inventory share x h x k
    h (half-spread) per market is chosen by the AI supervisor; the bid is blocked by the guards
    (Toman book sliding, fair value falling, USDT book frozen, inventory caps); the ask never sells
    below cost + fees unless an exit fires.
Exits: stop-loss when FV falls `stop_pct` below the average cost, time stop after `max_hold_min`,
both as taker sells on the Toman book. USDT is never held: hedges/conversions are not needed, so the
USDT/TMN market being closed 21:00-08:00 Tehran does not matter.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics as st
import time
import logging
import traceback
from collections import deque

from .agent import SupervisorAgent, fetch_headlines
from .arb import Fees
from .brokers import LiveExec, PaperExec
from .decision_log import DecisionLog
from .instance import InstanceLock
from .risk import RiskManager, TEHRAN
from .sleeves import HoldingSleeve
from .wallex_client import WallexClient, WallexError

log = logging.getLogger("mm")

MM_SYSTEM = """You are the decision-making AI of a market-making bot on the Wallex exchange (Iran), in a
3-day trading competition ranked by net % return in Toman (a losing team scores zero; drawdown is
penalised; regular, reasonable trading is rewarded).
The bot rests maker BUY and SELL orders on COIN/TMN books around a fair value FV (global price from the
COIN/USDT book x USDT/TMN, plus the coin's own Toman premium). It earns the spread when its bid and its
ask both fill; it loses when it buys just before the price falls (adverse selection). Maker fee 0.25%
per side, so a round trip costs 0.50%. Evidence so far:
 (a) order-book backtest on 4.2 h of real 10-second books, strict fills: narrow quotes get picked off by
     informed sellers. h 0.2-0.3% lost ~6-7% of capital, h 0.5% -2.4%, h 0.7% -0.3%, h 1.0% +0.2-0.4%;
 (b) live shadow: the few fills came when a coin was falling (FIL: bought, then -1.8% within seconds).
 So: be WIDE (h near the top of the range), prefer few, calm, busy markets whose Toman spread is well above
 MINSP bps, and drop any market whose live round trips lose. The bot never bids where the Toman spread is
 < MINSP bps (spread_bps in get_candidates), so a market below that is a wasted slot.

YOU decide, every ~20 minutes, using the tools:
  1. WHICH markets to make (at most MAXM). Prefer: wide Toman spread (spread_bps), busy market
     (vol24h_mtmn, trades), stable fair value (fv_vol_bps low), live round trips that made money.
     Avoid markets whose live fills lose, whose USDT book is stale, or with coin-specific bad news.
  2. The half-spread h (in %, between HLO and HHI) for each chosen market (quotes never go more than one
     tick inside the current best bid/ask, so a small h means "quote at the top of the book"): wider when the market is
     volatile or our fills there lost money; narrower only when it is calm, spreads are wide and our
     live round trips there made money.
  3. pause=true only for a market-wide shock (major news, crash).
  4. The PORTFOLIO (tool get_portfolio): besides the market maker (20% of the capital), the account runs two
     holding sleeves: "rial" (35%, BTC/ETH, medium risk) and "beta" (45%, high-volatility coins, high risk).
     Both earn mainly from the rial weakening: Toman prices of USDT and coins rose 15-19% in 29 days.
     Backtest (27 h holds, net of fees, entered while USDT/TMN 48h >= +1%): rial +0.88% (P(loss) 34%,
     worst -2.9%), beta PEPE/ADA/LINK +1.28% (30%, worst -4.3%); entered at 0..+1% or below 0 they LOST
     (-0.8..-2%). For each sleeve choose an exposure in [0, 1]; the deterministic regime cap is applied on top.
     In the last 4 hours the engine sells the sleeves in steps on its own (end_wind_down); no buying then.
     Cut exposure on news that the rial may strengthen (deal/negotiation progress, central-bank action,
     sharp USDT/TMN drop) or on crypto-crash news; keep it when the trend and news support it. For "beta"
     you may pick 2-4 coins from its universe (prefer high recent momentum, avoid coin-specific bad news).
Units: all *_bps fields are basis points (100 bps = 1%). h is in PERCENT.
Answer ONLY with JSON:
{"markets": {"COIN": h_percent, ...}, "pause": false,
 "sleeves": {"rial": exposure_0_to_1, "beta": exposure_0_to_1}, "beta_assets": ["COIN", ...],
 "reasoning": "4-6 sentences citing the concrete numbers that drove each choice (markets AND sleeves)"}"""

MM_TOOLS = [
    {"type": "function", "function": {
        "name": "get_portfolio",
        "description": "USDT/TMN regime (6h/24h/48h change, exposure cap) and the two holding sleeves: capital, weights, current exposure, value, cost, return %, PnL, stop state, beta universe.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_candidates",
        "description": "Every candidate market: Toman spread (bps), USDT-book spread (bps), 24h Toman volume (million TMN), local premium vs global fair value (bps), fair-value volatility over 30 min (bps), whether a guard blocks buying now, and our live fills / realised PnL / avg bps per round trip there.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_account_state",
        "description": "Equity in Toman, return %, drawdown, inventory per coin with cost and unrealised PnL, fills and realised PnL, minutes to the end.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_news",
        "description": "Latest headlines (Persian + English) about Iran's economy / rial and crypto markets.",
        "parameters": {"type": "object", "properties": {"topic": {"type": "string", "enum": ["iran", "crypto", "all"]}}}}},
]


def _mid(b):
    return (b["bids"][0][0] + b["asks"][0][0]) / 2 if b and b["bids"] and b["asks"] else None


class MMEngine:
    def __init__(self, cfg: dict, mode: str, api_key: str | None, client: WallexClient | None = None):
        assert mode in ("live", "shadow")
        self.cfg, self.mode, self.m = cfg, mode, cfg["mm"]
        self.client = client or WallexClient(api_key, per_sec=cfg["execution"].get("max_requests_per_sec", 5))
        ld = cfg["logging"]["dir"]
        os.makedirs(ld, exist_ok=True)
        self.dlog = DecisionLog(os.path.join(ld, f"decisions_{mode}.jsonl"), mode)
        self.state_path = os.path.join(ld, f"state_mm_{mode}.json")
        self.equity_path = os.path.join(ld, f"equity_{mode}.csv")
        self.books_path = os.path.join(ld, f"books_mm_{mode}.csv")   # own file: different column set
        self.lock = InstanceLock(os.path.join(ld, f"instance_{mode}.lock"))
        self.risk = RiskManager(cfg["risk"], cfg["challenge"])
        self.orders: dict[str, dict] = {}      # coin -> {"BUY": order|None, "SELL": order|None}
        self.inv: dict[str, dict] = {}         # coin -> {"cost": TMN spent on what we hold, "t0": first buy}
        self.policy: dict = {}
        self.last_policy = 0.0
        self.prem: dict[str, deque] = {}       # coin -> (t, toman mid / FV_usdt - 1)
        self.fvh: dict[str, deque] = {}        # coin -> (t, FV)
        self.ref_changed: dict[str, tuple] = {}
        self.blocked: dict[str, str] = {}
        self.fv: dict[str, float] = {}
        self.vol24: dict[str, float] = {}
        self.last_vol_refresh = 0.0
        self.stats = {"fills": 0, "buys": 0, "sells": 0, "round_trips": 0, "pnl_tmn": 0.0, "volume_tmn": 0.0,
                      "fees_tmn": 0.0, "exits": 0, "cycles": 0, "errors": 0}
        self.coin_stats: dict[str, dict] = {}
        self.trade_seen: dict[str, set] = {}
        self.last_trade_poll: dict[str, float] = {}
        self.last_equity_log = self.last_books_log = 0.0
        self._oo = None
        self._bal = None
        self._books = {}
        self.sleeves: dict[str, HoldingSleeve] = {}
        self.regime = {"cap": 0.0}
        self.last_regime = 0.0
        self.sleeves_path = os.path.join(ld, f"sleeves_{mode}.csv")
        self.last_sleeves_log = 0.0
        self.risk_tz = TEHRAN

    # ================================================================ setup
    def setup(self):
        c, m = self.cfg, self.m
        self.lock.claim()
        self.markets = self.client.markets()
        try:
            pkg = self.client.prop_package(c["challenge"]["package_id"])
            unavailable = set(pkg.get("unavailableMarkets") or [])
        except WallexError as e:
            log.warning("package lookup failed (%s)", e)
            unavailable = set()
        pf = c.get("portfolio") or {}
        for name, scfg in (pf.get("sleeves") or {}).items():
            if scfg.get("enabled", True):
                self.sleeves[name] = HoldingSleeve(name, scfg, self)
        reserved = set()
        for sl in self.sleeves.values():
            reserved |= set(sl.weights) | set(sl.cfg.get("universe", []))
        self.coins = [co for co in m["coins"] if co not in reserved
                      and all(s in self.markets and s not in unavailable for s in (f"{co}TMN", f"{co}USDT"))]
        for co in m["coins"]:
            if co not in self.coins:
                self.dlog.write("coin_skipped", coin=co, reason="held or tradable by a holding sleeve" if co in reserved
                                else "market missing or not allowed for the package")
        self.vol24 = {co: self.markets[f"{co}TMN"].quote_volume_24h for co in self.coins}
        self.last_vol_refresh = time.time()
        f = c["fees"]
        self.fees = Fees(f["tmn_maker"], f["tmn_taker"], f["usdt_maker"], f["usdt_taker"])
        fees_by_symbol = {}
        if self.mode == "live":
            try:
                fees_by_symbol = self.client.fees()
                t = fees_by_symbol.get(f"{self.coins[0]}TMN") or {}
                if t.get("maker"):
                    self.fees = Fees(t["maker"], t["taker"], f["usdt_maker"], f["usdt_taker"])
            except WallexError as e:
                log.warning("fee lookup failed: %s", e)
            self.ex = LiveExec(self.client, fees_by_symbol)
        else:
            self.ex = PaperExec({"TMN": c["challenge"]["initial_capital_tmn"]}, fees_by_symbol, self.fees.__dict__)
        self.agent = SupervisorAgent(c["agent"], {
            "get_candidates": self.tool_candidates,
            "get_account_state": self.tool_account,
            "get_portfolio": self.tool_portfolio,
            "get_news": lambda topic="all": {"headlines": fetch_headlines(c["agent"].get("news_feeds", []), topic)},
        }, tool_specs=MM_TOOLS)
        self.load_state()
        if self.mode == "live":
            self.live_self_test()
            self.cancel_all_open_orders("start-up: a previous instance may have left orders on the exchange")
        self.dlog.write("startup", strategy="market_maker", coins=self.coins, fees=self.fees.__dict__,
                        agent_enabled=self.agent.enabled, instance=self.lock.id, config={"mm": m, "risk": c["risk"]})
        log.info("MM coins=%s fees=%s agent=%s", self.coins, self.fees, self.agent.enabled)

    def cancel_all_open_orders(self, why):
        try:
            oo = self.ex.open_orders()
        except WallexError as e:
            self.dlog.write("cancel_all_failed", error=str(e)[:200])
            return
        for cid in oo:
            self.ex.cancel(cid)
        self.orders = {}
        self.dirty()
        self.dlog.write("cancel_all", count=len(oo), why=why)

    def live_self_test(self):
        """Before trading real money: place one tiny BUY 20% below the market (cannot fill), find it in
        the open orders, read it, cancel it and confirm the cancel. Any failure stops the bot."""
        res = {"ok": False}
        try:
            books = self.client.depth_all()
            co = max((c for c in self.coins if books.get(f"{c}TMN", {}).get("bids")), key=lambda c: self.vol24.get(c, 0))
            mt = self.markets[f"{co}TMN"]
            price = mt.round_price(books[mt.symbol]["bids"][0][0] * 0.8, "BUY")
            qty = mt.round_qty(max(mt.min_notional * 1.3, 65000) / price)
            o = self.ex.place_limit(mt, "BUY", qty, price, prefix="T")
            cid = o["clientOrderId"]
            time.sleep(1.5)
            listed = cid in self.ex.open_orders()
            seen = self.ex.get(cid)
            self.ex.cancel(cid)
            time.sleep(1.5)
            after = self.ex.get(cid)
            cancelled = (after.get("active") is False) or str(after.get("status", "")).upper().startswith("CANCEL")
            res = {"ok": bool(listed and cancelled and float(seen.get("executedQty", 0) or 0) == 0), "symbol": mt.symbol,
                   "price": price, "qty": qty, "listed_in_open_orders": listed, "status_before": seen.get("status"),
                   "status_after_cancel": after.get("status"), "active_after_cancel": after.get("active")}
        except Exception as e:                       # noqa: BLE001 — any failure must stop live trading
            res["error"] = str(e)[:300]
        self.dlog.write("live_self_test", **res,
                        why="verify the real order path (place, list, read, cancel) before trading money")
        if not res["ok"]:
            raise SystemExit(f"live self-test failed: {res}")

    # ========================================================== persistence
    def save_state(self):
        st_ = {"orders": self.orders, "inv": self.inv, "policy": self.policy, "last_policy": self.last_policy,
               "stats": self.stats, "coin_stats": self.coin_stats, "risk": self.risk.state.__dict__,
               "llm_usage": self.agent.usage, "sleeves": {k: v.to_state() for k, v in self.sleeves.items()},
               "paper": getattr(self.ex, "bal", None) if self.mode == "shadow" else None,
               "paper_orders": getattr(self.ex, "orders", None) if self.mode == "shadow" else None,
               "portfolio_sig": self.portfolio_sig()}
        tmp = f"{self.state_path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st_, f, default=str)
        os.replace(tmp, self.state_path)

    def portfolio_sig(self) -> str:
        pf = {"portfolio": self.cfg.get("portfolio"), "capital": self.cfg["challenge"]["initial_capital_tmn"]}
        return hashlib.sha1(json.dumps(pf, sort_keys=True, default=str).encode()).hexdigest()[:12]

    def load_state(self):
        if not os.path.exists(self.state_path):
            return
        s = json.load(open(self.state_path, encoding="utf-8"))
        changed = s.get("portfolio_sig") != self.portfolio_sig()
        if changed and self.mode == "shadow":
            # a shadow test of a new portfolio must not inherit the old paper positions and sleeve weights
            os.replace(self.state_path, f"{self.state_path}.{int(time.time())}.old")
            self.dlog.write("state_reset", why="portfolio config changed: the shadow test restarts from the "
                                               "initial capital in Toman")
            return
        for k, v in (s.get("risk") or {}).items():
            setattr(self.risk.state, k, v)
        self.orders = s.get("orders") or {}
        self.inv = s.get("inv") or {}
        self.policy = s.get("policy") or {}
        self.last_policy = s.get("last_policy") or 0.0
        lo, hi = self.m.get("half_spread_bounds_pct", [0.8, 2.0])
        if any(not (lo <= float(h) <= hi) for h in (self.policy.get("markets") or {}).values()):
            self.last_policy = 0.0          # config bounds changed: let the AI decide again now
        self.stats.update(s.get("stats") or {})
        self.coin_stats = s.get("coin_stats") or {}
        if s.get("llm_usage"):
            self.agent.usage.update(s["llm_usage"])
        for k, v in (s.get("sleeves") or {}).items():
            if k in self.sleeves:
                sl = self.sleeves[k]
                sl.from_state(v)
                if changed:                 # live: real holdings stay; target weights follow the new config and
                    sl.weights = {**{a: 0.0 for a in sl.weights}, **sl.cfg["assets"]}   # dropped coins are sold
        if self.mode == "shadow" and s.get("paper"):
            self.ex.bal = s["paper"]
            self.ex.orders = s.get("paper_orders") or {}
            for o in self.ex.orders.values():
                if o["symbol"] in self.markets:
                    self.ex.markets[o["symbol"]] = self.markets[o["symbol"]]
        self.dlog.write("state_restored", inventory=list(self.inv), stats=self.stats)

    # ============================================================ account
    def bal(self) -> dict:
        if self._bal is None:
            self._bal = self.ex.balances()
        return self._bal

    def dirty(self):
        self._bal = None
        self._oo = None

    def equity(self, books) -> tuple[float, float]:
        """(total equity in TMN over EVERY asset held, market-maker inventory value only)"""
        b = self.bal()
        eq = b.get("TMN", {}).get("total", 0.0)
        mm_inv = 0.0
        mm = set(self.coins)
        for a, x in b.items():
            q = x.get("total", 0.0)
            if a == "TMN" or q <= 0:
                continue
            tb = books.get(f"{a}TMN", {}).get("bids") or [[0, 0]]
            v = q * tb[0][0]
            eq += v
            if a in mm:
                mm_inv += v
        return eq, mm_inv

    def sleeve_tmn_reserve(self, now) -> float:
        """Toman the holding sleeves still need to reach their targets: the market maker must not lock it in bids."""
        if not self.entries_allowed(now) or self.risk.wind_down(now) < 1:
            return 0.0
        r = 0.0
        for sl in self.sleeves.values():
            if sl.stopped:
                continue
            want = sl.capital * sum(sl.weights.values()) * sl.scale
            locked = sum(o["qty"] * o["price"] for o in sl.orders.values() if o["side"] == "BUY")
            r += max(0.0, want - sl.value(self._books)[0] - locked)
        return r

    def entries_allowed(self, now) -> bool:
        return (self.risk.entries_allowed_by_time(now) and not self.risk.halted(now)
                and not self.policy.get("pause") and not self.risk.daily_loss_hit(getattr(self, "_eq", 1e18)))

    def update_regime(self, now):
        """USDT/TMN trend over 6/24/48 h from hourly candles -> cap on holding-sleeve exposure."""
        if now - self.last_regime < 1800 and self.regime.get("ch48_pct") is not None:
            return
        self.last_regime = now
        try:
            c = self.client.candles("USDTTMN", "60", int(now - 4 * 86400), int(now))
        except Exception as e:                          # noqa: BLE001 — no data -> keep the previous regime
            log.warning("regime candles: %s", e)
            return
        cl, ts = c.get("c") or [], c.get("t") or []
        if len(cl) < 50:
            return
        last = cl[-1]

        def ch(hours):
            old = [p for t, p in zip(ts, cl) if t <= ts[-1] - hours * 3600]
            return round((last / old[-1] - 1) * 100, 2) if old else None
        r = {"usdt_tmn": last, "ch6_pct": ch(6), "ch24_pct": ch(24), "ch48_pct": ch(48)}
        pf = self.cfg.get("portfolio") or {}
        full, half = pf.get("regime_full_pct", 1.0), pf.get("regime_half_pct", 0.0)
        r["cap"] = 1.0 if (r["ch48_pct"] or 0) >= full else (0.5 if (r["ch48_pct"] or 0) >= half else 0.0)
        r["why"] = (f"USDT/TMN 48h {r['ch48_pct']:+.2f}%: exposure cap {r['cap']:.1f} "
                    f"(>= +{full}% full, else none: entered outside the rial-weakening regime the sleeves lost)")
        if r.get("cap") != self.regime.get("cap"):
            self.dlog.write("regime", **r)
        self.regime = r

    def tool_portfolio(self) -> dict:
        books = self._books
        out = {"regime": self.regime, "sleeves": {},
               "end_wind_down": {"share_still_held": self.risk.wind_down(time.time()),
                                 "schedule": "sleeves sold in 4 steps from 4 h before the end (Fri 19:50, 20:40, 21:30, "
                                             "22:20); the rest is sold as taker 40 min before the end"}}
        for k, sl in self.sleeves.items():
            v, c = sl.value(books)
            out["sleeves"][k] = {"capital_tmn": round(sl.capital), "weights": sl.weights, "scale_now": sl.scale,
                                 "value_tmn": round(v), "cost_tmn": round(c), "return_pct": round(sl.ret(books) * 100, 2),
                                 "pnl_tmn": round(sl.pnl(books)), "stopped": sl.stopped,
                                 "stop_pct": sl.cfg["stop_pct"], "universe": sl.cfg.get("universe")}
        return out

    def coin_qty(self, co, free=False) -> float:
        return self.bal().get(co, {}).get("free" if free else "total", 0.0)

    # ======================================================== fair value
    def update_fair_values(self, books, now):
        hl = 3 * 3600 // self.cfg["execution"]["loop_seconds"]
        for sym in [f"{co}USDT" for co in self.coins] + ["USDTTMN"]:
            b = books.get(sym)
            if b:
                top = (tuple(b["bids"][0]) if b["bids"] else None, tuple(b["asks"][0]) if b["asks"] else None)
                prev = self.ref_changed.get(sym)
                if not prev or prev[0] != top:
                    self.ref_changed[sym] = (top, now)
        ut = _mid(books.get("USDTTMN"))
        self.fv = {}
        for co in self.coins:
            cu, tm = _mid(books.get(f"{co}USDT")), _mid(books.get(f"{co}TMN"))
            if not (ut and cu and tm):
                continue
            fv_u = cu * ut
            p = tm / fv_u - 1
            if abs(p) < 0.05:                   # >5%: stale/illiquid book or halted coin, not a premium
                self.prem.setdefault(co, deque(maxlen=hl)).append((now, p))
            ps = [x for t, x in self.prem.get(co, []) if t >= now - self.m.get("premium_window_s", 1800)]
            if not ps:
                continue
            self.fv[co] = fv_u * (1 + st.median(ps))
            self.fvh.setdefault(co, deque(maxlen=hl)).append((now, self.fv[co]))

    def update_guards(self, books, now):
        """Guards only stop BUYING (selling inventory is always allowed)."""
        m = self.m
        for co in self.coins:
            reason = None
            if co not in self.fv:
                reason = "no fair value (book missing)"
            else:
                fh = self.fvh.get(co)
                old = next((v for t, v in fh if t >= now - m.get("fv_drop_window_s", 60)), None) if fh else None
                if old and self.fv[co] / old - 1 < -m.get("fv_drop", 0.004):
                    reason = f"fair value fell {(self.fv[co]/old-1)*1e4:.0f} bps in {m.get('fv_drop_window_s', 60)}s"
                tb = books.get(f"{co}TMN")
                ps = [x for t, x in self.prem.get(co, []) if t >= now - m.get("premium_window_s", 1800)]
                recent = [x for t, x in self.prem.get(co, []) if t >= now - m.get("slide_window_s", 120)]
                if not reason and ps and recent and min(recent) < st.median(ps) - m.get("slide_drop", 0.003):
                    reason = (f"Toman book sliding: premium {min(recent)*1e4:.0f} bps vs {st.median(ps)*1e4:.0f} "
                              f"bps baseline in {m.get('slide_window_s', 120)}s")
                ref = self.ref_changed.get(f"{co}USDT")
                if not reason and ref and now - ref[1] > m.get("ref_stale_s", 900):
                    reason = f"{co}USDT book frozen {(now-ref[1])/60:.0f} min: fair value unverifiable"
                if not reason and tb and tb["bids"] and tb["asks"] and (tb["asks"][0][0] / tb["bids"][0][0] - 1) > 0.05:
                    reason = "Toman spread > 5%: book broken"
            if (reason is not None) != (co in self.blocked):
                self.dlog.write("buy_blocked" if reason else "buy_unblocked", coin=co, why=reason or "guards pass")
            if reason:
                self.blocked[co] = reason
            else:
                self.blocked.pop(co, None)

    # ================================================================ tools
    def tool_candidates(self) -> dict:
        books, now = self._books, time.time()
        out = {}
        for co in self.coins:
            tb, cu = books.get(f"{co}TMN"), books.get(f"{co}USDT")
            row = {"vol24h_mtmn": round(self.vol24.get(co, 0) / 1e6)}
            if tb and tb["bids"] and tb["asks"]:
                row["spread_bps"] = round((tb["asks"][0][0] / tb["bids"][0][0] - 1) * 1e4, 1)
            if cu and cu["bids"] and cu["asks"]:
                row["usdt_spread_bps"] = round((cu["asks"][0][0] / cu["bids"][0][0] - 1) * 1e4, 1)
            ps = [x for t, x in self.prem.get(co, []) if t >= now - 1800]
            if ps:
                row["premium_bps"] = round(st.median(ps) * 1e4, 1)
            fh = [v for t, v in self.fvh.get(co, []) if t >= now - 1800]
            if len(fh) > 10:
                rets = [fh[i] / fh[i - 1] - 1 for i in range(1, len(fh))]
                row["fv_vol_bps"] = round(st.pstdev(rets) * math.sqrt(len(rets)) * 1e4, 1)
            row["buy_blocked"] = self.blocked.get(co)
            cs = self.coin_stats.get(co, {})
            row.update({"live_buys": cs.get("buys", 0), "live_sells": cs.get("sells", 0),
                        "round_trips": cs.get("round_trips", 0), "realised_pnl_tmn": round(cs.get("pnl", 0)),
                        "avg_round_trip_bps": round(cs["rt_bps_sum"] / cs["round_trips"], 1) if cs.get("round_trips") else None,
                        "quoted_now": co in (self.policy.get("markets") or {})})
            out[co] = row
        return {"units": "bps = 0.01%", "candidates": out}

    def tool_account(self) -> dict:
        books = self._books
        eq, inv_val = self.equity(books)
        init = self.cfg["challenge"]["initial_capital_tmn"]
        inv = {}
        for co, iv in self.inv.items():
            q = self.coin_qty(co)
            if q > 0 and co in self.fv:
                inv[co] = {"value_tmn": round(q * self.fv[co]), "cost_tmn": round(iv["cost"]),
                           "unrealised_pct": round((q * self.fv[co] / iv["cost"] - 1) * 100, 2) if iv["cost"] else None,
                           "age_min": round((time.time() - iv["t0"]) / 60)}
        return {"equity_tmn": round(eq), "return_pct": round((eq / init - 1) * 100, 3),
                "drawdown_pct": round(self.risk.drawdown_pct(eq), 3), "inventory": inv,
                "inventory_share_pct": round(inv_val / eq * 100, 1) if eq else None,
                "fills": self.stats["fills"], "round_trips": self.stats["round_trips"],
                "realised_pnl_tmn": round(self.stats["pnl_tmn"]),
                "minutes_to_end": round((self.risk.end_ts - time.time()) / 60)}

    # ============================================================ AI policy
    def fallback_policy(self, why: str) -> dict:
        """Deterministic stand-in when the LLM is unavailable: widest busy markets, fixed half-spread."""
        books = self._books
        score = {}
        for co in self.coins:
            tb = books.get(f"{co}TMN")
            if co in self.blocked or not (tb and tb["bids"] and tb["asks"]):
                continue
            spread = tb["asks"][0][0] / tb["bids"][0][0] - 1
            score[co] = min(spread, 0.02) * math.log10(max(self.vol24.get(co, 1), 10))
        pick = sorted(score, key=score.get, reverse=True)[: self.m.get("max_markets", 5)]
        h = self.m.get("default_half_spread_pct", 1.0)
        return {"markets": {co: h for co in pick}, "pause": False, "source": "fallback",
                "sleeves": {k: 1.0 for k in self.sleeves}, "beta_assets": [],
                "reasoning": f"Fallback ({why}): the {len(pick)} candidates with the best spread x volume, h={h}%."}

    def maybe_supervise(self, now):
        if self.policy and now - self.last_policy < self.cfg["agent"]["policy_every_minutes"] * 60:
            return
        m = self.m
        hlo, hhi = m.get("half_spread_bounds_pct", [0.8, 2.0])
        system = (MM_SYSTEM.replace("MAXM", str(m.get("max_markets", 5)))
                  .replace("HLO", str(hlo)).replace("HHI", str(hhi))
                  .replace("MINSP", str(m.get("min_spread_to_buy_bps", 50))))
        ctx = {"time": time.strftime("%Y-%m-%d %H:%M"), "trigger": "startup" if not self.policy else "scheduled",
               "account": self.tool_account(), "candidates": self.tool_candidates()["candidates"],
               "portfolio": self.tool_portfolio()}
        out, trace, prov = self.agent._run(system, ctx)
        pol = None
        if out and isinstance(out.get("markets"), dict):
            mk = {}
            for co, h in out["markets"].items():
                co = str(co).upper().replace("TMN", "")
                try:
                    h = max(hlo, min(hhi, float(h)))
                except (TypeError, ValueError):
                    continue
                if co in self.coins:
                    mk[co] = h
            mk = dict(list(mk.items())[: m.get("max_markets", 5)])
            if mk or self.sleeves:
                sl = {}
                for k in self.sleeves:
                    try:
                        sl[k] = max(0.0, min(1.0, float((out.get("sleeves") or {}).get(k, 1.0))))
                    except (TypeError, ValueError):
                        sl[k] = 1.0
                beta = [str(x).upper().replace("TMN", "") for x in (out.get("beta_assets") or [])]
                pol = {"markets": mk, "pause": bool(out.get("pause", False)), "source": f"llm:{prov}",
                       "sleeves": sl, "beta_assets": beta,
                       "reasoning": str(out.get("reasoning", ""))[:1500], "tool_trace": trace}
        if pol is None:
            pol = self.fallback_policy("LLM unavailable" if not self.agent.enabled else "LLM answer unusable")
        self.policy, self.last_policy = pol, now
        self.apply_sleeve_policy()
        self.dlog.write("policy", policy=pol, context=ctx, llm_spent_usd=round(self.agent.spent_usd(), 4),
                        llm_usage=self.agent.usage)

    def apply_sleeve_policy(self):
        """AI exposure per sleeve, capped by the deterministic USDT/TMN regime cap; AI-picked beta coins."""
        pol = self.policy or {}
        for k, sl in self.sleeves.items():
            ai = (pol.get("sleeves") or {}).get(k, 1.0)
            cap = self.regime.get("cap", 0.0)
            if sl.value(self._books)[1] > 0:
                cap = max(cap, sl.scale)       # backtest = enter in the regime, then hold: a later regime drop does
            sl.scale = round(min(ai, cap), 3)  # not force a sale (the AI or the disaster stop still can)
            uni = sl.cfg.get("universe")
            pick = [c for c in (pol.get("beta_assets") or []) if uni and c in uni and f"{c}TMN" in self.markets]
            held = sl.value(self._books)[1] > 0
            changed = set(pick) != {a for a, w in sl.weights.items() if w > 0}
            # every switch costs ~0.55% in fees: once built, the coin set may change at most every 3 hours
            if (uni and 2 <= len(pick) <= 4 and not sl.stopped and changed and self.risk.wind_down(time.time()) >= 1
                    and (not held or time.time() - sl.last_reweight > sl.cfg.get("min_reweight_s", 10800))):
                new = {c: round(1 / len(pick), 4) for c in pick}
                for old in sl.weights:
                    new.setdefault(old, 0.0)          # dropped coins get target 0 -> trimmed
                sl.weights = new
                sl.last_reweight = time.time()
                self.dlog.write("sleeve_reweight", sleeve=k, weights=new, why="AI picked a new coin set")

    def log_sleeves(self, now, books, eq):
        if now - self.last_sleeves_log < 60 or not self.sleeves:
            return
        self.last_sleeves_log = now
        new = not os.path.exists(self.sleeves_path)
        names = sorted(self.sleeves)
        with open(self.sleeves_path, "a", encoding="utf-8") as f:
            if new:
                f.write("ts,time,equity,mm_realised_pnl," + ",".join(f"{n}_value,{n}_pnl,{n}_ret_pct,{n}_scale" for n in names) + "\n")
            parts = []
            for n in names:
                sl = self.sleeves[n]
                v, _ = sl.value(books)
                parts.append(f"{v:.0f},{sl.pnl(books):.0f},{sl.ret(books)*100:.3f},{sl.scale}")
            f.write(f"{now:.0f},{time.strftime('%Y-%m-%d %H:%M:%S')},{eq:.0f},{self.stats['pnl_tmn']:.0f}," + ",".join(parts) + "\n")

    # ============================================================== fills
    def reconcile(self, books):
        for co, sides in list(self.orders.items()):
            for side in ("BUY", "SELL"):
                o = sides.get(side)
                if not o:
                    continue
                if self._oo is not None:
                    oo = self._oo.get(o["cid"])
                    if oo and float(oo.get("executedQty", 0) or 0) <= o["exec_seen"]:
                        continue
                try:
                    x = self.ex.get(o["cid"])
                except WallexError as e:
                    log.warning("get order %s: %s", o["cid"], e)
                    continue
                ex = float(x.get("executedQty", 0) or 0)
                if ex > o["exec_seen"]:
                    q = ex - o["exec_seen"]
                    o["exec_seen"] = ex
                    self.dirty()
                    self.on_fill(co, side, q, o["price"], o)
                if not x.get("active", True):
                    sides[side] = None

    def on_fill(self, co, side, qty, price, o):
        fee = self.fees.tmn_maker
        notional = qty * price
        self.stats["fills"] += 1
        self.stats["volume_tmn"] += notional
        self.stats["fees_tmn"] += notional * fee
        cs = self.coin_stats.setdefault(co, {"buys": 0, "sells": 0, "round_trips": 0, "pnl": 0.0, "rt_bps_sum": 0.0})
        iv = self.inv.setdefault(co, {"cost": 0.0, "t0": time.time()})
        held_before = self.coin_qty(co)  # balance refreshed by dirty(): includes this fill
        if side == "BUY":
            if iv["cost"] <= 0:
                iv["t0"] = time.time()
            iv["cost"] += notional
            self.stats["buys"] += 1
            cs["buys"] += 1
            self.dlog.write("fill", coin=co, side="BUY", qty=qty, price=price, notional_tmn=round(notional),
                            fair_value=o.get("fv"), edge_bps=o.get("edge_bps"), inventory_qty=held_before,
                            inventory_cost_tmn=round(iv["cost"]),
                            why=f"our maker bid {o.get('edge_bps')} bps below fair value was hit")
        else:
            qty_before = held_before + qty
            part = iv["cost"] * min(1.0, qty / qty_before) if qty_before > 0 else 0.0
            proceeds = notional * (1 - fee)
            pnl = proceeds - part
            iv["cost"] -= part
            self.stats["sells"] += 1
            self.stats["pnl_tmn"] += pnl
            cs["sells"] += 1
            cs["pnl"] += pnl
            if part > 0:
                self.stats["round_trips"] += 1
                cs["round_trips"] += 1
                cs["rt_bps_sum"] += (proceeds / part - 1) * 1e4
            self.dlog.write("fill", coin=co, side="SELL", qty=qty, price=price, notional_tmn=round(notional),
                            fair_value=o.get("fv"), pnl_tmn=round(pnl),
                            round_trip_bps=round((proceeds / part - 1) * 1e4, 1) if part else None,
                            why=f"our maker ask {o.get('edge_bps')} bps above fair value was lifted")
            if self.coin_qty(co) * (self.fv.get(co) or 0) < self.markets[f"{co}TMN"].min_notional:
                iv["cost"], iv["t0"] = 0.0, time.time()

    # ============================================================== exits
    def manage_exits(self, books, now):
        m = self.m
        for co, iv in list(self.inv.items()):
            q = self.coin_qty(co, free=False)
            mt = self.markets[f"{co}TMN"]
            fv = self.fv.get(co)
            if q <= 0 or not fv or q * fv < mt.min_notional or iv["cost"] <= 0:
                continue
            avg_vs_fv = q * fv / iv["cost"] - 1
            age_min = (now - iv["t0"]) / 60
            why = None
            if avg_vs_fv < -m.get("stop_pct", 1.2) / 100:
                why = f"stop-loss: inventory {avg_vs_fv*100:.2f}% below cost"
            elif age_min > m.get("max_hold_min", 90):
                why = f"time stop: inventory held {age_min:.0f} min"
            if why:
                self.exit_coin(co, books, why)

    def exit_coin(self, co, books, why):
        sides = self.orders.get(co, {})
        for side in ("BUY", "SELL"):
            if sides.get(side):
                self.ex.cancel(sides[side]["cid"])
        self.dirty()
        self.reconcile(books)
        self.orders[co] = {"BUY": None, "SELL": None}
        mt = self.markets[f"{co}TMN"]
        q = self.coin_qty(co, free=True)
        if q <= 0:
            return
        iv = self.inv.get(co, {"cost": 0.0})
        f = self.ex.market_sell(mt, q, books, self.fees.tmn_taker)
        self.dirty()
        proceeds = f.quote - f.fee_quote
        part = iv["cost"] * min(1.0, f.qty / q) if q else 0.0
        pnl = proceeds - part
        iv["cost"] -= part
        if self.coin_qty(co) * (self.fv.get(co) or 0) < mt.min_notional:
            iv["cost"], iv["t0"] = 0.0, time.time()
        self.stats["exits"] += 1
        self.stats["pnl_tmn"] += pnl
        self.stats["volume_tmn"] += f.quote
        self.stats["fees_tmn"] += f.fee_quote
        cs = self.coin_stats.setdefault(co, {"buys": 0, "sells": 0, "round_trips": 0, "pnl": 0.0, "rt_bps_sum": 0.0})
        cs["pnl"] += pnl
        if part > 0:
            cs["round_trips"] += 1
            cs["rt_bps_sum"] += (proceeds / part - 1) * 1e4
            self.stats["round_trips"] += 1
        self.dlog.write("exit", coin=co, qty=f.qty, avg_price=f.avg_price, pnl_tmn=round(pnl), why=why, orders=f.orders)

    def flatten(self, books, reason):
        for co in self.coins:
            for side in ("BUY", "SELL"):
                o = self.orders.get(co, {}).get(side)
                if o:
                    self.ex.cancel(o["cid"])
        self.dirty()
        self.reconcile(books)
        self.orders = {}
        for co in self.coins:
            mt = self.markets[f"{co}TMN"]
            q = self.coin_qty(co, free=True)
            if q > 0 and q * ((books.get(mt.symbol, {}).get("bids") or [[0, 0]])[0][0]) >= mt.min_notional:
                self.exit_coin(co, books, f"flatten: {reason}")
        self.dlog.write("flatten", reason=reason, equity=round(self.equity(books)[0]))

    # ================================================================ quotes
    def place(self, co, side, price, qty, fv, now):
        mt = self.markets[f"{co}TMN"]
        try:
            o = self.ex.place_limit(mt, side, qty, price, prefix="M")
        except WallexError as e:
            self.dlog.write("quote_failed", coin=co, side=side, error=str(e)[:200])
            return
        self.dirty()
        edge = round(abs(price / fv - 1) * 1e4, 1)
        self.orders.setdefault(co, {"BUY": None, "SELL": None})[side] = {
            "cid": o["clientOrderId"], "price": mt.round_price(price, side), "qty": mt.round_qty(qty),
            "t": now, "exec_seen": 0.0, "fv": round(fv, 6), "edge_bps": edge}
        self.dlog.write("quote", coin=co, side=side, price=mt.round_price(price, side), qty=mt.round_qty(qty),
                        size_tmn=round(qty * price), fair_value=round(fv, 6), edge_bps=edge,
                        half_spread_pct=(self.policy.get("markets") or {}).get(co),
                        why=("maker bid below fair value (AI-chosen half-spread, inventory skew)" if side == "BUY" else
                             "maker ask above fair value and above cost + fees"))

    def cancel(self, co, side, books):
        o = self.orders.get(co, {}).get(side)
        if o:
            self.ex.cancel(o["cid"])
            self.dirty()
            self.reconcile(books)
            if self.orders.get(co, {}).get(side):
                self.orders[co][side] = None

    def requote(self, books, eq, inv_val, now):
        m, pol = self.m, self.policy
        markets = pol.get("markets") or {}
        can_buy_time = (self.risk.entries_allowed_by_time(now) and not self.risk.halted(now)
                        and not self.risk.daily_loss_hit(eq) and not pol.get("pause"))
        max_inv_coin = eq * m.get("max_inventory_per_coin_pct", 25) / 100
        max_inv_total = eq * m.get("max_inventory_total_pct", 60) / 100
        quote_tmn = min(m.get("quote_tmn", 900000), eq * self.cfg["risk"]["max_position_pct"]) * self.risk.size_factor()
        reserve = self.sleeve_tmn_reserve(now)
        # 1) cancel first: quotes on markets the AI dropped, bids on blocked markets
        for co in list(self.orders):
            if co not in markets or co not in self.fv:
                self.cancel(co, "BUY", books)
                if self.coin_qty(co) * (self.fv.get(co) or 0) < self.markets[f"{co}TMN"].min_notional:
                    self.cancel(co, "SELL", books)
            elif co in self.blocked or not can_buy_time:
                self.cancel(co, "BUY", books)
        # 2) place / refresh
        for co in self.coins:
            fv = self.fv.get(co)
            tb = books.get(f"{co}TMN")
            if not fv or not tb or not tb["bids"] or not tb["asks"]:
                continue
            mt = self.markets[f"{co}TMN"]
            tick = 10 ** -mt.price_decimals
            best_bid, best_ask = tb["bids"][0][0], tb["asks"][0][0]
            held = self.coin_qty(co)
            held_val = held * fv
            iv = self.inv.get(co, {"cost": 0.0, "t0": now})
            h = markets.get(co)
            if h is None and held_val < mt.min_notional:
                continue
            h = (h or m.get("default_half_spread_pct", 1.0)) / 100
            skew = min(1.0, held_val / max_inv_coin) * h * m.get("skew_k", 0.5) if max_inv_coin else 0.0
            # ---- BUY (only where the Toman spread can pay the maker round trip at all)
            spread_bps = (best_ask / best_bid - 1) * 1e4
            wide_enough = spread_bps >= m.get("min_spread_to_buy_bps", 50)
            want_bid = (co in markets and co not in self.blocked and can_buy_time and wide_enough
                        and held_val < max_inv_coin - mt.min_notional and inv_val < max_inv_total)
            if not wide_enough and (self.orders.get(co) or {}).get("BUY"):
                self.cancel(co, "BUY", books)
            if want_bid:
                # at most one tick better than the current best bid: never pay up into the spread
                bid = min(fv * (1 - h - skew), best_bid + tick, best_ask - tick)
                ob = (self.orders.get(co) or {}).get("BUY") or {}
                own = (ob.get("qty", 0) - ob.get("exec_seen", 0)) * ob.get("price", 0)   # Toman our bid already locks
                room = min(quote_tmn, max_inv_coin - held_val, max_inv_total - inv_val,
                           max(0.0, self.bal().get("TMN", {}).get("free", 0.0) * 0.98 - reserve) + own)
                self._refresh(co, "BUY", bid, room / bid if bid else 0, fv, books, now)
            # ---- SELL (inventory only)
            free_q = held  # resting ask's qty is locked; held = total
            if held_val >= mt.min_notional:
                age_min = (now - iv["t0"]) / 60
                floor_mult = 1 + 2 * self.fees.tmn_maker + (m.get("min_profit_bps", 10) / 1e4
                                                            if age_min < m.get("breakeven_after_min", 30) else 0)
                avg_cost = iv["cost"] / held if held and iv["cost"] > 0 else 0
                ask = max(fv * (1 + h - skew), best_ask - tick, best_bid + tick, avg_cost * floor_mult)
                self._refresh(co, "SELL", ask, free_q, fv, books, now)

    def _refresh(self, co, side, price, qty, fv, books, now):
        mt = self.markets[f"{co}TMN"]
        price = mt.round_price(price, side)
        qty = mt.round_qty(qty)
        o = self.orders.get(co, {}).get(side)
        if o:
            moved = abs(price / o["price"] - 1)
            safer = price < o["price"] if side == "BUY" else price > o["price"]
            too_old = now - o["t"] > self.m.get("max_quote_age_s", 300)
            qty_off = side == "SELL" and abs(qty - (o["qty"] - o["exec_seen"])) > 10 ** -mt.qty_decimals
            thr = self.m.get("requote_bps", 15) / 1e4
            # a safer price (lower bid / higher ask) is applied sooner, but not for every tick of noise
            if not (moved > thr or (safer and moved > thr / 3) or too_old or qty_off):
                return
            self.cancel(co, side, books)
            if side == "SELL":
                qty = mt.round_qty(self.coin_qty(co, free=True))
        if qty <= 0 or qty < mt.min_qty or qty * price < max(mt.min_notional, self.cfg["risk"].get("min_order_tmn", 0)
                                                                if side == "BUY" else mt.min_notional):
            return
        self.place(co, side, price, qty, fv, now)

    # ============================================================ logging
    def log_rows(self, now, books, eq, inv_val):
        if now - self.last_books_log >= self.cfg["logging"].get("books_every_s", 10):
            syms = [f"{c}{q}" for c in self.coins for q in ("TMN", "USDT")] + ["USDTTMN"]
            hdr = ["ts"] + [f"{s_}_{k}" for s_ in syms for k in ("bid", "bidq", "ask", "askq")]
            if os.path.exists(self.books_path):
                with open(self.books_path, encoding="utf-8") as f:
                    old = f.readline().strip()
                if old != ",".join(hdr):        # the coin list changed: keep the old file, start one whose header fits
                    os.replace(self.books_path, f"{self.books_path[:-4]}_{int(now)}.csv")
            new = not os.path.exists(self.books_path)
            with open(self.books_path, "a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(hdr)
                row = [int(now)]
                for s_ in syms:
                    b = books.get(s_) or {"bids": [], "asks": []}
                    bb = b["bids"][0] if b["bids"] else ("", "")
                    aa = b["asks"][0] if b["asks"] else ("", "")
                    row += [bb[0], bb[1], aa[0], aa[1]]
                w.writerow(row)
            self.last_books_log = now
        if now - self.last_equity_log >= 60:
            new = not os.path.exists(self.equity_path)
            with open(self.equity_path, "a", encoding="utf-8") as f:
                if new:
                    f.write("ts,time,equity,drawdown_pct,fills,pnl_tmn,volume_tmn,usdt_tmn,coins_tmn\n")
                f.write(f"{now:.0f},{time.strftime('%Y-%m-%d %H:%M:%S')},{eq:.0f},"
                        f"{self.risk.drawdown_pct(eq):.3f},{self.stats['fills']},{self.stats['pnl_tmn']:.0f},"
                        f"{self.stats['volume_tmn']:.0f},0,{inv_val:.0f}\n")
            self.last_equity_log = now

    def poll_trade_tape(self, now):
        """Shadow only: feed the real trade tape of every market we have a paper order on."""
        every = self.m.get("paper_trades_every_s", 5)
        syms = sorted({o["symbol"] for o in self.ex.orders.values() if o["active"]})
        due = [s_ for s_ in syms if now - self.last_trade_poll.get(s_, 0) >= every][:3]
        for sym in due:
            self.last_trade_poll[sym] = now
            try:
                trades = self.client.trades(sym)
            except (WallexError, KeyError, TypeError) as e:
                log.info("trades %s: %s", sym, e)
                continue
            keys = {(t.get("timestamp") or t.get("time"), str(t.get("price")), str(t.get("quantity"))) for t in trades}
            if sym not in self.trade_seen:
                self.trade_seen[sym] = keys
                continue
            self.ex.on_trades(sym, trades, self.trade_seen[sym])
            if len(self.trade_seen[sym]) > 5000:
                self.trade_seen[sym] = keys

    # ================================================================= loop
    def step(self):
        now = time.time()
        if not self.lock.still_mine():
            self.dlog.write("instance_superseded", instance=self.lock.id,
                            why="a newer deployment took over the logs volume; stopping this one")
            raise SystemExit("superseded by a newer instance")
        self.lock.heartbeat()
        books = self.client.depth_all()
        self._books = books
        self.ex.on_books(books)
        if self.mode == "shadow":
            self.poll_trade_tape(now)
        self.stats["cycles"] += 1
        self.dirty()
        try:
            self._oo = self.ex.open_orders()
        except WallexError:
            self._oo = None
        if now - self.last_vol_refresh > 1800:
            try:
                mk = self.client.markets()
                self.vol24 = {co: mk[f"{co}TMN"].quote_volume_24h for co in self.coins if f"{co}TMN" in mk}
            except WallexError:
                pass
            self.last_vol_refresh = now
        self.update_fair_values(books, now)
        self.update_guards(books, now)
        self.update_regime(now)
        self.reconcile(books)
        eq, inv_val = self.equity(books)
        self._eq = eq
        for ev in self.risk.on_equity(eq, now):
            self.dlog.write(ev, equity=eq, reason=self.risk.state.kill_reason, paused_until=self.risk.state.paused_until)
        self.log_rows(now, books, eq, inv_val)
        self.log_sleeves(now, books, eq)
        if self.risk.must_flatten(now) or self.risk.halted(now):
            for sl in self.sleeves.values():
                if self.risk.halted(now) and not sl.stopped:
                    sl.stopped = "risk engine halt (circuit breaker / kill switch)"
                    self.dlog.write("sleeve_stop", sleeve=sl.name, why=sl.stopped)
                sl.step(books, now)
            if any(self.orders.get(co, {}).get(s) for co in self.coins for s in ("BUY", "SELL")) or inv_val > 0:
                self.flatten(books, "challenge_end" if self.risk.must_flatten(now) else
                             ("kill_switch" if self.risk.state.killed else "circuit_breaker_pause"))
            self.save_state()
            return
        wd = self.risk.wind_down(now)
        if self.sleeves and wd != getattr(self, "_last_wind", 1.0):
            self._last_wind = wd
            self.dlog.write("wind_down_step", share_still_held=wd,
                            why="end of challenge: holding sleeves are sold in steps, not all at once")
        self.maybe_supervise(now)
        self.apply_sleeve_policy()
        for sl in self.sleeves.values():
            sl.step(books, now)
        self.manage_exits(books, now)
        eq, inv_val = self.equity(books)
        self.requote(books, eq, inv_val, now)
        self.save_state()

    def run(self):
        self.setup()
        log.info("market maker running in %s mode", self.mode.upper())
        while time.time() < self.risk.end_ts + 600:
            t0 = time.time()
            try:
                self.step()
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                self.stats["errors"] += 1
                self.dlog.write("error", error=str(e)[:400], trace=traceback.format_exc()[-1500:])
                log.error("step error: %s", e)
                time.sleep(5)
            time.sleep(max(0.2, self.cfg["execution"]["loop_seconds"] - (time.time() - t0)))
        self.dlog.write("finished", stats=self.stats)
