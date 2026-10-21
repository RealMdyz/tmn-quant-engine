"""Main trading engine (live + shadow). One loop, one code path, any broker.

Loop (every `loop_seconds`):
  1. refresh prices, compute equity, update risk state (kill switch / daily limit)
  2. manage open positions (TP / SL / trailing / time exit / agent exit / flatten)
  3. every `policy_every_minutes`: LLM agent sets the trading policy
  4. on every new closed candle: ML model scores all symbols -> candidates
     -> risk pre-check -> LLM review -> sizing -> execution
  5. log everything (decision log + equity curve) and persist state for restarts
"""
from __future__ import annotations

import json
import os
import time
import logging
import traceback

import numpy as np
import pandas as pd

from .agent import TradingAgent
from .brokers import LiveBroker, PaperBroker
from .data import fetch_history, drop_open_bar
from .decision_log import DecisionLog
from .features import build_features, candles_to_df
from .model import SignalModel
from .risk import RiskManager, Position
from .wallex_client import WallexClient, WallexError

log = logging.getLogger("engine")


class Engine:
    def __init__(self, cfg: dict, mode: str, api_key: str | None):
        assert mode in ("live", "shadow")
        self.cfg = cfg
        self.mode = mode
        self.client = WallexClient(api_key)
        ldir = cfg["logging"]["dir"]
        os.makedirs(ldir, exist_ok=True)
        self.dlog = DecisionLog(os.path.join(ldir, f"decisions_{mode}.jsonl"), mode)
        self.equity_path = os.path.join(ldir, f"equity_{mode}.csv")
        self.state_path = os.path.join(ldir, f"state_{mode}.json")
        self.res = cfg["data"]["resolution_min"]
        self.risk = RiskManager(cfg["risk"], cfg["challenge"])
        self.positions: dict[str, Position] = {}
        self.frames: dict[str, pd.DataFrame] = {}
        self.markets = {}
        self.universe: list[str] = []
        self.policy: dict = {}
        self.last_policy_t = 0.0
        self.last_bar_t = 0
        self.last_train_t = 0.0
        self.last_equity_log = 0.0
        self.last_candle_refresh = 0.0
        self.trades_done = 0
        self.errors = 0

    # =============================================================== setup
    def setup(self):
        c = self.cfg
        self.markets = self.client.markets()
        cands = c["markets"]["allowed_override"] or c["markets"]["candidates"]
        uni = []
        for s in cands:
            m = self.markets.get(s)
            if not m or m.quote != c["markets"]["quote"]:
                self.dlog.write("universe_skip", symbol=s, reason="market not found")
                continue
            if m.quote_volume_24h < c["markets"]["min_24h_quote_volume_tmn"]:
                self.dlog.write("universe_skip", symbol=s, reason="illiquid",
                                quote_volume_24h=m.quote_volume_24h)
                continue
            uni.append(s)
        self.universe = uni
        # fees
        self.fee_rate = c["execution"]["fee_rate_fallback"]
        fees = {}
        if self.mode == "live":
            try:
                fees = self.client.fees()
                tk = [fees[s]["taker"] for s in uni if s in fees and fees[s]["taker"] > 0]
                if tk:
                    self.fee_rate = max(tk)
            except WallexError as e:
                log.warning("fee lookup failed, using fallback: %s", e)
        self.round_trip_cost = 2 * self.fee_rate
        self.risk.breakeven_frac = self.round_trip_cost + 0.001
        # broker
        if self.mode == "live":
            self.broker = LiveBroker(self.client, fees, self.fee_rate, c["execution"])
        else:
            self.broker = PaperBroker(self.client, self.fee_rate, c["challenge"]["initial_capital_tmn"])
        # data + model
        need = set(uni) | {"BTCTMN", "USDTTMN"}
        for s in need:
            if s in self.markets:
                self.frames[s] = fetch_history(self.client, s, self.res, c["data"]["history_days"])
        self.model = SignalModel(c["model"], self.round_trip_cost)
        self.train()
        # agent with tools
        self.agent = TradingAgent(c["agent"], {
            "get_orderbook": self.tool_orderbook,
            "get_candles_summary": self.tool_candles_summary,
            "get_account_state": self.tool_account_state,
        }, self.fee_rate, c["model"], self.res)
        self.load_state()
        self.dlog.write("startup", universe=uni, fee_rate=self.fee_rate,
                        round_trip_cost=self.round_trip_cost, agent_enabled=self.agent.enabled,
                        model_report=self.model.report.to_dict(), config=c)
        log.info("universe=%s fee=%.4f agent=%s", uni, self.fee_rate, self.agent.enabled)

    def train(self):
        frames = {s: df for s, df in self.frames.items() if s in self.universe or s in ("BTCTMN", "USDTTMN")}
        data = self.model.dataset({s: df for s, df in frames.items() if s in self.universe} |
                                  {k: frames[k] for k in ("BTCTMN", "USDTTMN") if k in frames})
        try:
            rep = self.model.fit(data)
            self.dlog.write("model_trained", report=rep.to_dict())
        except ValueError as e:
            self.dlog.write("model_train_skipped", reason=str(e))
        self.last_train_t = time.time()

    # ============================================================ persistence
    def save_state(self):
        st = {"positions": {k: v.to_dict() for k, v in self.positions.items()},
              "risk": self.risk.state.__dict__, "trades_done": self.trades_done,
              "paper_balances": getattr(self.broker, "bal", None)}
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(st, f, default=str)
        os.replace(tmp, self.state_path)

    def load_state(self):
        if not os.path.exists(self.state_path):
            return
        with open(self.state_path, encoding="utf-8") as f:
            st = json.load(f)
        self.positions = {k: Position(**v) for k, v in st.get("positions", {}).items()}
        for k, v in st.get("risk", {}).items():
            setattr(self.risk.state, k, v)
        self.trades_done = st.get("trades_done", 0)
        if self.mode == "shadow" and st.get("paper_balances"):
            self.broker.bal = st["paper_balances"]
        self.dlog.write("state_restored", positions=list(self.positions))

    # ================================================================ account
    def equity(self) -> tuple[float, float, float, dict]:
        bal = self.broker.balances()
        tmn = bal.get("TMN", {}).get("total", 0.0)
        free_tmn = bal.get("TMN", {}).get("free", 0.0)
        exposure = 0.0
        for s, m in self.markets.items():
            if m.quote == "TMN" and m.base in bal and bal[m.base]["total"] > 0 and s in self.universe:
                exposure += bal[m.base]["total"] * m.bid
        return tmn + exposure, exposure, free_tmn, bal

    def log_equity(self, eq, exposure, now):
        new = not os.path.exists(self.equity_path)
        with open(self.equity_path, "a", encoding="utf-8") as f:
            if new:
                f.write("ts,time,equity,exposure,drawdown_pct,open_positions\n")
            f.write(f"{now:.0f},{time.strftime('%Y-%m-%d %H:%M:%S')},{eq:.0f},{exposure:.0f},"
                    f"{self.risk.drawdown_pct(eq):.3f},{len(self.positions)}\n")

    # ================================================================== tools
    def tool_orderbook(self, symbol: str) -> dict:
        ob = self.client.depth(symbol)
        if not ob["bids"] or not ob["asks"]:
            return {"symbol": symbol, "error": "empty book"}
        bb, ba = ob["bids"][0][0], ob["asks"][0][0]
        mid = (bb + ba) / 2
        bd = sum(p * q for p, q in ob["bids"] if p >= mid * 0.995)
        ad = sum(p * q for p, q in ob["asks"] if p <= mid * 1.005)
        return {"symbol": symbol, "best_bid": bb, "best_ask": ba,
                "spread_pct": round((ba - bb) / mid * 100, 4),
                "bid_depth_tmn_0.5pct": round(bd), "ask_depth_tmn_0.5pct": round(ad),
                "imbalance": round((bd - ad) / (bd + ad), 3) if bd + ad else 0}

    def tool_candles_summary(self, symbol: str, hours: float = 6) -> dict:
        df = self.frames.get(symbol)
        if df is None or df.empty:
            return {"symbol": symbol, "error": "no data"}
        n = max(2, int(hours * 60 / self.res))
        d = df.iloc[-n:]
        r = np.log(d["c"]).diff().dropna()
        return {"symbol": symbol, "hours": hours, "return_pct": round((d["c"].iloc[-1] / d["c"].iloc[0] - 1) * 100, 3),
                "high": d["h"].max(), "low": d["l"].min(), "last": d["c"].iloc[-1],
                "vol_per_bar_pct": round(float(r.std() * 100), 4) if len(r) > 2 else None,
                "volume_tmn": round(float((d["v"] * d["c"]).sum())),
                "volume_trend_last_hour_vs_avg": round(float((d["v"] * d["c"]).iloc[-12:].mean() /
                                                     max(1e-9, (d["v"] * d["c"]).mean())), 3)}

    def tool_account_state(self) -> dict:
        eq, exp, free, _ = self.equity()
        init = self.cfg["challenge"]["initial_capital_tmn"]
        return {"equity_tmn": round(eq), "return_pct": round((eq / init - 1) * 100, 3),
                "drawdown_from_peak_pct": round(self.risk.drawdown_pct(eq), 3),
                "exposure_pct": round(exp / eq * 100, 2) if eq else 0, "free_tmn": round(free),
                "open_positions": {s: {"entry": p.entry_price, "qty": p.qty,
                                       "held_min": round((time.time() - p.entry_time) / 60)}
                                   for s, p in self.positions.items()},
                "trades_done": self.trades_done,
                "minutes_to_end": round((self.risk.end_ts - time.time()) / 60)}

    # ============================================================== market io
    def refresh_candles(self):
        now = time.time()
        for s in list(self.frames):
            try:
                c = self.client.candles(s, str(self.res), int(now - 6 * 3600), int(now))
                new = candles_to_df(c)
                if new.empty:
                    continue
                df = pd.concat([self.frames[s], new], ignore_index=True)
                df = df.drop_duplicates("t", keep="last").sort_values("t").reset_index(drop=True)
                self.frames[s] = df.iloc[-6000:]
            except WallexError as e:
                log.warning("candle refresh %s: %s", s, e)
        self.last_candle_refresh = now

    def scores(self) -> dict[str, dict]:
        out = {}
        mk, us = self.frames.get("BTCTMN"), self.frames.get("USDTTMN")
        for s in self.universe:
            df = drop_open_bar(self.frames.get(s, pd.DataFrame()), self.res)
            if len(df) < 100:
                continue
            f = build_features(df, None if s == "BTCTMN" else drop_open_bar(mk, self.res) if mk is not None else None,
                               None if s == "USDTTMN" else drop_open_bar(us, self.res) if us is not None else None)
            p = self.model.predict_latest(f)
            last = f.iloc[-1]
            m = self.markets[s]
            out[s] = {"p_tp": None if p is None else round(p, 4),
                      "bar_t": int(last["t"]),
                      "r1h_pct": round(float(last["r12"]) * 100, 3),
                      "r4h_pct": round(float(last["r48"]) * 100, 3),
                      "rsi": round(float(last["rsi14"]) * 100, 1),
                      "vol12": round(float(last["vol12"]) * 100, 4) if pd.notna(last["vol12"]) else None,
                      "bb_z": round(float(last["bb_z20"]), 2) if pd.notna(last["bb_z20"]) else None,
                      "spread_pct": round(m.spread_pct, 4)}
        return out

    # ============================================================= decisions
    def maybe_update_policy(self, now, scores):
        if now - self.last_policy_t < self.cfg["agent"]["policy_every_minutes"] * 60 and self.policy:
            return
        snapshot = {"time": time.strftime("%Y-%m-%d %H:%M"), "base_threshold": self.cfg["model"]["base_prob_threshold"],
                    "model_valid_auc": self.model.report.valid_auc, "symbols": scores,
                    "account": self.tool_account_state()}
        self.policy = self.agent.policy(snapshot, self.universe)
        self.last_policy_t = now
        self.dlog.write("policy", policy=self.policy, snapshot=snapshot)

    def close_position(self, s: str, reason: str, decision: dict | None = None):
        pos = self.positions.get(s)
        m = self.markets[s]
        fill = self.broker.sell(m, pos.qty if pos else 0, self.cfg["execution"]["exit_mode"])
        if fill.ok:
            pnl = fill.notional_tmn - fill.fee_tmn - (pos.cost_tmn if pos else 0)
            pnl_pct = pnl / pos.cost_tmn * 100 if pos and pos.cost_tmn else None
            self.trades_done += 1
            self.dlog.write("exit", symbol=s, reason=reason, qty=fill.qty, avg_price=fill.avg_price,
                            proceeds_tmn=round(fill.notional_tmn), fee_tmn=round(fill.fee_tmn),
                            pnl_tmn=round(pnl), pnl_pct=None if pnl_pct is None else round(pnl_pct, 3),
                            entry_decision_id=pos.decision_id if pos else None, orders=fill.orders,
                            agent=decision)
            if pnl < 0:
                self.risk.on_loss_exit(s, time.time())
            remaining = (pos.qty - fill.qty) if pos else 0
            if pos and remaining * m.bid > m.min_notional:
                pos.qty = remaining  # partial exit: keep the rest, retry next loop
            else:
                self.positions.pop(s, None)
        else:
            self.dlog.write("exit_failed", symbol=s, reason=reason, note=fill.note, orders=fill.orders)
        self.save_state()

    def manage_positions(self, now):
        max_hold = self.cfg["model"]["horizon_bars"] * self.res * 60 * 1.5
        for s, pos in list(self.positions.items()):
            m = self.markets.get(s)
            if not m:
                continue
            reason = None
            if self.risk.must_flatten(now):
                reason = "challenge_end_flatten"
            elif self.risk.state.killed:
                reason = "kill_switch"
            elif s in (self.policy.get("exit_symbols") or []):
                reason = "agent_exit"
            else:
                reason = self.risk.exit_reason(pos, m.bid, now, max_hold)
            if reason:
                self.close_position(s, reason, {"policy_reasoning": self.policy.get("reasoning")}
                                    if reason == "agent_exit" else None)

    def flatten_stray_balances(self):
        """Safety net at the end: sell any coin balance in the universe, even if
        it is not tracked as a position (e.g. after a crash)."""
        _, _, _, bal = self.equity()
        for s in self.universe:
            m = self.markets[s]
            q = bal.get(m.base, {}).get("free", 0.0)
            if q > 0 and q * m.bid > m.min_notional and s not in self.positions:
                fill = self.broker.sell(m, q, "taker")
                self.dlog.write("flatten_stray", symbol=s, qty=fill.qty, avg_price=fill.avg_price,
                                proceeds_tmn=round(fill.notional_tmn), orders=fill.orders)

    def try_entries(self, now, scores, eq, exposure, free_tmn):
        base = self.cfg["model"]["base_prob_threshold"]
        th = base + float(self.policy.get("threshold_adj", 0.03))
        allowed = set(self.policy.get("allowed_symbols") or [])
        mx_spread = self.cfg["markets"]["max_spread_pct"]
        cands = []
        for s, sc in scores.items():
            p = sc["p_tp"]
            if p is None or p < th:
                continue
            if s not in allowed:
                self.dlog.write("candidate_blocked", symbol=s, p_tp=p, threshold=th,
                                reason=f"not allowed by agent policy (regime={self.policy.get('regime')})")
                continue
            if sc["spread_pct"] > mx_spread:
                self.dlog.write("candidate_blocked", symbol=s, p_tp=p, reason=f"spread {sc['spread_pct']}% too wide")
                continue
            cands.append((p, s))
        for p, s in sorted(cands, reverse=True):
            ok, why = self.risk.can_open(s, eq, exposure, len(self.positions), s in self.positions, now)
            if not ok:
                self.dlog.write("candidate_blocked", symbol=s, p_tp=p, threshold=th, reason=why)
                continue
            did = self.dlog.new_id()
            cand = {"symbol": s, "p_tp": p, "threshold": round(th, 4), **scores[s],
                    "take_profit_pct": self.cfg["model"]["take_profit_pct"],
                    "stop_loss_pct": self.cfg["model"]["stop_loss_pct"]}
            rev = self.agent.review(cand, self.policy)
            self.dlog.write("candidate_review", decision_id=did, candidate=cand, review=rev)
            if not rev["approve"]:
                continue
            size = self.risk.size_tmn(eq, exposure, free_tmn, p, th,
                                      float(self.policy.get("size_mult", 0.6)), rev["size_mult"])
            if size < self.cfg["risk"]["min_order_tmn"]:
                self.dlog.write("candidate_blocked", decision_id=did, symbol=s,
                                reason=f"size {size:.0f} TMN below minimum")
                continue
            m = self.markets[s]
            fill = self.broker.buy(m, size, self.cfg["execution"]["entry_mode"])
            if not fill.ok:
                self.dlog.write("entry_unfilled", decision_id=did, symbol=s, size_tmn=round(size),
                                note=fill.note, orders=fill.orders)
                continue
            mc = self.cfg["model"]
            px = fill.avg_price
            self.positions[s] = Position(symbol=s, qty=fill.qty, entry_price=px, entry_time=time.time(),
                                         cost_tmn=fill.notional_tmn, tp_price=px * (1 + mc["take_profit_pct"] / 100),
                                         sl_price=px * (1 - mc["stop_loss_pct"] / 100), peak_price=px,
                                         decision_id=did)
            self.trades_done += 1
            exposure += fill.notional_tmn
            free_tmn -= fill.notional_tmn
            self.dlog.write("entry", decision_id=did, symbol=s, qty=fill.qty, avg_price=px,
                            cost_tmn=round(fill.notional_tmn), fee_tmn=round(fill.fee_tmn),
                            tp_price=self.positions[s].tp_price, sl_price=self.positions[s].sl_price,
                            why={"p_tp": p, "threshold": th, "policy_regime": self.policy.get("regime"),
                                 "policy_reasoning": self.policy.get("reasoning"),
                                 "review_reason": rev.get("reason")}, orders=fill.orders)
            self.save_state()

    # ================================================================== loop
    def step(self):
        now = time.time()
        self.markets = self.client.markets()
        if now - self.last_candle_refresh > 60:
            self.refresh_candles()
        eq, exposure, free_tmn, _ = self.equity()
        for ev in self.risk.on_equity(eq, now):
            self.dlog.write(ev, equity=eq, reason=self.risk.state.kill_reason)
        if now - self.last_equity_log > 60:
            self.log_equity(eq, exposure, now)
            self.last_equity_log = now
        self.manage_positions(now)
        if self.risk.must_flatten(now) or self.risk.state.killed:
            self.flatten_stray_balances()
            return
        if now - self.last_train_t > self.cfg["model"]["retrain_every_minutes"] * 60:
            self.train()
        scores = self.scores()
        if not scores:
            return
        self.maybe_update_policy(now, scores)
        bar_t = max(v["bar_t"] for v in scores.values())
        if bar_t > self.last_bar_t:  # act once per new closed candle
            self.last_bar_t = bar_t
            self.dlog.write("scan", threshold=self.cfg["model"]["base_prob_threshold"] +
                            float(self.policy.get("threshold_adj", 0)), regime=self.policy.get("regime"),
                            scores={s: v["p_tp"] for s, v in scores.items()}, equity=round(eq))
            eq, exposure, free_tmn, _ = self.equity()
            self.try_entries(now, scores, eq, exposure, free_tmn)
        self.save_state()

    def run(self):
        self.setup()
        log.info("engine running in %s mode", self.mode.upper())
        while True:
            t0 = time.time()
            if t0 > self.risk.end_ts + 300:
                self.dlog.write("finished", trades=self.trades_done)
                log.info("challenge over — exiting")
                break
            try:
                self.step()
            except KeyboardInterrupt:
                raise
            except Exception as e:  # never die: log, back off, continue
                self.errors += 1
                self.dlog.write("error", error=str(e)[:500], trace=traceback.format_exc()[-1500:])
                log.error("step error: %s", e)
                time.sleep(10)
            dt = time.time() - t0
            time.sleep(max(1.0, self.cfg["execution"]["loop_seconds"] - dt))
