"""Risk questionnaire -> risk score (0-100) -> allocation over the engine's three strategies.

Two dimensions, 5 questions each, every answer worth 0..4 points:
  capacity    (objective: can you afford losses?)   horizon, share of savings, income, emergency fund, age
  willingness (subjective: do you want risk?)       experience, reaction to a drop, max loss, scenario, goal
score = min(average of the two, the lower one + 10): a high score on one side cannot hide a low one.

Allocation: piecewise-linear between anchor points. The anchor at 70 is the founder's live allocation
(config.yaml: 20% market maker / 35% rial sleeve / 45% beta sleeve). A user may always choose a MORE
conservative mix than the recommendation, never a riskier one.
"""
from __future__ import annotations

from .settings import settings

QUESTIONS = [
    # ---------------- capacity
    {"id": "horizon", "dim": "capacity", "title": "این پول را تا چه مدت لازم ندارید؟",
     "options": ["کمتر از ۱ ماه", "۱ تا ۶ ماه", "۶ ماه تا ۱ سال", "۱ تا ۳ سال", "بیش از ۳ سال"]},
    {"id": "savings_share", "dim": "capacity", "title": "این مبلغ چند درصد از کل پس‌انداز شماست؟",
     "options": ["بیش از ۷۵٪", "۵۰ تا ۷۵٪", "۲۵ تا ۵۰٪", "۱۰ تا ۲۵٪", "کمتر از ۱۰٪"]},
    {"id": "income", "dim": "capacity", "title": "درآمد ماهانه‌ی شما چقدر پایدار است؟",
     "options": ["درآمد ثابتی ندارم", "نامنظم است", "نسبتاً پایدار است", "پایدار است و هر ماه پس‌انداز می‌کنم",
                 "بسیار پایدار است و چند منبع درآمد دارم"]},
    {"id": "emergency", "dim": "capacity", "title": "اگر فردا هزینه‌ای غیرمنتظره پیش بیاید، از کجا تأمین می‌کنید؟",
     "options": ["باید از همین سرمایه برداشت کنم", "احتمالاً باید از همین سرمایه بردارم",
                 "قرض می‌گیرم یا بخشی را از جای دیگر جور می‌کنم", "پس‌انداز اضطراری کمی جدا دارم",
                 "پس‌انداز اضطراری کافی (حداقل ۶ ماه هزینه) جدا دارم"]},
    {"id": "age", "dim": "capacity", "title": "سن شما؟",
     "options": ["بالای ۶۰ سال", "۵۰ تا ۶۰ سال", "۴۰ تا ۵۰ سال", "۳۰ تا ۴۰ سال", "زیر ۳۰ سال"]},
    # ---------------- willingness
    {"id": "experience", "dim": "willingness", "title": "چقدر در بازار رمزارز تجربه دارید؟",
     "options": ["هیچ تجربه‌ای ندارم", "کمتر از ۱ سال", "۱ تا ۳ سال", "بیش از ۳ سال", "معامله‌گر حرفه‌ای هستم"]},
    {"id": "drop_reaction", "dim": "willingness", "title": "ارزش سبد شما در یک هفته ۱۵٪ کم شده است. چه می‌کنید؟",
     "options": ["همه را می‌فروشم تا بیشتر ضرر نکنم", "بخشی را می‌فروشم", "صبر می‌کنم و کاری نمی‌کنم",
                 "کمی بیشتر می‌خرم", "فرصت است؛ با تمام توان بیشتر می‌خرم"]},
    {"id": "max_loss", "dim": "willingness", "title": "حداکثر افت موقت سرمایه که بدون نگرانی تحمل می‌کنید؟",
     "options": ["۲٪", "۵٪", "۱۰٪", "۲۰٪", "بیش از ۳۰٪"]},
    {"id": "scenario", "dim": "willingness", "title": "از بین این سبدها کدام را انتخاب می‌کنید؟ (بازه‌ی بازده ممکن در یک ماه)",
     "options": ["بین ۱+٪ تا ۲+٪", "بین ۲-٪ تا ۵+٪", "بین ۵-٪ تا ۱۰+٪", "بین ۱۰-٪ تا ۲۰+٪", "بین ۲۰-٪ تا ۴۰+٪"]},
    {"id": "goal", "dim": "willingness", "title": "هدف اصلی شما از این سرمایه‌گذاری چیست؟",
     "options": ["فقط حفظ ارزش پول", "حفظ ارزش در برابر تورم و کمی سود", "رشد متعادل", "رشد سریع",
                 "بیشترین سود ممکن، حتی با ریسک بالا"]},
]

