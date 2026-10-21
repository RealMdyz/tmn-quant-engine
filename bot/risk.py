"""Deterministic risk engine — has the final veto over every AI decision."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

TEHRAN = timezone(timedelta(hours=3, minutes=30))


@dataclass
class Position:
    symbol: str
    qty: float
    entry_price: float
    entry_time: float
    cost_tmn: float
    tp_price: float
    sl_price: float
    peak_price: float
    decision_id: str = ""

    def to_dict(self):
        return self.__dict__.copy()


@dataclass
class RiskState:
    equity_peak: float = 0.0
    day_key: str = ""
    day_start_equity: float = 0.0
    killed: bool = False
    kill_reason: str = ""
    cooldown_until: dict = field(default_factory=dict)
    max_drawdown_seen_pct: float = 0.0


class RiskManager:
    def __init__(self, cfg: dict, challenge: dict):
        self.cfg = cfg
        self.ch = challenge
        self.end_ts = datetime.fromisoformat(challenge["end_time"]).timestamp()
        self.state = RiskState()
        self.breakeven_frac = 0.005  # set by engine to round-trip fee cost

    # ----------------------------------------------------------- time gates
    def entries_allowed_by_time(self, now: float) -> bool:
        return now < self.end_ts - self.ch["stop_new_entries_minutes_before_end"] * 60

    def must_flatten(self, now: float) -> bool:
        return now >= self.end_ts - self.ch["force_flatten_minutes_before_end"] * 60

    # ------------------------------------------------------- equity tracking
    def on_equity(self, equity: float, now: float) -> list[str]:
        """Update peak/daily stats. Returns list of triggered events."""
        events = []
        s = self.state
        day = datetime.fromtimestamp(now, TEHRAN).strftime("%Y-%m-%d")
        if s.day_key != day:
            s.day_key, s.day_start_equity = day, equity
        s.equity_peak = max(s.equity_peak, equity)
        dd = (1 - equity / s.equity_peak) * 100 if s.equity_peak else 0.0
        s.max_drawdown_seen_pct = max(s.max_drawdown_seen_pct, dd)
        if not s.killed and dd >= self.cfg["max_drawdown_pct"]:
            s.killed, s.kill_reason = True, f"drawdown {dd:.2f}% >= {self.cfg['max_drawdown_pct']}%"
            events.append("kill_switch")
        return events

    def daily_loss_hit(self, equity: float) -> bool:
        s = self.state
        if not s.day_start_equity:
            return False
        return (1 - equity / s.day_start_equity) * 100 >= self.cfg["daily_loss_limit_pct"]

    def drawdown_pct(self, equity: float) -> float:
        return (1 - equity / self.state.equity_peak) * 100 if self.state.equity_peak else 0.0

    # ---------------------------------------------------------- entry checks
    def can_open(self, symbol: str, equity: float, exposure: float, n_open: int,
                 has_position: bool, now: float) -> tuple[bool, str]:
        c = self.cfg
        if self.state.killed:
            return False, f"kill switch active ({self.state.kill_reason})"
        if not self.entries_allowed_by_time(now):
            return False, "too close to challenge end"
        if self.daily_loss_hit(equity):
            return False, f"daily loss limit {c['daily_loss_limit_pct']}% reached"
        if has_position:
            return False, "already holding this symbol"
        if n_open >= c["max_open_positions"]:
            return False, f"max open positions ({c['max_open_positions']})"
        if exposure / equity >= c["max_total_exposure_pct"]:
            return False, "max total exposure reached"
        if self.state.cooldown_until.get(symbol, 0) > now:
            return False, "symbol in cooldown after a loss"
        return True, "ok"

    def size_tmn(self, equity: float, exposure: float, free_tmn: float, p: float,
                 threshold: float, policy_mult: float, review_mult: float) -> float:
        c = self.cfg
        conf = min(1.0, max(0.5, 0.5 + (p - threshold) / 0.15))  # 0.5..1 by edge strength
        size = equity * c["max_position_pct"] * policy_mult * review_mult * conf
        size = min(size, equity * c["max_total_exposure_pct"] - exposure, free_tmn * 0.98)
        return max(0.0, size)

    def on_loss_exit(self, symbol: str, now: float):
        self.state.cooldown_until[symbol] = now + self.cfg["cooldown_after_loss_min"] * 60

    # ----------------------------------------------------------- exit logic
    def exit_reason(self, pos: Position, bid: float, now: float, max_hold_s: float) -> str | None:
        """Pure function of position + current bid -> reason to exit or None."""
        pos.peak_price = max(pos.peak_price, bid)
        if bid <= pos.sl_price:
            return "stop_loss"
        if bid >= pos.tp_price:
            return "take_profit"
        gain_peak = pos.peak_price / pos.entry_price - 1
        half_tp = (pos.tp_price / pos.entry_price - 1) / 2
        if gain_peak >= half_tp:
            # profit protection: never let a trade that reached +TP/2 close below break-even
            protect = max(pos.entry_price * (1 + self.breakeven_frac),
                          pos.peak_price * (1 - self.cfg["trailing_stop_pct"] / 100))
            if bid <= protect:
                return "trailing_stop"
        if now - pos.entry_time >= max_hold_s:
            return "time_exit"
        return None
