"""TMN Portal web app: JSON API under /api, the Persian single-page UI at /.

Run locally from the repo root:  uvicorn portal.app.main:app --port 8000
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select

from . import billing, risk, simulator
from .db import (BotAccount, BotEvent, BotTrade, EquitySnapshot, Payment, RiskProfile, SessionLocal, Subscription,
                 User, active_subscription, count, init_db, kv_get, latest_profile, now)
from .market import with_freshness
from .security import (COOKIE, EMAIL_RE, create_session, drop_session, hash_password, login_limit, password_problem,
                       user_from_token, verify_password)
from .settings import PORTAL_DIR, settings
from .telemetry import downsample

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("portal")
WEB = os.path.join(PORTAL_DIR, "web")
MIN_CAPITAL, MAX_CAPITAL = 1_000_000, 100_000_000_000
FOUNDER_UNTIL = 4102444800.0          # 2100-01-01: the founder's subscription never expires


class ApiError(Exception):
    def __init__(self, msg: str, status: int = 400):
        self.msg, self.status = msg, status


def ensure_founder():
    if not settings.founder_email:
        log.warning("FOUNDER_EMAIL is not set: no founder account")
        return
    with SessionLocal() as db:
        u = db.scalars(select(User).where(User.email == settings.founder_email)).first()
        if not u:
            if not settings.founder_password:
                log.warning("FOUNDER_PASSWORD is not set: founder account not created")
                return
            u = User(email=settings.founder_email, name=settings.founder_name, role="founder",
                     password_hash=hash_password(settings.founder_password))
            db.add(u)
            db.flush()
            log.info("founder account created: %s", u.email)
        else:
            u.role = "founder"
            if settings.founder_password and not verify_password(settings.founder_password, u.password_hash):
                u.password_hash = hash_password(settings.founder_password)
        if not active_subscription(db, u.id):
            db.add(Subscription(user_id=u.id, plan_key="founder", expires_at=FOUNDER_UNTIL))
        bot = db.scalars(select(BotAccount).where(BotAccount.user_id == u.id)).first()
        lo, me, hi = risk.founder_allocation()
        if not bot:
            bot = BotAccount(user_id=u.id)
            db.add(bot)
        bot.mode, bot.status = "master", "running"
        bot.capital_tmn = float(settings.engine_config["challenge"]["initial_capital_tmn"])
        bot.alloc_low, bot.alloc_medium, bot.alloc_high = lo, me, hi
        bot.started_at = bot.started_at or now()
        db.commit()


@asynccontextmanager
async def lifespan(_app):
    init_db()
    ensure_founder()
    if settings.seed_demo:
        from .seed import seed_demo
        seed_demo()
    loops = []
    if settings.run_worker:
        from .worker import start_loops
        loops = start_loops()
    yield
    for x in loops:
        x.stop.set()


app = FastAPI(title="TMN Portal", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.exception_handler(ApiError)
async def _api_error(_req, e: ApiError):
    return JSONResponse({"error": e.msg}, status_code=e.status)


@app.middleware("http")
async def guard(request: Request, call_next):
    # CSRF: state-changing API calls must carry a custom header, which a cross-site form cannot send
    if (request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/api/")
            and request.headers.get("x-requested-with") != "tmn"):
        return JSONResponse({"error": "درخواست نامعتبر"}, status_code=403)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def optional_user(request: Request, db=Depends(get_db)) -> User | None:
    return user_from_token(db, request.cookies.get(COOKIE))


def user_required(u: User | None = Depends(optional_user)) -> User:
    if not u:
        raise ApiError("ابتدا وارد حساب کاربری شوید", 401)
    return u


def founder_required(u: User = Depends(user_required)) -> User:
    if u.role != "founder":
        raise ApiError("این بخش فقط برای بنیان‌گذار است", 403)
    return u


async def body(request: Request) -> dict:
    try:
        b = await request.json()
    except ValueError:
        b = None
    if not isinstance(b, dict):
        raise ApiError("بدنه‌ی درخواست نامعتبر است")
    return b


def set_cookie(resp: JSONResponse, token: str):
    resp.set_cookie(COOKIE, token, max_age=settings.session_days * 86400, httponly=True, samesite="lax",
                    secure=settings.cookie_secure, path="/")


def market_view(db) -> dict:
    m = with_freshness(kv_get(db, "market"))
    return {"source": m.get("source", settings.market_source), "fresh": m["fresh"], "ts": m.get("ts"),
            "data_ts": m.get("data_ts"), "regime": m.get("regime") or {}, "prices": m.get("prices") or {},
            "error": m.get("error", "")}


def sub_view(s: Subscription | None) -> dict | None:
    if not s:
        return None
    name = "بنیان‌گذار (دائمی)" if s.plan_key == "founder" else billing.PLANS.get(s.plan_key, {}).get("name", s.plan_key)
    return {"plan": s.plan_key, "name": name, "expires_at": s.expires_at, "days_left": max(0, int((s.expires_at - now()) // 86400))}


def profile_view(p: RiskProfile | None) -> dict | None:
    if not p:
        return None
    alloc = {"low": p.alloc_low, "medium": p.alloc_medium, "high": p.alloc_high}
    return {"score": p.score, "capacity": p.capacity, "willingness": p.willingness, "profile_key": p.profile_key,
            "profile_name": risk.profile_name(p.profile_key), "allocation": alloc, "answers": p.answers,
            "expected": risk.expected(alloc), "created_at": p.created_at}


def get_bot(db, user: User, create=True) -> BotAccount | None:
    bot = db.scalars(select(BotAccount).where(BotAccount.user_id == user.id)).first()
    if not bot and create:
        bot = BotAccount(user_id=user.id, state={})
        p = latest_profile(db, user.id)
        if p:
            bot.alloc_low, bot.alloc_medium, bot.alloc_high = p.alloc_low, p.alloc_medium, p.alloc_high
        db.add(bot)
        db.commit()
    return bot


# ================================================================== public
@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/meta")
def meta(db=Depends(get_db)):
    m = market_view(db)
    lo, me, hi = risk.founder_allocation()
    return {"strategies": risk.strategies(), "plans": list(billing.PLANS.values()), "features": billing.FEATURES,
            "payment_provider": settings.payment_provider,
            "market": {k: m[k] for k in ("source", "fresh", "regime", "ts", "data_ts")},
            "questions": len(risk.QUESTIONS), "founder_allocation": {"low": lo, "medium": me, "high": hi},
            "min_capital": MIN_CAPITAL, "anchors": risk.ANCHORS,
            "profiles": [{"upto": hi_, "key": k, "name": n} for hi_, k, n, _ in risk.PROFILES]}


@app.get("/api/me")
def me(u: User | None = Depends(optional_user), db=Depends(get_db)):
    if not u:
        return {"user": None}
    bot = get_bot(db, u, create=False)
    return {"user": {"id": u.id, "email": u.email, "name": u.name, "role": u.role},
            "profile": profile_view(latest_profile(db, u.id)), "subscription": sub_view(active_subscription(db, u.id)),
            "bot": {"status": bot.status, "mode": bot.mode} if bot else None}


# ==================================================================== auth
@app.post("/api/auth/signup")
async def signup(request: Request, db=Depends(get_db)):
    b = await body(request)
    email = str(b.get("email", "")).strip().lower()
    name = str(b.get("name", "")).strip()[:120]
    pw = str(b.get("password", ""))
    if not name:
        raise ApiError("نام را وارد کنید")
    if not EMAIL_RE.match(email):
        raise ApiError("ایمیل معتبر نیست")
    problem = password_problem(pw)
    if problem:
        raise ApiError(problem)
    if db.scalars(select(User).where(User.email == email)).first():
        raise ApiError("با این ایمیل قبلاً ثبت‌نام شده است")
    u = User(email=email, name=name, phone=str(b.get("phone", "")).strip()[:20], password_hash=hash_password(pw))
    db.add(u)
    db.flush()
    resp = JSONResponse({"ok": True})
    set_cookie(resp, create_session(db, u))
    db.commit()
    return resp


@app.post("/api/auth/login")
async def login(request: Request, db=Depends(get_db)):
    b = await body(request)
    email = str(b.get("email", "")).strip().lower()
    key = f"{request.client.host if request.client else '?'}|{email}"
    if login_limit.blocked(key):
        raise ApiError("تلاش‌های ناموفق زیاد بود؛ ۱۵ دقیقه‌ی دیگر دوباره امتحان کنید", 429)
    u = db.scalars(select(User).where(User.email == email)).first()
    if not u or not verify_password(str(b.get("password", "")), u.password_hash):
        login_limit.fail(key)
        raise ApiError("ایمیل یا رمز عبور اشتباه است", 401)
    login_limit.reset(key)
    resp = JSONResponse({"ok": True, "role": u.role})
    set_cookie(resp, create_session(db, u))
    db.commit()
    return resp


@app.post("/api/auth/logout")
def logout(request: Request, db=Depends(get_db)):
    drop_session(db, request.cookies.get(COOKIE))
    db.commit()
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE, path="/")
    return resp


# ==================================================================== risk
@app.get("/api/risk/questions")
def questions():
    return {"questions": [{"id": q["id"], "title": q["title"], "options": q["options"], "dim": q["dim"]}
                          for q in risk.QUESTIONS], "strategies": risk.strategies()}


@app.post("/api/risk/submit")
async def submit_risk(request: Request, u: User = Depends(user_required), db=Depends(get_db)):
    b = await body(request)
    answers = b.get("answers") or {}
    problem = risk.validate_answers(answers)
    if problem:
        raise ApiError(problem)
    answers = {q["id"]: int(answers[q["id"]]) for q in risk.QUESTIONS}
    r = risk.score(answers)
    p = RiskProfile(user_id=u.id, answers=answers, capacity=r["capacity"], willingness=r["willingness"],
                    score=r["score"], profile_key=r["profile_key"], alloc_low=r["allocation"]["low"],
                    alloc_medium=r["allocation"]["medium"], alloc_high=r["allocation"]["high"])
    db.add(p)
    bot = get_bot(db, u)
    if bot.mode == "paper" and bot.status != "running":
        bot.alloc_low, bot.alloc_medium, bot.alloc_high = p.alloc_low, p.alloc_medium, p.alloc_high
    db.commit()
    return {"profile": profile_view(p), "profile_desc": r["profile_desc"], "strategies": risk.strategies()}


@app.get("/api/risk/profile")
def get_profile(u: User = Depends(user_required), db=Depends(get_db)):
    p = latest_profile(db, u.id)
    return {"profile": profile_view(p), "strategies": risk.strategies(),
            "profile_desc": risk.profile_for(p.score)[2] if p else ""}


@app.post("/api/allocation")
async def set_allocation(request: Request, u: User = Depends(user_required), db=Depends(get_db)):
    b = await body(request)
    p = latest_profile(db, u.id)
    if not p:
        raise ApiError("ابتدا پرسشنامه‌ی ریسک را پر کنید")
    bot = get_bot(db, u)
    if bot.mode == "master":
        raise ApiError("تخصیص ربات اصلی از config.yaml خوانده می‌شود و از اینجا عوض نمی‌شود")
    if bot.status == "running":
        raise ApiError("برای تغییر تخصیص ابتدا ربات را متوقف کنید")
    rec = {"low": p.alloc_low, "medium": p.alloc_medium, "high": p.alloc_high}
    problem = risk.check_custom_allocation(rec, b)
    if problem:
        raise ApiError(problem)
    bot.alloc_low, bot.alloc_medium, bot.alloc_high = int(b["low"]), int(b["medium"]), int(b["high"])
    db.commit()
    return {"ok": True, "allocation": {"low": bot.alloc_low, "medium": bot.alloc_medium, "high": bot.alloc_high},
            "expected": risk.expected({"low": bot.alloc_low, "medium": bot.alloc_medium, "high": bot.alloc_high})}


# ================================================================= billing
@app.get("/api/billing")
def billing_info(u: User = Depends(user_required), db=Depends(get_db)):
    pays = db.scalars(select(Payment).where(Payment.user_id == u.id).order_by(Payment.id.desc()).limit(20)).all()
    return {"plans": list(billing.PLANS.values()), "features": billing.FEATURES, "provider": settings.payment_provider,
            "subscription": sub_view(active_subscription(db, u.id)),
            "payments": [{"id": x.id, "plan": billing.PLANS.get(x.plan_key, {}).get("name", x.plan_key),
                          "amount_tmn": x.amount_tmn, "provider": x.provider, "status": x.status, "ref_id": x.ref_id,
                          "created_at": x.created_at} for x in pays]}


@app.post("/api/billing/checkout")
async def checkout(request: Request, u: User = Depends(user_required), db=Depends(get_db)):
    b = await body(request)
    if u.role == "founder":
        raise ApiError("اشتراک بنیان‌گذار دائمی است")
    try:
        out = billing.start_payment(db, u, str(b.get("plan", "")))
        db.commit()
        return out
    except billing.PaymentError as e:
        db.commit()                     # keep the failed payment row for the record
        raise ApiError(str(e)) from e


@app.get("/api/billing/zarinpal/callback")
def zarinpal_callback(Authority: str = "", Status: str = "", db=Depends(get_db)):
    pay = billing.verify_zarinpal(db, Authority, Status)
    db.commit()
    ok = bool(pay and pay.status == "paid")
    return RedirectResponse(f"/#/billing?{'paid=1' if ok else 'failed=1'}", status_code=303)


# ===================================================================== bot
def bot_view(db, bot: BotAccount) -> dict:
    m = market_view(db)
    prices = m["prices"]
    out = {"id": bot.id, "mode": bot.mode, "status": bot.status, "capital_tmn": bot.capital_tmn,
           "allocation": {"low": bot.alloc_low, "medium": bot.alloc_medium, "high": bot.alloc_high},
           "started_at": bot.started_at, "last_tick_at": bot.last_tick_at,
           "market": {k: m[k] for k in ("source", "fresh", "regime", "ts", "data_ts", "error")}}
    st = bot.state or {}
    if bot.mode == "paper" and st.get("sleeves"):
        v = simulator.valuation(st, prices)
        sleeves = {"low": {"value": v["low"], "cash": st["sleeves"]["low"]["cash"], "positions": [], "state": "cash"}}
        for key, cfg_name, name in simulator.SLEEVES:
            sl = st["sleeves"][key]
            pos = []
            for a, p in sl["pos"].items():
                bid = (prices.get(a) or {}).get("bid") or p.get("last_bid") or 0.0
                pos.append({"asset": a, "qty": p["qty"], "cost": p["cost"], "price": bid, "value": p["qty"] * bid,
                            "pnl_pct": round((p["qty"] * bid / p["cost"] - 1) * 100, 2) if p["cost"] else 0.0})
            state = "stopped" if sl["stopped"] else ("holding" if sl["built"] else ("waiting" if sl["cash"] >= simulator.MIN_ORDER_TMN else "empty"))
            sleeves[key] = {"value": v[key], "cash": sl["cash"], "positions": pos, "state": state,
                            "stopped": sl["stopped"], "realised": sl["realised"]}
        out.update({"equity": v["equity"], "pnl_tmn": v["equity"] - bot.capital_tmn,
                    "pnl_pct": round((v["equity"] / bot.capital_tmn - 1) * 100, 3) if bot.capital_tmn else 0.0,
                    "fees_tmn": st.get("fees_tmn", 0.0), "sleeves": sleeves})
    return out


@app.get("/api/bot")
def get_bot_view(u: User = Depends(user_required), db=Depends(get_db)):
    bot = get_bot(db, u)
    p = latest_profile(db, u.id)
    sub = active_subscription(db, u.id)
    checks = {"profile": bool(p), "subscription": bool(sub), "market": market_view(db)["fresh"]}
    return {"bot": bot_view(db, bot), "checks": checks, "min_capital": MIN_CAPITAL,
            "expected": risk.expected({"low": bot.alloc_low, "medium": bot.alloc_medium, "high": bot.alloc_high})
            if bot.alloc_low + bot.alloc_medium + bot.alloc_high == 100 else None,
            "recommended": profile_view(p)["allocation"] if p else None}


@app.post("/api/bot/start")
async def start_bot(request: Request, u: User = Depends(user_required), db=Depends(get_db)):
    b = await body(request)
    bot = get_bot(db, u)
    if bot.mode == "master":
        raise ApiError("ربات اصلی روی لیارا اجرا می‌شود و از اینجا شروع یا متوقف نمی‌شود")
    if bot.status == "running":
        raise ApiError("ربات در حال اجراست")
    if not latest_profile(db, u.id):
        raise ApiError("ابتدا پرسشنامه‌ی ریسک را پر کنید")
    if not active_subscription(db, u.id):
        raise ApiError("برای شروع ربات اشتراک فعال لازم است", 402)
    try:
        capital = float(b.get("capital_tmn", 0))
    except (TypeError, ValueError):
        capital = 0.0
    if not MIN_CAPITAL <= capital <= MAX_CAPITAL:
        raise ApiError(f"سرمایه باید بین {MIN_CAPITAL:,} و {MAX_CAPITAL:,} تومان باشد")
    alloc = {"low": bot.alloc_low, "medium": bot.alloc_medium, "high": bot.alloc_high}
    if sum(alloc.values()) != 100:
        raise ApiError("تخصیص سرمایه مشخص نیست")
    ctx = simulator.start(bot, capital, alloc)
    snap = with_freshness(kv_get(db, "market"))
    ctx2 = simulator.step(bot, snap)            # act at once if the entry rule already holds
    db.add_all(ctx.events + ctx2.trades + ctx2.events)
    s = simulator.maybe_snapshot(bot, snap.get("prices") or {}, 0)
    if s:
        db.add(s)
    db.commit()
    return {"ok": True, "bot": bot_view(db, bot)}


@app.post("/api/bot/stop")
def stop_bot(u: User = Depends(user_required), db=Depends(get_db)):
    bot = get_bot(db, u)
    if bot.mode == "master":
        raise ApiError("ربات اصلی روی لیارا اجرا می‌شود و از اینجا شروع یا متوقف نمی‌شود")
    if bot.status != "running":
        raise ApiError("ربات در حال اجرا نیست")
    prices = market_view(db)["prices"]
    ctx = simulator.stop(bot, prices)
    db.add_all(ctx.trades + ctx.events)
    s = simulator.maybe_snapshot(bot, prices, 0)
    if s:
        db.add(s)
    db.commit()
    return {"ok": True, "bot": bot_view(db, bot)}


def history_rows(db, bot_id: int, hours: float) -> list:
    rows = db.execute(select(EquitySnapshot.ts, EquitySnapshot.equity_tmn, EquitySnapshot.low_tmn,
                             EquitySnapshot.medium_tmn, EquitySnapshot.high_tmn)
                      .where(EquitySnapshot.bot_id == bot_id, EquitySnapshot.ts > now() - hours * 3600)
                      .order_by(EquitySnapshot.ts)).all()
    return downsample([list(r) for r in rows], 500)


@app.get("/api/bot/history")
def bot_history(hours: float = 168, u: User = Depends(user_required), db=Depends(get_db)):
    bot = get_bot(db, u)
    return {"rows": history_rows(db, bot.id, min(hours, 24 * 400))}


@app.get("/api/bot/activity")
def bot_activity(u: User = Depends(user_required), db=Depends(get_db)):
    bot = get_bot(db, u)
    trades = db.scalars(select(BotTrade).where(BotTrade.bot_id == bot.id).order_by(BotTrade.id.desc()).limit(100)).all()
    events = db.scalars(select(BotEvent).where(BotEvent.bot_id == bot.id).order_by(BotEvent.id.desc()).limit(60)).all()
    return {"trades": [{"ts": t.ts, "sleeve": t.sleeve, "asset": t.asset, "side": t.side, "qty": t.qty, "price": t.price,
                        "notional_tmn": t.notional_tmn, "fee_tmn": t.fee_tmn, "reason": t.reason} for t in trades],
            "events": [{"ts": e.ts, "kind": e.kind, "text": e.text} for e in events]}


# ================================================================= founder
@app.get("/api/founder/overview")
def founder_overview(u: User = Depends(founder_required), db=Depends(get_db)):
    bot = get_bot(db, u)
    m = market_view(db)
    users = count(db, select(User.id))
    day, week = now() - 86400, now() - 7 * 86400
    running = db.scalars(select(BotAccount).where(BotAccount.status == "running", BotAccount.mode == "paper")).all()
    aum = sum(simulator.valuation(b.state, m["prices"])["equity"] for b in running if (b.state or {}).get("sleeves"))
    cap = sum(b.capital_tmn for b in running)
    latest_ids = select(func.max(RiskProfile.id)).group_by(RiskProfile.user_id)
    dist = dict(db.execute(select(RiskProfile.profile_key, func.count()).where(RiskProfile.id.in_(latest_ids))
                           .group_by(RiskProfile.profile_key)).all())
    paid = select(Payment).where(Payment.status == "paid", Payment.provider != "founder")
    platform = {
        "users": users, "signups_24h": count(db, select(User.id).where(User.created_at > day)),
        "signups_7d": count(db, select(User.id).where(User.created_at > week)),
        "active_subscriptions": count(db, select(Subscription.user_id).where(Subscription.expires_at > now(),
                                                                             Subscription.plan_key != "founder").distinct()),
        "revenue_tmn": db.scalar(select(func.coalesce(func.sum(Payment.amount_tmn), 0)).where(
            Payment.status == "paid", Payment.provider != "demo")) or 0,
        "demo_payments": count(db, paid.where(Payment.provider == "demo")),
        "running_bots": len(running), "paper_aum_tmn": aum, "paper_capital_tmn": cap,
        "profiles": {k: {"name": risk.profile_name(k), "count": dist.get(k, 0)} for _, k, *_ in risk.PROFILES},
    }
    lo, me, hi = risk.founder_allocation()
    return {"wallex": kv_get(db, "wallex", {"configured": bool(settings.wallex_api_key), "ok": False}),
            "bot": kv_get(db, "bot", {"configured": False, "ok": False}),
            "platform": platform, "market": {k: m[k] for k in ("source", "fresh", "regime", "ts", "error")},
            "allocation": {"low": lo, "medium": me, "high": hi},
            "wallex_history": history_rows(db, bot.id, 24 * 30),
            "config": {"bot_status_url": bool(settings.bot_status_url), "bot_logs_dir": bool(settings.bot_logs_dir),
                       "github": bool(settings.github_token), "wallex_key": bool(settings.wallex_api_key),
                       "payment_provider": settings.payment_provider, "market_source": settings.market_source}}


@app.get("/api/founder/users")
def founder_users(u: User = Depends(founder_required), db=Depends(get_db)):
    prices = market_view(db)["prices"]
    out = []
    for usr in db.scalars(select(User).order_by(User.id.desc()).limit(500)).all():
        p = latest_profile(db, usr.id)
        s = active_subscription(db, usr.id)
        bot = get_bot(db, usr, create=False)
        eq = None
        if bot and bot.mode == "paper" and (bot.state or {}).get("sleeves"):
            eq = simulator.valuation(bot.state, prices)["equity"]
        out.append({"id": usr.id, "name": usr.name, "email": usr.email, "role": usr.role, "created_at": usr.created_at,
                    "profile": risk.profile_name(p.profile_key) if p else None, "score": p.score if p else None,
                    "subscription": sub_view(s), "bot_status": bot.status if bot else None,
                    "allocation": [bot.alloc_low, bot.alloc_medium, bot.alloc_high] if bot else None,
                    "capital_tmn": bot.capital_tmn if bot else None, "equity_tmn": eq})
    return {"users": out}


# ================================================================== web UI
app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"), headers={"Cache-Control": "no-cache"})
