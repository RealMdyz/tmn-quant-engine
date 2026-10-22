"""Cross-market fair-value arbitrage on Wallex.

Every coin trades twice on Wallex: against Toman (XTMN) and against Tether (XUSDT).
The Tether book follows the global price; Toman books are thinner and get
"dumped" by impatient sellers. The executable value of one coin in Toman is

    liquidation_value = best_bid(XUSDT) * best_bid(USDTTMN)

i.e. what we really get if we sell the coin on the Tether book and sell the
Tether for Toman. We rest a BUY order on the Toman book *below* that value by
(all fees + a safety margin). When an impatient seller hits it, we immediately
sell the coin on the Tether book -> the spread is locked in, no market risk.

    entry  : maker BUY  XTMN     (maker fee, e.g. 0.25%)
    hedge  : taker SELL XUSDT    (taker fee, e.g. 0.13%)
    convert: SELL USDT  USDTTMN  (maker/taker 0.25-0.30%, batched, policy-driven)

The margin per market is chosen by a Thompson-sampling bandit (online learning
of adverse selection), seeded with priors from the walk-forward backtest.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field


@dataclass
class Fees:
    tmn_maker: float = 0.0025
    tmn_taker: float = 0.0030
    usdt_maker: float = 0.0010
    usdt_taker: float = 0.0013

    @property
    def round_trip(self) -> float:
        """Cost of maker-buy XTMN + taker-sell XUSDT + taker-sell USDTTMN."""
        return self.tmn_maker + self.usdt_taker + self.tmn_taker


def liquidation_value(books: dict, coin: str, base_qty: float | None = None) -> float | None:
    """TMN we would receive per 1 coin by selling on XUSDT then USDTTMN (best bids)."""
    cu = books.get(f"{coin}USDT")
    ut = books.get("USDTTMN")
    if not cu or not ut or not cu["bids"] or not ut["bids"]:
        return None
    return cu["bids"][0][0] * ut["bids"][0][0]


def deviation(books: dict, coin: str) -> float | None:
    """Toman best bid vs liquidation value (negative = Toman market is cheap)."""
    lv = liquidation_value(books, coin)
    t = books.get(f"{coin}TMN")
    if not lv or not t or not t["bids"]:
        return None
    return t["bids"][0][0] / lv - 1


# --------------------------------------------------------------------- bandit
HALF_LIFE_S = 2 * 3600      # live evidence older than ~2h counts half as much (lets coins recover)


@dataclass
class Arm:
    margin: float          # extra edge required on top of fees (fraction)
    prior_mean: float      # expected net return per fill (fraction), from backtest
    prior_n: float         # strength of the prior (pseudo-observations)
    fill_rate: float       # expected fills per hour, from backtest
    obs: list = field(default_factory=list)   # [(timestamp, net_return)] of live fills

    def _weighted(self, now: float | None = None):
        now = now or time.time()
        w = [0.5 ** ((now - t) / HALF_LIFE_S) for t, _ in self.obs]
        return sum(w), sum(wi * r for wi, (_, r) in zip(w, self.obs))

    @property
    def n(self) -> int:
        return len(self.obs)

    def posterior(self) -> tuple[float, float]:
        n_eff, sum_r = self._weighted()
        n0 = self.prior_n
        mean = (self.prior_mean * n0 + sum_r) / (n0 + n_eff)
        sd = 0.006 / math.sqrt(n0 + n_eff)          # ~60 bps per-fill noise
        return mean, sd

    def update(self, r: float, t: float | None = None):
        self.obs.append((t or time.time(), r))
        self.obs = self.obs[-200:]


@dataclass
class MarketBandit:
    coin: str
    arms: list[Arm] = field(default_factory=list)
    last_choice: float | None = None

    def choose(self, rng: random.Random, margin_mult: float = 1.0) -> tuple[float, dict]:
        """Thompson sampling on expected profit per hour = fill_rate * sampled E[r]."""
        scores = {}
        for a in self.arms:
            mu, sd = a.posterior()
            draw = rng.gauss(mu, sd)
            scores[a.margin] = a.fill_rate * draw
        best = max(scores, key=scores.get)
        shown = {f"{k*100:.1f}%": round(v * 1e4, 2) for k, v in scores.items()}
        if scores[best] <= 0:          # no arm with positive expected profit -> do not quote
            self.last_choice = None
            return None, shown
        self.last_choice = best
        return best * margin_mult, shown

    def update(self, margin: float, r: float):
        a = min(self.arms, key=lambda x: abs(x.margin - margin))
        a.update(r)

    def expected_per_hour(self) -> float:
        return max(a.posterior()[0] * a.fill_rate for a in self.arms)

    def safest_margin(self) -> float:
        """Probe margin for a sidelined market: the widest arm (most protection)."""
        return max(a.margin for a in self.arms)

    def summary(self) -> dict:
        out = {}
        for a in self.arms:
            mu, sd = a.posterior()
            out[f"{a.margin*100:.1f}%"] = {"live_fills": a.n, "post_mean_bps": round(mu * 1e4, 1),
                                           "live_mean_bps": round(sum(r for _, r in a.obs) / a.n * 1e4, 1) if a.n else None}
        return out


def build_bandits(priors: dict, default: list | None = None, coins: list[str] | None = None) -> dict[str, MarketBandit]:
    """priors: {coin: [[margin %, mean_bps, fills_per_10d], ...]} per-coin overrides; `default` is the
    same shape and is used for every coin in `coins` without an override (pooled realistic backtest)."""
    out = {}
    rows_by_coin = dict(priors or {})
    for coin in coins or []:
        if coin not in rows_by_coin and default:
            rows_by_coin[coin] = default
    for coin, rows in rows_by_coin.items():
        arms = [Arm(margin=m / 100, prior_mean=mb / 1e4, prior_n=max(3.0, min(20.0, f / 4)),
                    fill_rate=max(0.01, f / 240.0)) for m, mb, f in rows]
        out[coin] = MarketBandit(coin, arms)
    return out
