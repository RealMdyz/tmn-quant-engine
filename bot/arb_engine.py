"""Main engine: hedged fair-value arbitrage + AI supervision. Live and shadow share
this exact code; only the execution object differs.

Cycle (every `loop_seconds`, ~2s):
  1. ONE request for all order books  -> liquidation value of every coin
  2. reconcile our resting quotes     -> detect (partial) fills
  3. hedge every fill immediately on the coin/USDT book; score it; teach the bandit
  4. manage USDT inventory (maker sell to Toman, minus what the agent wants to hold)
  5. re-quote: one maker BUY per enabled coin at  LV * (1 - fees - margin)
  6. risk: equity, drawdown kill-switch, daily loss limit, end-of-challenge flatten
  7. AI supervisor every N minutes (or immediately on an anomaly)
  8. log every decision (JSONL) + equity curve + deviation recorder; persist state
"""
from __future__ import annotations

import csv
import json
import os
import random
import time
import logging
import traceback
from collections import deque

from .agent import SupervisorAgent, fetch_headlines
from .arb import Fees, build_bandits, liquidation_value
from .brokers import LiveExec, PaperExec
from .decision_log import DecisionLog
from .risk import RiskManager
from .wallex_client import WallexClient, WallexError

log = logging.getLogger("engine")


