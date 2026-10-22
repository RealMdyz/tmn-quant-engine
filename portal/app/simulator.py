"""Per-user paper bot: the engine's three strategies, scaled to the user's capital and allocation, run on
live market prices with the engine's rules (config.yaml):

  low    (market maker)  kept in Toman in paper mode: per-user market making cannot be simulated honestly
                         from top-of-book prices, and its backtest is ~0%. Shown as such in the UI.
  medium (rial sleeve)   enter when USDT/TMN rose >= regime_full_pct in 48 h; hold; disaster stop.
  high   (beta sleeve)   same rule, its own basket and disaster stop.

Fills are conservative: buys at the best ask and sells at the best bid, both with the taker fee.
"""
from __future__ import annotations

import copy

from sqlalchemy.orm.attributes import flag_modified

from .db import BotAccount, BotEvent, BotTrade, EquitySnapshot, now
from .settings import settings

MIN_ORDER_TMN = 60_000          # Wallex rejects smaller Toman orders
SLEEVES = (("medium", "rial", "سبد ریال"), ("high", "beta", "سبد بتا"))


def sleeve_cfg(cfg_name: str) -> dict:
    return ((settings.engine_config.get("portfolio") or {}).get("sleeves") or {}).get(cfg_name, {})


def taker_fee() -> float:
    return float((settings.engine_config.get("fees") or {}).get("tmn_taker", 0.003))


def fmt_tmn(x: float) -> str:
    return f"{x:,.0f}".replace(",", "٬")


def new_state(capital: float, alloc: dict) -> dict:
    st = {"sleeves": {"low": {"cash": capital * alloc["low"] / 100}}, "fees_tmn": 0.0, "waiting_logged": False}
    for key, _, _ in SLEEVES:
        st["sleeves"][key] = {"cash": capital * alloc[key] / 100, "pos": {}, "built": False, "stopped": None,
                              "realised": 0.0}
    return st


def valuation(state: dict, prices: dict) -> dict:
    out = {"low": state["sleeves"]["low"]["cash"]}
    for key, _, _ in SLEEVES:
        sl = state["sleeves"][key]
        v = sl["cash"]
        for a, p in sl["pos"].items():
            bid = (prices.get(a) or {}).get("bid") or p.get("last_bid") or 0.0
            v += p["qty"] * bid
        out[key] = v
    out["equity"] = out["low"] + out["medium"] + out["high"]
    return out


class Ctx:
    """Collects the trades and events of one step so the caller writes them in one transaction."""

    def __init__(self, bot: BotAccount):
        self.bot, self.trades, self.events = bot, [], []

    def trade(self, sleeve, asset, side, qty, price, fee, reason):
        self.trades.append(BotTrade(bot_id=self.bot.id, ts=now(), sleeve=sleeve, asset=asset, side=side, qty=qty,
                                    price=price, notional_tmn=qty * price, fee_tmn=fee, reason=reason))

    def event(self, kind, text):
        self.events.append(BotEvent(bot_id=self.bot.id, ts=now(), kind=kind, text=text))


def _buy_sleeve(ctx: Ctx, st: dict, key: str, name: str, weights: dict, prices: dict, why: str):
    sl = st["sleeves"][key]
    budget, fee = sl["cash"], taker_fee()
    total_w = sum(weights.values()) or 1.0
    bought = []
    for a, w in weights.items():
        amount = budget * w / total_w
        ask = (prices.get(a) or {}).get("ask")
        if not ask or amount < MIN_ORDER_TMN:
            continue
        qty = amount * (1 - fee) / ask
        p = sl["pos"].setdefault(a, {"qty": 0.0, "cost": 0.0})
        p["qty"] += qty
        p["cost"] += amount
        sl["cash"] -= amount
        st["fees_tmn"] += amount * fee
        ctx.trade(key, a, "BUY", qty, ask, amount * fee, why)
        bought.append(a)
    if bought:
        sl["built"] = True
        ctx.event("enter", f"ورود به {name}: خرید {'، '.join(bought)} به ارزش {fmt_tmn(budget - sl['cash'])} تومان. {why}")


def _sell_sleeve(ctx: Ctx, st: dict, key: str, prices: dict, why: str):
    sl = st["sleeves"][key]
    fee = taker_fee()
    for a, p in list(sl["pos"].items()):
        bid = (prices.get(a) or {}).get("bid") or p.get("last_bid")
        if not bid or p["qty"] <= 0:
            continue
        gross = p["qty"] * bid
        sl["cash"] += gross * (1 - fee)
        sl["realised"] += gross * (1 - fee) - p["cost"]
        st["fees_tmn"] += gross * fee
        ctx.trade(key, a, "SELL", p["qty"], bid, gross * fee, why)
        del sl["pos"][a]


