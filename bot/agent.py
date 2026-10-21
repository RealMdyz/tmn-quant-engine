"""LLM supervisory agent (the "Agentic AI" layer).

Research (e.g. "The Alpha Illusion", 2026) shows end-to-end LLM trading alpha does
not survive leakage/cost controls; LLMs add value UPSTREAM — reading context and
news — while sizing, risk and execution stay in audited deterministic modules.
That is exactly how this agent is used:

  * POLICY (every N minutes, and immediately on anomalies): with tool calls it
    inspects market dislocations, the bandit's live learning, the account and
    news (Iran/rial + crypto headlines), then decides
      - which markets the arbitrage may quote (e.g. disable a coin whose Toman
        price is persistently dislocated -> likely deposit/withdrawal halt, not
        a mean-reverting opportunity),
      - a margin multiplier (wider = safer in turbulent conditions),
      - how much of the Tether earned from hedges to HOLD instead of converting
        to Toman (a bounded bet on rial weakness),
      - whether to pause quoting entirely (news shock).
  * Every output is clamped to bounds and logged with its reasoning + tool trace.
  * If the LLM is unavailable the documented fallback policy is used.
"""
from __future__ import annotations

import json
import os
import re
import time
import logging
from collections import deque
from typing import Callable

import requests

log = logging.getLogger("agent")

SYSTEM = """You supervise an automated, market-neutral arbitrage bot on the Wallex exchange (Iran).
How it earns: it rests BUY orders on coin/Toman books below the coin's liquidation value
(coin/USDT best bid x USDT/Toman best bid) minus fees and a margin; when filled it instantly
sells the coin on the coin/USDT book. Risk comes from (a) adverse selection: a fill caused by a
real crash that the USDT book has not shown yet, and (b) structural dislocations: when a coin's
deposits/withdrawals are suspended its Toman price can stay far from fair value and NOT revert.
It also accumulates USDT from hedges; holding some USDT is a bet that the rial weakens (USDT/TMN
rose ~17% in the last month but can fall 2-3% in a day on political news).
Competition context: 3 days, ranked by net % return in Toman, drawdown is penalised,
everything must be back in Toman at the end.

Use the tools to check what you need, then answer ONLY with JSON:
{"enabled_coins": [coins allowed to quote],
 "margin_mult": number in [MM_LO, MM_HI] (1 = learned margins; >1 = demand more edge),
 "usdt_hold_frac": number in [0, UH_HI] (fraction of equity that may stay in USDT),
 "pause": true|false (stop quoting everything, e.g. major breaking news),
 "reasoning": "3-5 sentences citing concrete numbers you saw"}"""

TOOLS = [
    {"type": "function", "function": {
        "name": "get_market_stats",
        "description": "For one coin: current deviation of the Toman bid from liquidation value, its mean/std/min over the last hours, minutes spent below -2%, live fills and realised PnL, bandit margins.",
        "parameters": {"type": "object", "properties": {"coin": {"type": "string"}}, "required": ["coin"]}}},
    {"type": "function", "function": {
        "name": "get_account_state",
        "description": "Equity in Toman, return %, drawdown, USDT inventory, open quotes, fills today, minutes to the end.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_news",
        "description": "Latest headlines (Persian + English) about Iran's economy / rial / sanctions and crypto markets.",
        "parameters": {"type": "object", "properties": {"topic": {"type": "string", "enum": ["iran", "crypto", "all"]}}}}},
    {"type": "function", "function": {
        "name": "get_usdt_tmn_trend",
        "description": "USDT/TMN price now and its change over the last 1h, 6h and 24h from our own recorded prices.",
        "parameters": {"type": "object", "properties": {}}}},
]


def _extract_json(text: str):
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _clamp(x, lo, hi, default):
    try:
        return max(lo, min(hi, float(x)))
    except (TypeError, ValueError):
        return default


