"""Subscription plans and payment providers.

demo     : the payment succeeds at once (for testing the flow; shown as "پرداخت آزمایشی").
zarinpal : Zarinpal v4 (request -> StartPay redirect -> callback -> verify). Amounts are sent in Rial.
"""
from __future__ import annotations

import logging

import requests

from .db import Payment, Subscription, now
from .settings import settings

log = logging.getLogger("portal.billing")

PLANS = {
    "monthly": {"key": "monthly", "name": "ماهانه", "days": 30, "price_tmn": 490_000, "badge": ""},
    "quarterly": {"key": "quarterly", "name": "سه‌ماهه", "days": 90, "price_tmn": 1_290_000, "badge": "۱۲٪ تخفیف"},
    "yearly": {"key": "yearly", "name": "سالانه", "days": 365, "price_tmn": 4_490_000, "badge": "۲۴٪ تخفیف"},
}
FEATURES = ["پرسشنامه‌ی ریسک و تخصیص شخصی بین ۳ استراتژی", "ربات معامله‌گر ۲۴ ساعته با نظارت AI",
            "داشبورد لحظه‌ای سود و زیان و تاریخچه‌ی معاملات", "حد ضرر چندلایه و توقف خودکار در شوک بازار"]


class PaymentError(Exception):
    pass


def _zp_base():
    return "https://sandbox.zarinpal.com" if settings.zarinpal_sandbox else "https://payment.zarinpal.com"


def start_payment(db, user, plan_key: str) -> dict:
    """Creates a pending payment. Returns {"redirect": url} for a gateway or {"paid": True} for demo."""
    plan = PLANS.get(plan_key)
    if not plan:
        raise PaymentError("پلن نامعتبر است")
    pay = Payment(user_id=user.id, plan_key=plan_key, amount_tmn=plan["price_tmn"], provider=settings.payment_provider)
    db.add(pay)
    db.flush()
    if settings.payment_provider == "demo":
        pay.authority = f"DEMO-{pay.id}"
        complete_payment(db, pay, ref_id=f"DEMO-{pay.id}")
        return {"paid": True, "payment_id": pay.id}
    if settings.payment_provider == "zarinpal":
        if not settings.zarinpal_merchant:
            raise PaymentError("درگاه پرداخت تنظیم نشده است (ZARINPAL_MERCHANT_ID)")
        body = {"merchant_id": settings.zarinpal_merchant, "amount": plan["price_tmn"] * 10,
                "callback_url": f"{settings.public_url}/api/billing/zarinpal/callback",
                "description": f"اشتراک {plan['name']} ربات TMN", "metadata": {"email": user.email}}
        try:
            r = requests.post(f"{_zp_base()}/pg/v4/payment/request.json", json=body, timeout=20)
            data = (r.json() or {}).get("data") or {}
        except (requests.RequestException, ValueError) as e:
            raise PaymentError(f"اتصال به درگاه ناموفق بود: {e}") from e
        if data.get("code") != 100 or not data.get("authority"):
            pay.status = "failed"
            raise PaymentError("درگاه درخواست پرداخت را نپذیرفت")
        pay.authority = data["authority"]
        return {"redirect": f"{_zp_base()}/pg/StartPay/{pay.authority}", "payment_id": pay.id}
    raise PaymentError("روش پرداخت ناشناخته است")


def verify_zarinpal(db, authority: str, status: str) -> Payment | None:
    pay = db.query(Payment).filter(Payment.authority == authority).first()
    if not pay or pay.status != "pending":
        return pay
    if status != "OK":
        pay.status = "failed"
        return pay
    try:
        r = requests.post(f"{_zp_base()}/pg/v4/payment/verify.json", timeout=20,
                          json={"merchant_id": settings.zarinpal_merchant, "amount": pay.amount_tmn * 10,
                                "authority": authority})
        data = (r.json() or {}).get("data") or {}
    except (requests.RequestException, ValueError) as e:
        log.warning("zarinpal verify failed: %s", e)
        return pay                      # stays pending; the user can retry the callback page
    if data.get("code") in (100, 101):
        complete_payment(db, pay, ref_id=str(data.get("ref_id", "")))
    else:
        pay.status = "failed"
    return pay


def complete_payment(db, pay: Payment, ref_id: str):
    plan = PLANS[pay.plan_key]
    pay.status, pay.ref_id, pay.paid_at = "paid", ref_id, now()
    # a renewal before expiry extends the current subscription instead of overlapping it
    cur = (db.query(Subscription).filter(Subscription.user_id == pay.user_id, Subscription.expires_at > now())
           .order_by(Subscription.expires_at.desc()).first())
    start = cur.expires_at if cur else now()
    db.add(Subscription(user_id=pay.user_id, plan_key=pay.plan_key, started_at=start,
                        expires_at=start + plan["days"] * 86400, payment_id=pay.id))