class ArbEngine:
    def __init__(self, cfg: dict, mode: str, api_key: str | None, client: WallexClient | None = None):
        assert mode in ("live", "shadow")
        self.cfg, self.mode = cfg, mode
        self.client = client or WallexClient(api_key, per_sec=cfg["execution"].get("max_requests_per_sec", 5))
        ld = cfg["logging"]["dir"]
        os.makedirs(ld, exist_ok=True)
        self.ld = ld
        self.dlog = DecisionLog(os.path.join(ld, f"decisions_{mode}.jsonl"), mode)
        self.state_path = os.path.join(ld, f"state_{mode}.json")
        self.equity_path = os.path.join(ld, f"equity_{mode}.csv")
        self.dev_path = os.path.join(ld, f"deviations_{mode}.csv")
        self.risk = RiskManager(cfg["risk"], cfg["challenge"])
        self.rng = random.Random(cfg.get("seed", 7))
        self.quotes: dict[str, dict] = {}          # coin -> {cid, price, qty, margin, lv, t, exec_seen}
        self.usdt_order: dict | None = None
        self.policy: dict = {}
        self.last_policy = 0.0
        self.dev_hist: dict[str, deque] = {}
        self.usdt_hist: deque = deque(maxlen=20000)
        self.stats = {"fills": 0, "hedges": 0, "hedge_failures": 0, "pnl_tmn": 0.0, "cycles": 0, "errors": 0,
                      "volume_tmn": 0.0, "requotes": 0}
        self.coin_stats: dict[str, dict] = {}
        self.last_equity_log = self.last_dev_log = 0.0
        self.anomaly_flag = None
        self._bal = None
        self._oo = None

    # ================================================================ setup
    def setup(self):
        c = self.cfg
        self.markets = self.client.markets()
        try:
            pkg = self.client.prop_package(c["challenge"]["package_id"])
            self.unavailable = set(pkg.get("unavailableMarkets") or [])
        except WallexError as e:
            log.warning("package lookup failed (%s) — using config whitelist only", e)
            self.unavailable = set()
        self.coins = []
        for coin in c["arb"]["coins"]:
            ok = all(s in self.markets and s not in self.unavailable for s in (f"{coin}TMN", f"{coin}USDT"))
            (self.coins.append(coin) if ok else
             self.dlog.write("coin_skipped", coin=coin, reason="market missing or not allowed for the package"))
        if "USDTTMN" in self.unavailable:
            raise SystemExit("USDTTMN not allowed — strategy cannot convert back to Toman")
        f = c["fees"]
        self.fees = Fees(f["tmn_maker"], f["tmn_taker"], f["usdt_maker"], f["usdt_taker"])
        fees_by_symbol = {}
        if self.mode == "live":
            try:
                live_fees = self.client.fees()
                tm = live_fees.get("USDTTMN") or {}
                cu = live_fees.get(f"{self.coins[0]}USDT") if self.coins else None
                if tm.get("maker"):
                    self.fees = Fees(tm["maker"], tm["taker"], (cu or {}).get("maker", f["usdt_maker"]),
                                     (cu or {}).get("taker", f["usdt_taker"]))
                fees_by_symbol = live_fees
            except WallexError as e:
                log.warning("fee lookup failed: %s", e)
        if self.mode == "live":
            self.ex = LiveExec(self.client, fees_by_symbol)
        else:
            self.ex = PaperExec({"TMN": c["challenge"]["initial_capital_tmn"]}, fees_by_symbol, self.fees.__dict__)
        priors = c["arb"]["priors"]
        pfile = os.path.join(self.ld, "backtest", "arb_summary.json")
        if c["arb"].get("use_backtest_priors") and os.path.exists(pfile):
            priors = {k: v for k, v in json.load(open(pfile))["priors"].items() if k in self.coins} or priors
        self.bandits = build_bandits({k: v for k, v in priors.items() if k in self.coins})
        self.agent = SupervisorAgent(c["agent"], {
            "get_market_stats": self.tool_market_stats,
            "get_account_state": self.tool_account_state,
            "get_news": lambda topic="all": {"headlines": fetch_headlines(c["agent"].get("news_feeds", []), topic)},
            "get_usdt_tmn_trend": self.tool_usdt_trend,
        })
        self.load_state()
        self.dlog.write("startup", coins=self.coins, fees=self.fees.__dict__, round_trip=self.fees.round_trip,
                        agent_enabled=self.agent.enabled, unavailable_count=len(self.unavailable),
                        config={k: c[k] for k in ("arb", "risk", "execution", "challenge")})
        log.info("coins=%s fees=%s agent=%s", self.coins, self.fees, self.agent.enabled)

    # ========================================================== persistence
    def save_state(self):
        st = {"quotes": self.quotes, "usdt_order": self.usdt_order, "risk": self.risk.state.__dict__,
              "stats": self.stats, "coin_stats": self.coin_stats, "policy": self.policy,
              "llm_usage": self.agent.usage,
              "bandits": {k: [a.__dict__ for a in b.arms] for k, b in self.bandits.items()},
              "paper": getattr(self.ex, "bal", None) if self.mode == "shadow" else None,
              "paper_orders": getattr(self.ex, "orders", None) if self.mode == "shadow" else None}
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, default=str)
        os.replace(tmp, self.state_path)

    def load_state(self):
        if not os.path.exists(self.state_path):
            return
        st = json.load(open(self.state_path, encoding="utf-8"))
        for k, v in (st.get("risk") or {}).items():
            setattr(self.risk.state, k, v)
        self.stats.update(st.get("stats") or {})
        self.coin_stats = st.get("coin_stats") or {}
        self.policy = st.get("policy") or {}
        if st.get("llm_usage"):
            self.agent.usage.update(st["llm_usage"])
        for coin, arms in (st.get("bandits") or {}).items():
            if coin in self.bandits:
                for a, saved in zip(self.bandits[coin].arms, arms):
                    a.n, a.sum_r, a.sum_r2 = saved["n"], saved["sum_r"], saved["sum_r2"]
        self.quotes = st.get("quotes") or {}
        self.usdt_order = st.get("usdt_order")
        if self.mode == "shadow" and st.get("paper"):
            self.ex.bal = st["paper"]
            self.ex.orders = st.get("paper_orders") or {}
            for o in self.ex.orders.values():
                if o["symbol"] in self.markets:
                    self.ex.markets[o["symbol"]] = self.markets[o["symbol"]]
        self.dlog.write("state_restored", quotes=list(self.quotes), stats=self.stats)

    # ============================================================== account
    def bal(self, fresh=False) -> dict:
        """Balances, cached within a cycle (invalidated after every order action)."""
        if fresh or self._bal is None:
            self._bal = self.ex.balances()
        return self._bal

    def dirty(self):
        self._bal = None

    def equity(self, books) -> tuple[float, dict, dict]:
        bal = self.bal()
        ut = books.get("USDTTMN", {}).get("bids") or [[0, 0]]
        parts = {"TMN": bal.get("TMN", {}).get("total", 0.0)}
        parts["USDT"] = bal.get("USDT", {}).get("total", 0.0) * ut[0][0]
        for coin in self.coins:
            q = bal.get(coin, {}).get("total", 0.0)
            if q > 0:
                b = books.get(f"{coin}TMN", {}).get("bids") or [[0, 0]]
                parts[coin] = q * b[0][0]
        return sum(parts.values()), parts, bal

    # ================================================================ tools
    def tool_market_stats(self, coin: str) -> dict:
        h = list(self.dev_hist.get(coin, []))
        devs = [d for _, d in h]
        cs = self.coin_stats.get(coin, {})
        out = {"coin": coin, "samples": len(devs)}
        if devs:
            import statistics as st
            out.update({"dev_now_pct": round(devs[-1] * 100, 3), "dev_mean_pct": round(st.mean(devs) * 100, 3),
                        "dev_std_pct": round(st.pstdev(devs) * 100, 3), "dev_min_pct": round(min(devs) * 100, 3),
                        "minutes_below_-2pct": round(sum(1 for d in devs if d < -0.02) *
                                                     self.cfg["execution"]["loop_seconds"] / 60, 1)})
        out.update({"live_fills": cs.get("fills", 0), "realised_pnl_tmn": round(cs.get("pnl", 0)),
                    "avg_fill_bps": round(cs.get("pnl_bps_sum", 0) / cs["fills"], 1) if cs.get("fills") else None,
                    "bandit": self.bandits[coin].summary() if coin in self.bandits else None})
        return out

    def tool_account_state(self) -> dict:
        books = self._last_books
        eq, parts, _ = self.equity(books)
        init = self.cfg["challenge"]["initial_capital_tmn"]
        return {"equity_tmn": round(eq), "return_pct": round((eq / init - 1) * 100, 3),
                "drawdown_pct": round(self.risk.drawdown_pct(eq), 3),
                "holdings_tmn": {k: round(v) for k, v in parts.items()},
                "open_quotes": {k: {"price": v["price"], "margin_pct": round(v["margin"] * 100, 2)}
                                for k, v in self.quotes.items()},
                "fills": self.stats["fills"], "realised_pnl_tmn": round(self.stats["pnl_tmn"]),
                "minutes_to_end": round((self.risk.end_ts - time.time()) / 60)}

    def tool_usdt_trend(self) -> dict:
        h = list(self.usdt_hist)
        if not h:
            return {"error": "no data yet"}
        now_t, now_p = h[-1]

        def ch(sec):
            old = [p for t, p in h if t <= now_t - sec]
            return round((now_p / old[-1] - 1) * 100, 3) if old else None
        return {"usdt_tmn": now_p, "change_1h_pct": ch(3600), "change_6h_pct": ch(21600), "change_24h_pct": ch(86400)}

    # ============================================================ supervisor
    def maybe_supervise(self, now):
        due = now - self.last_policy > self.cfg["agent"]["policy_every_minutes"] * 60
        if not (due or not self.policy or self.anomaly_flag):
            return
        ctx = {"time": time.strftime("%Y-%m-%d %H:%M"), "coins": self.coins,
               "trigger": self.anomaly_flag or ("startup" if not self.policy else "scheduled"),
               "round_trip_fee_pct": round(self.fees.round_trip * 100, 3),
               "snapshot": {c: {"dev_now_pct": round(self.dev_hist[c][-1][1] * 100, 3) if self.dev_hist.get(c) else None,
                                "fills": self.coin_stats.get(c, {}).get("fills", 0)} for c in self.coins},
               "account": self.tool_account_state()}
        self.policy = self.agent.decide(ctx, self.coins)
        self.last_policy = now
        self.anomaly_flag = None
        self.dlog.write("policy", policy=self.policy, context=ctx,
                        llm_spent_usd=round(self.agent.spent_usd(), 4), llm_usage=self.agent.usage)

    def detect_anomaly(self, coin, dev):
        """Persistent dislocation (e.g. withdrawals halted) -> ask the agent now."""
        h = self.dev_hist[coin]
        win = int(self.cfg["arb"]["anomaly_minutes"] * 60 / self.cfg["execution"]["loop_seconds"])
        if len(h) >= win and all(d < -self.cfg["arb"]["anomaly_dev"] for _, d in list(h)[-win:]):
            if coin in (self.policy.get("enabled_coins") or []) and not self.anomaly_flag:
                self.anomaly_flag = f"{coin} Toman price persistently {dev*100:.2f}% below liquidation value"
                if not self.agent.enabled:      # deterministic fallback: disable the coin
                    self.policy["enabled_coins"] = [c for c in self.policy.get("enabled_coins", []) if c != coin]

    # ================================================================ fills
    def process_quote(self, coin, books):
        q = self.quotes.get(coin)
        if not q:
            return
        if self._oo is not None:                       # cheap path: unchanged resting order -> no request
            oo = self._oo.get(q["cid"])
            if oo and float(oo.get("executedQty", 0) or 0) <= q["exec_seen"]:
                return
        try:
            o = self.ex.get(q["cid"])
        except WallexError as e:
            log.warning("get order %s: %s", q["cid"], e)
            return
        executed = float(o.get("executedQty", 0) or 0)
        new = executed - q["exec_seen"]
        if new > 0:
            self.dirty()
            q["exec_seen"] = executed
            self.on_fill(coin, q, new, books)
        if not o.get("active", True):
            self.quotes.pop(coin, None)

    def on_fill(self, coin, q, gross_qty, books):
        mt = self.markets[f"{coin}TMN"]
        mu = self.markets[f"{coin}USDT"]
        cost_tmn = gross_qty * q["price"]
        self.stats["fills"] += 1
        self.stats["volume_tmn"] += cost_tmn
        # hedge everything we hold of this coin (includes earlier dust)
        bal = self.bal()
        free = bal.get(coin, {}).get("free", 0.0)
        hedge = self.ex.market_sell(mu, free, books, self.fees.usdt_taker)
        self.dirty()
        ut_bid = (books.get("USDTTMN", {}).get("bids") or [[0, 0]])[0][0]
        if hedge.qty > 0:
            usdt_net = hedge.quote - hedge.fee_quote
            tmn_value = usdt_net * ut_bid * (1 - self.fees.tmn_taker)        # conservative conversion
            spent = cost_tmn * hedge.qty / max(gross_qty * (1 - self.fees.tmn_maker), 1e-12)
            r = tmn_value / spent - 1 if spent else 0.0
            pnl = tmn_value - spent
            self.stats["hedges"] += 1
            self.stats["pnl_tmn"] += pnl
            cs = self.coin_stats.setdefault(coin, {"fills": 0, "pnl": 0.0, "pnl_bps_sum": 0.0})
            cs["fills"] += 1
            cs["pnl"] += pnl
            cs["pnl_bps_sum"] += r * 1e4
            self.bandits[coin].update(q["margin"], r)
            self.dlog.write("fill_hedged", coin=coin, quote_price=q["price"], gross_qty=gross_qty,
                            liquidation_value_at_quote=q["lv"], margin=q["margin"],
                            hedge_qty=hedge.qty, hedge_avg_usdt=hedge.avg_price, usdt_tmn_bid=ut_bid,
                            net_return_bps=round(r * 1e4, 1), pnl_tmn=round(pnl),
                            why=f"Toman seller hit our bid {((q['price']/q['lv'])-1)*100:.2f}% below liquidation value; "
                                f"sold on {coin}USDT immediately to lock the spread",
                            orders=hedge.orders)
        else:
            self.stats["hedge_failures"] += 1
            self.dlog.write("hedge_pending", coin=coin, qty=free, note=hedge.note,
                            why="filled amount below USDT-market minimum or hedge failed; will retry/accumulate")

    def sweep_inventory(self, books):
        """Any coin left over (partial fills below the USDT-market minimum, rounding dust) is
        hedged as soon as it is large enough — the strategy never wants directional coin exposure."""
        bal = self.bal()
        ut_bid = books["USDTTMN"]["bids"][0][0]
        for coin in self.coins:
            free = bal.get(coin, {}).get("free", 0.0)
            mu = self.markets[f"{coin}USDT"]
            b = books.get(mu.symbol, {}).get("bids")
            if free <= 0 or not b:
                continue
            if free * b[0][0] >= mu.min_notional * 1.05 and free >= mu.min_qty:
                f = self.ex.market_sell(mu, free, books, self.fees.usdt_taker)
                self.dirty()
                if f.qty:
                    self.dlog.write("inventory_sweep", coin=coin, qty=f.qty, avg_usdt=f.avg_price,
                                    value_tmn=round(f.quote * ut_bid), orders=f.orders)

    # ========================================================= USDT manager
    def manage_usdt(self, books, eq, flatten=False):
        m = self.markets["USDTTMN"]
        ub = books.get("USDTTMN")
        if not ub or not ub["asks"] or not ub["bids"]:
            return
        if self.usdt_order:
            try:
                o = self.ex.get(self.usdt_order["cid"])
                ex = float(o.get("executedQty", 0) or 0)
                if ex > self.usdt_order["exec_seen"]:
                    self.stats["volume_tmn"] += (ex - self.usdt_order["exec_seen"]) * self.usdt_order["price"]
                    self.usdt_order["exec_seen"] = ex
                    self.dlog.write("usdt_converted", qty=ex, price=self.usdt_order["price"], mode="maker")
                if not o.get("active", True):
                    self.usdt_order = None
            except WallexError:
                pass
        bal = self.bal().get("USDT", {"free": 0.0, "total": 0.0})
        hold_frac = 0.0 if flatten else float(self.policy.get("usdt_hold_frac", 0.0))
        target_usdt = eq * hold_frac / ub["bids"][0][0]
        excess = bal["total"] - target_usdt
        min_qty = max(m.min_qty, m.min_notional / ub["bids"][0][0]) * 1.05
        if flatten:
            if self.usdt_order:
                self.ex.cancel(self.usdt_order["cid"])
                self.usdt_order = None
            self.dirty()
            free = self.bal().get("USDT", {}).get("free", 0.0)
            if free > min_qty:
                f = self.ex.market_sell(m, free, books, self.fees.tmn_taker)
                self.dlog.write("usdt_converted", qty=f.qty, avg=f.avg_price, mode="taker_flatten", orders=f.orders)
            return
        best_ask = ub["asks"][0][0]
        if self.usdt_order:
            drift = abs(self.usdt_order["price"] / best_ask - 1)
            too_old = time.time() - self.usdt_order["t"] > self.cfg["arb"].get("usdt_maker_timeout_s", 900)
            if drift > 0.0008 or excess < min_qty or too_old:
                self.ex.cancel(self.usdt_order["cid"])
                self.dirty()
                self.usdt_order = None
                if too_old and excess > min_qty:       # maker did not fill in time -> taker, cap USDT exposure
                    free = self.bal().get("USDT", {}).get("free", 0.0)
                    f = self.ex.market_sell(m, min(free, excess), books, self.fees.tmn_taker)
                    self.dirty()
                    self.dlog.write("usdt_converted", qty=f.qty, avg=f.avg_price, mode="taker_after_timeout",
                                    orders=f.orders)
            return
        free = bal["free"]
        qty = min(free, excess)
        if qty > min_qty:
            price = max(best_ask, ub["bids"][0][0] + 10 ** -m.price_decimals)   # join best ask, never cross
            try:
                o = self.ex.place_limit(m, "SELL", qty, price, prefix="U")
                self.dirty()
                self.usdt_order = {"cid": o["clientOrderId"], "price": price, "qty": qty, "exec_seen": 0.0, "t": time.time()}
            except WallexError as e:
                log.warning("usdt sell failed: %s", e)

    # ================================================================ quotes
    def requote(self, books, eq, now):
        c = self.cfg
        enabled = set(self.policy.get("enabled_coins") or []) if not self.policy.get("pause") else set()
        can_trade = (self.risk.entries_allowed_by_time(now) and not self.risk.state.killed
                     and not self.risk.daily_loss_hit(eq))
        tmn_free_total = self.bal().get("TMN", {}).get("free", 0.0)
        # active set: the K enabled markets with the highest expected profit per hour (posterior, no sampling)
        def expected(coin):
            return max(a.posterior()[0] * a.fill_rate for a in self.bandits[coin].arms)
        ranked = sorted((co for co in self.coins if co in enabled and expected(co) > 0), key=expected, reverse=True)
        active = set(ranked[: c["arb"].get("max_active_quotes", 8)])
        locked_in_quotes = sum(q["qty"] * q["price"] for q in self.quotes.values())
        per_quote = max(0.0, (tmn_free_total + locked_in_quotes) * 0.97 / max(1, len(active)))
        for coin in self.coins:
            q = self.quotes.get(coin)
            lv = liquidation_value(books, coin)
            tb = books.get(f"{coin}TMN")
            if not lv or not tb or not tb["asks"] or not tb["bids"] or coin not in active or not can_trade:
                if q:
                    self.ex.cancel(q["cid"]); self.dirty(); self._oo = None
                    self.process_quote(coin, books)
                    self.quotes.pop(coin, None)
                continue
            bandit = self.bandits[coin]
            if not q or now - q.get("t_choice", 0) > c["arb"]["rechoose_margin_s"]:
                margin, scores = bandit.choose(self.rng, float(self.policy.get("margin_mult", 1.0)))
                choice_t = now
                if margin is None:
                    if q:
                        self.ex.cancel(q["cid"]); self.dirty(); self._oo = None
                        self.process_quote(coin, books)
                        self.quotes.pop(coin, None)
                    continue
            else:
                margin, scores, choice_t = q["margin"], None, q["t_choice"]
            mt = self.markets[f"{coin}TMN"]
            target = lv * (1 - self.fees.round_trip - margin)
            best_ask = tb["asks"][0][0]
            if target >= best_ask:
                # the book already offers a price below liquidation value: take it (taker fee instead of maker)
                taker_ok = best_ask <= lv * (1 - (self.fees.tmn_taker + self.fees.usdt_taker + self.fees.tmn_taker) - margin)
                target = best_ask if taker_ok else best_ask - 10 ** -mt.price_decimals
            price = mt.round_price(target, "BUY")
            if q:
                safe = price >= q["price"]          # existing bid not above the new safe level?
                moved = abs(price / q["price"] - 1) > c["arb"]["requote_threshold"]
                stale = now - q["t"] > c["arb"]["max_quote_age_s"]
                if not (moved or stale or not safe):
                    continue
                self.ex.cancel(q["cid"]); self.dirty(); self._oo = None
                self.process_quote(coin, books)          # capture any fill that happened before cancel
                self.quotes.pop(coin, None)
                self.stats["requotes"] += 1
                tmn_free_total = self.bal().get("TMN", {}).get("free", 0.0)
            size_tmn = min(c["arb"]["quote_tmn"], eq * c["risk"]["max_position_pct"], per_quote,
                           tmn_free_total * 0.98)
            ut_bid = books["USDTTMN"]["bids"][0][0]
            min_hedge_tmn = self.markets[f"{coin}USDT"].min_notional * ut_bid * 1.2
            if size_tmn < max(c["risk"]["min_order_tmn"], mt.min_notional, min_hedge_tmn):
                continue
            qty = mt.round_qty(size_tmn / price)
            try:
                o = self.ex.place_limit(mt, "BUY", qty, price)
                self.dirty()
            except WallexError as e:
                self.dlog.write("quote_failed", coin=coin, error=str(e)[:200])
                continue
            self.quotes[coin] = {"cid": o["clientOrderId"], "price": price, "qty": qty, "margin": margin,
                                 "lv": lv, "t": now, "t_choice": choice_t, "exec_seen": 0.0}
            tmn_free_total -= qty * price
            if scores is not None:
                self.dlog.write("quote", coin=coin, price=price, qty=qty, size_tmn=round(qty * price),
                                liquidation_value=round(lv, 6), discount_pct=round((price / lv - 1) * 100, 3),
                                margin_pct=round(margin * 100, 3), bandit_scores_bps_per_hour=scores,
                                why="resting maker bid below liquidation value minus fees+margin (Thompson-sampled)")

    # ============================================================== flatten
    def flatten(self, books, reason):
        for coin, q in list(self.quotes.items()):
            self.ex.cancel(q["cid"]); self.dirty(); self._oo = None
            self.process_quote(coin, books)
        self.quotes.clear()
        bal = self.bal()
        for coin in self.coins:
            free = bal.get(coin, {}).get("free", 0.0)
            if free <= 0:
                continue
            mu, mt = self.markets[f"{coin}USDT"], self.markets[f"{coin}TMN"]
            b = books.get(mt.symbol, {}).get("bids") or [[0, 0]]
            if free * b[0][0] >= mt.min_notional:
                f = self.ex.market_sell(mt, free, books, self.fees.tmn_taker)
            else:
                f = self.ex.market_sell(mu, free, books, self.fees.usdt_taker)
            if f.qty:
                self.dlog.write("flatten_coin", coin=coin, reason=reason, qty=f.qty, avg=f.avg_price, orders=f.orders)
        self.manage_usdt(books, 0, flatten=True)

    # ================================================================= loop
    def log_rows(self, now, books, eq, parts):
        if now - self.last_dev_log >= 30:
            new = not os.path.exists(self.dev_path)
            with open(self.dev_path, "a", newline="") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["ts"] + [f"{c}_dev_bps" for c in self.coins] + ["usdt_tmn_bid"])
                w.writerow([int(now)] + [round(self.dev_hist[c][-1][1] * 1e4, 1) if self.dev_hist.get(c) else ""
                                         for c in self.coins] + [books["USDTTMN"]["bids"][0][0]])
            self.last_dev_log = now
        if now - self.last_equity_log >= 60:
            new = not os.path.exists(self.equity_path)
            with open(self.equity_path, "a", encoding="utf-8") as f:
                if new:
                    f.write("ts,time,equity,drawdown_pct,fills,pnl_tmn,volume_tmn,usdt_tmn,coins_tmn\n")
                f.write(f"{now:.0f},{time.strftime('%Y-%m-%d %H:%M:%S')},{eq:.0f},"
                        f"{self.risk.drawdown_pct(eq):.3f},{self.stats['fills']},{self.stats['pnl_tmn']:.0f},"
                        f"{self.stats['volume_tmn']:.0f},{parts.get('USDT', 0):.0f},"
                        f"{sum(v for k, v in parts.items() if k not in ('TMN', 'USDT')):.0f}\n")
            self.last_equity_log = now

    def step(self):
        now = time.time()
        books = self.client.depth_all()
        self._last_books = books
        self.ex.on_books(books)
        self.stats["cycles"] += 1
        self._bal = None
        try:
            self._oo = self.ex.open_orders()
        except WallexError:
            self._oo = None
        ut = books.get("USDTTMN")
        if not ut or not ut["bids"]:
            return
        self.usdt_hist.append((now, ut["bids"][0][0]))
        for coin in self.coins:
            lv = liquidation_value(books, coin)
            tb = books.get(f"{coin}TMN")
            if lv and tb and tb["bids"]:
                dev = tb["bids"][0][0] / lv - 1
                self.dev_hist.setdefault(coin, deque(maxlen=6 * 3600 // self.cfg["execution"]["loop_seconds"])).append((now, dev))
                self.detect_anomaly(coin, dev)
        for coin in list(self.quotes):
            self.process_quote(coin, books)
        eq, parts, _ = self.equity(books)
        for ev in self.risk.on_equity(eq, now):
            self.dlog.write(ev, equity=eq, reason=self.risk.state.kill_reason)
        self.log_rows(now, books, eq, parts)
        if self.risk.must_flatten(now) or self.risk.state.killed:
            self.flatten(books, "challenge_end" if self.risk.must_flatten(now) else "kill_switch")
            self.save_state()
            return
        self.maybe_supervise(now)
        if now - getattr(self, "_last_sweep", 0) > 60:
            self.sweep_inventory(books)
            self._last_sweep = now
        self.manage_usdt(books, eq)
        self.requote(books, eq, now)
        self.save_state()

    def run(self):
        self.setup()
        log.info("arb engine running in %s mode", self.mode.upper())
        while time.time() < self.risk.end_ts + 600:
            t0 = time.time()
            try:
                self.step()
            except KeyboardInterrupt:
                raise
            except Exception as e:
                self.stats["errors"] += 1
                self.dlog.write("error", error=str(e)[:400], trace=traceback.format_exc()[-1500:])
                log.error("step error: %s", e)
                time.sleep(5)
            time.sleep(max(0.2, self.cfg["execution"]["loop_seconds"] - (time.time() - t0)))
        self.dlog.write("finished", stats=self.stats)