class SupervisorAgent:
    def __init__(self, cfg: dict, tools: dict[str, Callable[..., dict]]):
        self.cfg = cfg
        self.tools = tools
        self.providers = []
        for p in cfg.get("providers", []):
            base, key = os.getenv(p["base_url_env"], "").rstrip("/"), os.getenv(p["api_key_env"], "")
            if base and key:
                self.providers.append({"base": base, "key": key, "model": p["model"], "name": p["name"]})
        self.enabled = bool(cfg.get("enabled", True) and self.providers)
        self.calls = deque()
        self.usage = {"calls": 0, "failures": 0, "prompt_tokens": 0, "completion_tokens": 0, "by_provider": {}}

    def spent_usd(self) -> float:
        p = self.cfg.get("price_per_million_usd", {"input": 0.30, "output": 2.50})
        return (self.usage["prompt_tokens"] * p["input"] + self.usage["completion_tokens"] * p["output"]) / 1e6

    def _budget_ok(self):
        """Hard guards for the LLM budget: calls per hour AND total estimated dollars."""
        now = time.time()
        while self.calls and now - self.calls[0] > 3600:
            self.calls.popleft()
        if self.spent_usd() >= self.cfg.get("budget_usd", 2.0):
            return False
        return len(self.calls) < self.cfg.get("max_calls_per_hour", 6)

    def _chat(self, prov, messages, use_tools):
        body = {"model": prov["model"], "messages": messages,
                "max_completion_tokens": self.cfg.get("max_output_tokens", 2500),
                "reasoning_effort": self.cfg.get("reasoning_effort", "low")}   # cheap: little hidden reasoning
        if use_tools:
            body["tools"] = TOOLS
            body["tool_choice"] = "auto"
        hdr = {"Authorization": f"Bearer {prov['key']}"}
        url = f"{prov['base']}/chat/completions"
        r = requests.post(url, json=body, timeout=self.cfg.get("timeout_s", 60), headers=hdr)
        if r.status_code == 400:            # provider does not accept the optional params -> plain request
            body.pop("reasoning_effort", None)
            body.pop("max_completion_tokens", None)
            r = requests.post(url, json=body, timeout=self.cfg.get("timeout_s", 60), headers=hdr)
        r.raise_for_status()
        data = r.json()
        u = data.get("usage") or {}
        self.usage["prompt_tokens"] += u.get("prompt_tokens", 0)
        self.usage["completion_tokens"] += u.get("completion_tokens", 0)
        self.usage["by_provider"][prov["name"]] = self.usage["by_provider"].get(prov["name"], 0) + 1
        return data["choices"][0]["message"]

    def _run(self, system, user, max_steps=4):
        if not self.enabled or not self._budget_ok():
            return None, [], None
        self.calls.append(time.time())
        self.usage["calls"] += 1
        for prov in self.providers:              # provider failover (BoxAPI -> AvalAI ...)
            messages = [{"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(user, ensure_ascii=False, default=str)}]
            trace = []
            try:
                for step in range(max_steps):
                    msg = self._chat(prov, messages, use_tools=step < max_steps - 1)
                    tcs = msg.get("tool_calls") or []
                    if not tcs:
                        return _extract_json(msg.get("content")), trace, prov["name"]
                    messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tcs})
                    for tc in tcs:
                        name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"].get("arguments") or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        try:
                            res = self.tools[name](**args) if name in self.tools else {"error": "unknown tool"}
                        except Exception as e:
                            res = {"error": str(e)[:200]}
                        trace.append({"tool": name, "args": args})
                        messages.append({"role": "tool", "tool_call_id": tc["id"],
                                         "content": json.dumps(res, ensure_ascii=False, default=str)[:self.cfg.get("tool_output_chars", 2500)]})
            except Exception as e:
                self.usage["failures"] += 1
                log.warning("LLM provider %s failed: %s", prov["name"], e)
                continue
        return None, [], None

    def fallback(self, coins: list[str], why: str) -> dict:
        return {"enabled_coins": coins, "margin_mult": 1.15, "usdt_hold_frac": 0.0, "pause": False,
                "reasoning": f"Fallback policy ({why}): all whitelisted coins, margins +15%, convert all USDT.",
                "source": "fallback"}

    def decide(self, context: dict, coins: list[str]) -> dict:
        lo, hi = self.cfg["margin_mult_bounds"]
        uh = self.cfg["usdt_hold_max"]
        system = SYSTEM.replace("MM_LO", str(lo)).replace("MM_HI", str(hi)).replace("UH_HI", str(uh))
        out, trace, prov = self._run(system, context)
        if not out:
            return self.fallback(coins, "LLM unavailable" if not self.enabled else "LLM call failed")
        return {
            "enabled_coins": [c for c in (out.get("enabled_coins") or []) if c in coins],
            "margin_mult": _clamp(out.get("margin_mult"), lo, hi, 1.15),
            "usdt_hold_frac": _clamp(out.get("usdt_hold_frac"), 0.0, uh, 0.0),
            "pause": bool(out.get("pause", False)),
            "reasoning": str(out.get("reasoning", ""))[:1200],
            "tool_trace": trace, "source": f"llm:{prov}",
        }


# ------------------------------------------------------------------ news tool
def fetch_headlines(feeds: list[dict], topic: str = "all", limit: int = 8) -> list[dict]:
    out = []
    for f in feeds:
        if topic != "all" and f.get("topic") != topic:
            continue
        try:
            r = requests.get(f["url"], timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            items = re.findall(r"<item>(.*?)</item>", r.text, re.S)[:limit]
            for it in items:
                t = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", it, re.S)
                d = re.search(r"<pubDate>(.*?)</pubDate>", it, re.S)
                if t:
                    out.append({"source": f["name"], "title": re.sub(r"\s+", " ", t.group(1)).strip()[:200],
                                "date": d.group(1).strip() if d else ""})
        except Exception as e:
            out.append({"source": f["name"], "error": str(e)[:100]})
    return out[:limit]
