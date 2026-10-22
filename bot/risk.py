"""Deterministic risk engine — has the final veto over every AI decision.

* time gates: no new quotes near the end, forced flatten before the official end
* daily loss limit: stop quoting for the rest of the (Tehran) day
* two-stage circuit breaker on drawdown from peak:
    stage 1  -> flatten everything, pause `pause_minutes`, then resume at reduced size
    stage 2  -> a further `second_drawdown_pct` loss from the resume level = permanent stop
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta

TEHRAN = timezone(timedelta(hours=3, minutes=30))


@dataclass
class RiskState:
    equity_peak: float = 0.0
    day_key: str = ""
    day_start_equity: float = 0.0
    killed: bool = False                 # permanent stop (stage 2)
    kill_reason: str = ""
    breaker_count: int = 0               # how many times stage 1 fired
    paused_until: float = 0.0            # stage-1 pause end (epoch seconds)
    resume_equity: float = 0.0           # equity level when trading resumed after a pause
    max_drawdown_seen_pct: float = 0.0
    events: list = field(default_factory=list)


class RiskManager:
    def __init__(self, cfg: dict, challenge: dict):
        self.cfg = cfg
        self.ch = challenge
        self.end_ts = datetime.fromisoformat(challenge["end_time"]).timestamp()
        self.state = RiskState()

    # ----------------------------------------------------------- time gates
    def entries_allowed_by_time(self, now: float) -> bool:
        return now < self.end_ts - self.ch["stop_new_entries_minutes_before_end"] * 60

    def must_flatten(self, now: float) -> bool:
        return now >= self.end_ts - self.ch["force_flatten_minutes_before_end"] * 60

    def wind_down(self, now: float) -> float:
        """Share of the holding sleeves still held. Steps down from 1 to 0 in `wind_down_steps` equal steps
        between `wind_down_start_hours_before_end` and the forced flatten (4 h, 4 steps: 19:50 -> 75%,
        20:40 -> 50%, 21:30 -> 25%, 22:20 -> 0%), so the exit is spread over hours with maker sells instead of
        one taker sale of everything 40 minutes before the end."""
        start = self.end_ts - self.ch.get("wind_down_start_hours_before_end", 0) * 3600
        stop = self.end_ts - self.ch["force_flatten_minutes_before_end"] * 60
        n = self.ch.get("wind_down_steps", 4)
        if now < start or stop <= start:
            return 1.0
        k = min(n, int((now - start) // ((stop - start) / n)) + 1)
        return round(1 - k / n, 4)

    # ------------------------------------------------------ circuit breaker
    def halted(self, now: float) -> bool:
        return self.state.killed or now < self.state.paused_until

    def size_factor(self) -> float:
        """Quotes are smaller after the breaker has fired once."""
        return self.cfg.get("size_after_pause", 0.5) if self.state.breaker_count else 1.0

    def drawdown_pct(self, equity: float) -> float:
        return (1 - equity / self.state.equity_peak) * 100 if self.state.equity_peak else 0.0

    def on_equity(self, equity: float, now: float) -> list[str]:
        """Update peak / daily stats and fire the breaker. Returns triggered events."""
        events, s, c = [], self.state, self.cfg
        day = datetime.fromtimestamp(now, TEHRAN).strftime("%Y-%m-%d")
        if s.day_key != day:
            s.day_key, s.day_start_equity = day, equity
        s.equity_peak = max(s.equity_peak, equity)
        dd = self.drawdown_pct(equity)
        s.max_drawdown_seen_pct = max(s.max_drawdown_seen_pct, dd)
        if s.killed or now < s.paused_until:
            return events
        if s.breaker_count == 0 and dd >= c["max_drawdown_pct"]:
            s.breaker_count = 1
            s.paused_until = now + c.get("pause_minutes", 60) * 60
            s.resume_equity = equity
            s.kill_reason = f"drawdown {dd:.2f}% >= {c['max_drawdown_pct']}% -> flatten, pause {c.get('pause_minutes', 60)} min, resume at reduced size"
            events.append("circuit_breaker_pause")
        elif s.breaker_count >= 1 and s.resume_equity and \
                (1 - equity / s.resume_equity) * 100 >= c.get("second_drawdown_pct", 2.0):
            s.killed = True
            s.kill_reason = f"second breach: -{c.get('second_drawdown_pct', 2.0)}% after resume -> permanent stop"
            events.append("kill_switch")
        return events

    def daily_loss_hit(self, equity: float) -> bool:
        s = self.state
        if not s.day_start_equity:
            return False
        return (1 - equity / s.day_start_equity) * 100 >= self.cfg["daily_loss_limit_pct"]