def step(bot: BotAccount, snap: dict) -> Ctx:
    """One tick of one paper bot. Mutates bot.state; returns the trades/events to persist."""
    ctx = Ctx(bot)
    if bot.status != "running" or bot.mode != "paper" or not snap.get("fresh"):
        return ctx
    st = copy.deepcopy(bot.state)
    prices, reg = snap["prices"], snap.get("regime") or {}
    for key, cfg_name, name in SLEEVES:
        sl, cfg = st["sleeves"][key], sleeve_cfg(cfg_name)
        if sl["stopped"]:
            continue
        if not sl["built"]:
            if sl["cash"] < MIN_ORDER_TMN:
                continue
            if reg.get("on"):
                _buy_sleeve(ctx, st, key, name, cfg.get("assets", {}), prices,
                            f"شرط ورود برقرار است: تتر/تومان در ۴۸ ساعت {reg.get('ch48_pct')}٪ رشد کرده "
                            f"(حداقل {reg.get('threshold_pct')}٪).")
            elif not st.get("waiting_logged"):
                st["waiting_logged"] = True
                ctx.event("wait", f"منتظر شرط ورود: رشد ۴۸ ساعته‌ی تتر/تومان {reg.get('ch48_pct')}٪ است و باید "
                                  f"حداقل {reg.get('threshold_pct')}٪ باشد. تا آن موقع پول به تومان می‌ماند.")
            continue
        value = sum(p["qty"] * ((prices.get(a) or {}).get("bid") or 0.0) for a, p in sl["pos"].items())
        cost = sum(p["cost"] for p in sl["pos"].values())
        for a, p in sl["pos"].items():
            if (prices.get(a) or {}).get("bid"):
                p["last_bid"] = prices[a]["bid"]
        stop = float(cfg.get("stop_pct", 99))
        if cost > 0 and value > 0 and (value / cost - 1) * 100 <= -stop:
            why = f"حد ضرر فاجعه‌ی {name} ({stop}٪) فعال شد: ارزش سبد {(value / cost - 1) * 100:.2f}٪ زیر بهای خرید"
            _sell_sleeve(ctx, st, key, prices, why)
            sl["stopped"] = why
            ctx.event("stop", why + ". این سبد تا شروع دوباره‌ی ربات به تومان می‌ماند.")
    bot.state = st
    flag_modified(bot, "state")
    bot.last_tick_at = now()
    return ctx


def start(bot: BotAccount, capital: float, alloc: dict) -> Ctx:
    bot.capital_tmn = capital
    bot.alloc_low, bot.alloc_medium, bot.alloc_high = alloc["low"], alloc["medium"], alloc["high"]
    bot.state = new_state(capital, alloc)
    flag_modified(bot, "state")
    bot.status, bot.started_at, bot.last_snapshot_at = "running", now(), 0.0
    ctx = Ctx(bot)
    ctx.event("start", f"ربات با سرمایه‌ی {fmt_tmn(capital)} تومان شروع شد: کم‌ریسک {alloc['low']}٪، "
                       f"متوسط {alloc['medium']}٪، پرریسک {alloc['high']}٪.")
    return ctx


def stop(bot: BotAccount, prices: dict) -> Ctx:
    ctx = Ctx(bot)
    st = copy.deepcopy(bot.state or {})
    if st.get("sleeves"):
        for key, _, _ in SLEEVES:
            _sell_sleeve(ctx, st, key, prices, "توقف ربات توسط کاربر: همه‌چیز به تومان برگشت")
        bot.state = st
        flag_modified(bot, "state")
    bot.status = "stopped"
    v = valuation(st, prices)["equity"] if st.get("sleeves") else bot.capital_tmn
    ctx.event("stop_user", f"ربات متوقف شد. ارزش نهایی {fmt_tmn(v)} تومان.")
    return ctx


def maybe_snapshot(bot: BotAccount, prices: dict, every_s: float) -> EquitySnapshot | None:
    if not bot.state or not bot.state.get("sleeves") or now() - (bot.last_snapshot_at or 0) < every_s:
        return None
    v = valuation(bot.state, prices)
    bot.last_snapshot_at = now()
    return EquitySnapshot(bot_id=bot.id, ts=now(), equity_tmn=v["equity"], low_tmn=v["low"], medium_tmn=v["medium"],
                          high_tmn=v["high"])