PROFILES = [  # (upper bound of the score, key, Persian name, description)
    (20, "conservative", "محافظه‌کار", "اولویت شما حفظ سرمایه است. بیشتر پول در بازارساز کم‌ریسک می‌ماند."),
    (40, "cautious", "محتاط", "کمی ریسک برای سود بیشتر را می‌پذیرید، ولی سهم پرریسک کوچک است."),
    (60, "balanced", "متعادل", "تعادل بین رشد و امنیت؛ سرمایه بین هر سه استراتژی تقسیم می‌شود."),
    (80, "growth", "رشدگرا", "دنبال رشد هستید و افت‌های موقت را تحمل می‌کنید."),
    (101, "aggressive", "جسور", "بیشترین سهم در استراتژی پرریسک؛ نوسان زیاد را می‌پذیرید."),
]

# score -> (low, medium, high) in %; the 70 anchor is the founder's live mix (20/35/45)
ANCHORS = [(0, (85, 15, 0)), (25, (60, 30, 10)), (50, (35, 40, 25)), (70, (20, 35, 45)), (100, (5, 25, 70))]


def strategies() -> list[dict]:
    """The three strategies, described from the engine's config.yaml (single source of truth)."""
    pf = (settings.engine_config.get("portfolio") or {}).get("sleeves") or {}
    rial = pf.get("rial", {})
    beta = pf.get("beta", {})
    mm = settings.engine_config.get("mm", {})
    return [
        {"key": "low", "name": "کم‌ریسک: بازارساز", "assets": f"{mm.get('max_markets', 3)} بازار تومانی پرنوسان",
         "how": "سفارش خرید و فروش دوطرفه (Maker) حول ارزش منصفانه؛ سود از اختلاف قیمت خرید و فروش. "
                "موجودی هر کوین محدود، حد ضرر هر معامله ۱.۲٪ و حد زمانی ۹۰ دقیقه.",
         "backtest": {"mean_pct": 0.0, "p_loss_pct": None, "worst_pct": -1.2},
         "stop_pct": mm.get("stop_pct", 1.2), "color": "low"},
        {"key": "medium", "name": "ریسک متوسط: سبد ریال", "assets": " / ".join(rial.get("assets", {"BTC": 1, "ETH": 1})),
         "how": "نگهداری بیت‌کوین و اتریوم وقتی تتر/تومان در ۴۸ ساعت حداقل ۱٪ رشد کرده باشد (تضعیف ریال). "
                f"حد ضرر فاجعه {rial.get('stop_pct', 5)}٪ کل سبد.",
         "backtest": {"mean_pct": 0.88, "p_loss_pct": 34, "worst_pct": -2.93},
         "stop_pct": rial.get("stop_pct", 5.0), "color": "medium"},
        {"key": "high", "name": "پرریسک: سبد بتا", "assets": " / ".join(beta.get("assets", {"PEPE": 1})),
         "how": "آلت‌کوین‌های پرنوسان با همان شرط رژیم؛ AI می‌تواند هر ۳ ساعت ۲ تا ۴ کوین از "
                + "، ".join(beta.get("universe", [])) + f" انتخاب کند. حد ضرر فاجعه {beta.get('stop_pct', 7)}٪.",
         "backtest": {"mean_pct": 1.28, "p_loss_pct": 30, "worst_pct": -4.28},
         "stop_pct": beta.get("stop_pct", 7.0), "color": "high"},
    ]


def founder_allocation() -> tuple[int, int, int]:
    pf = (settings.engine_config.get("portfolio") or {}).get("sleeves") or {}
    med = int(pf.get("rial", {}).get("capital_pct", 35))
    high = int(pf.get("beta", {}).get("capital_pct", 45))
    return 100 - med - high, med, high


def validate_answers(answers: dict) -> str | None:
    for q in QUESTIONS:
        v = answers.get(q["id"])
        if not isinstance(v, int) or not 0 <= v < len(q["options"]):
            return f"به سؤال «{q['title']}» پاسخ داده نشده است"
    return None


def score(answers: dict) -> dict:
    dims = {"capacity": [], "willingness": []}
    for q in QUESTIONS:
        dims[q["dim"]].append(answers[q["id"]])
    cap = sum(dims["capacity"]) / (4 * len(dims["capacity"])) * 100
    will = sum(dims["willingness"]) / (4 * len(dims["willingness"])) * 100
    final = min((cap + will) / 2, min(cap, will) + 10)
    final = round(max(0.0, min(100.0, final)), 1)
    key, name, desc = profile_for(final)
    return {"capacity": round(cap, 1), "willingness": round(will, 1), "score": final,
            "profile_key": key, "profile_name": name, "profile_desc": desc, "allocation": allocation_for(final)}


def profile_for(s: float) -> tuple[str, str, str]:
    for hi, key, name, desc in PROFILES:
        if s < hi:
            return key, name, desc
    return PROFILES[-1][1:]


def profile_name(key: str) -> str:
    return next((p[2] for p in PROFILES if p[1] == key), key)


def allocation_for(s: float) -> dict:
    s = max(0.0, min(100.0, s))
    for (s0, a0), (s1, a1) in zip(ANCHORS, ANCHORS[1:]):
        if s0 <= s <= s1:
            t = (s - s0) / (s1 - s0)
            raw = [a0[i] + (a1[i] - a0[i]) * t for i in range(3)]
            break
    high, medium = round(raw[2]), round(raw[1])     # the low-risk share takes the rounding remainder
    return {"low": 100 - high - medium, "medium": medium, "high": high}


def check_custom_allocation(rec: dict, alloc: dict) -> str | None:
    """More conservative than the recommendation is always allowed; riskier never."""
    try:
        lo, me, hi = int(alloc["low"]), int(alloc["medium"]), int(alloc["high"])
    except (KeyError, TypeError, ValueError):
        return "تخصیص نامعتبر است"
    if min(lo, me, hi) < 0 or lo + me + hi != 100:
        return "جمع درصدها باید ۱۰۰ باشد"
    if hi > rec["high"]:
        return f"سهم پرریسک نمی‌تواند از پیشنهاد پروفایل شما ({rec['high']}٪) بیشتر باشد"
    if hi + me > rec["high"] + rec["medium"]:
        return "سهم متوسط و پرریسک روی هم نمی‌تواند از پیشنهاد پروفایل شما بیشتر باشد"
    return None


def expected(alloc: dict) -> dict:
    """Backtest figures of the mix (27-hour windows while the entry rule held; see STRATEGY.md)."""
    st = {s["key"]: s["backtest"] for s in strategies()}
    w = {k: alloc[k] / 100 for k in ("low", "medium", "high")}
    return {"mean_pct": round(sum(w[k] * st[k]["mean_pct"] for k in w), 2),
            "worst_pct": round(sum(w[k] * st[k]["worst_pct"] for k in w), 2),
            "note": "میانگین و بدترین نتیجه در پنجره‌های ۲۷ ساعته‌ی بک‌تست روی ۲۹ روز داده‌ی والکس، بعد از کارمزد. "
                    "«بدترین» فرض می‌کند هر سه استراتژی هم‌زمان بدترین نتیجه را بدهند. سود به ادامه‌ی روند "
                    "تضعیف ریال بستگی دارد و بازده گذشته تضمینی برای آینده نیست."}
