# TMN Quant Engine

موتور معاملاتی خودکار روی صرافی والکس. استراتژی فعلی یک **بازارساز «ارزش منصفانه»** در بازارهای تومانی است (`strategy: mm`): ارزش منصفانه از بازار تتری می‌آید، سفارش خرید و فروش Maker دو طرف آن گذاشته می‌شود، و **ایجنت LLM تصمیم می‌گیرد** در کدام بازارها و با چه پهنایی معامله شود. استراتژی قبلی (آربیتراژ پوشش‌داده‌شده، `strategy: arb`) هم در کد مانده است.

- منطق کامل الگوریتم، شرایط خرید و فروش، و مدیریت ریسک: [STRATEGY.md](STRATEGY.md)
- تحقیق و دلیل انتخاب استراتژی (و استراتژی‌هایی که رد شدند): [RESEARCH.md](RESEARCH.md)

## نصب و اجرا

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt   # research/ scripts: requirements-research.txt
cp .env.example .env        # WALLEX_API_KEY و LLM_API_KEY را وارد کنید
```

| دستور | کار |
|---|---|
| `python run.py check` | اتصال، کلید، موجودی، کارمزد، بازارهای مجاز پکیج، شکاف فعلی، LLM، اخبار |
| `python run.py backtest --cached` | بک‌تست walk-forward روی داده‌ی واقعی موجود در `data/` (بدون نیاز به اینترنت) |
| `python run.py backtest` | همان بک‌تست با دانلود داده‌ی تازه |
| `python run.py shadow` | تست سایه: دفترهای زنده با پرشدن شبیه‌سازی‌شده |
| `python run.py live --yes` | معامله‌ی واقعی روی حساب چالش |
| `python run.py flatten` | اضطراری: لغو همه‌ی سفارش‌ها و تبدیل همه‌چیز به تومان |
| `python run.py report` | ساخت `logs/report.md` همراه با نمودارها |
| `python run.py probe` | تصویر فقط‌خواندنی از بازار برای تحقیق (`logs/probe/`)؛ روی سرور با هر استقرار خودکار اجرا می‌شود |

## استقرار روی سرور
`deploy/bootstrap.sh` روی اوبونتو اجرا می‌شود: کلیدها را می‌پرسد (فقط در `.env` با دسترسی 600 ذخیره می‌شوند)، محیط پایتون را می‌سازد و سرویس systemd را نصب می‌کند. سرپرست (`deploy/supervisor.py`):
- ربات را در حالتی که در `control/mode.txt` نوشته شده (`shadow` / `live` / `off`) اجرا می‌کند،
- هر ۳ دقیقه کد جدید را از GitHub می‌گیرد و در صورت تغییر ربات را ری‌استارت می‌کند،
- هر ۱۰ دقیقه لاگ‌ها و گزارش را روی شاخه‌ی `runtime-logs` منتشر می‌کند.

## خروجی‌های قابل بررسی
- `logs/decisions_<mode>.jsonl`: لاگ تصمیم برای هر quote، پرشدن، پوشش، تبدیل تتر و تصمیم AI، همراه با دلیل
- `logs/equity_<mode>.csv`: ارزش حساب، افت، تعداد پرشدن‌ها، سود محقق‌شده و حجم، به‌صورت دقیقه‌ای
- `logs/deviations_<mode>.csv`: شکاف هر بازار هر ۳۰ ثانیه
- `results/backtest/`: نتایج و نمودار بک‌تست walk-forward

## ساختار
```
run.py                  CLI
config.yaml             همه‌ی پارامترها (کوین‌ها، priorهای بک‌تست، ریسک، ایجنت)
bot/wallex_client.py    کلاینت REST (retry، 429، depth_all، پکیج اعتباری)
bot/arb.py              ارزش نقدشوندگی، کارمزدها، Bandit (Thompson Sampling)
bot/mm_engine.py        موتور بازارساز (استراتژی فعلی، live/shadow)
bot/arb_engine.py       موتور آربیتراژ (نسخه‌ی ۲)
bot/backtest_mm.py      بک‌تست بازارساز
bot/instance.py         قفل تک‌نسخه‌ای
bot/probe.py            جمع‌آوری داده‌ی فقط‌خواندنی از داخل ایران
bot/brokers.py          LiveExec / PaperExec
bot/agent.py            ایجنت LLM با ابزار + خواندن خبر
bot/risk.py             موتور ریسک قطعی
bot/backtest_arb.py     بک‌تست walk-forward
bot/report.py           گزارش
deploy/                 نصب سرور و سرپرست
research/               اسکریپت‌های تحقیق و نسخه‌ی ۱ (جهت‌دار، ردشده)
data/                   داده‌ی واقعی والکس برای بازتولید بک‌تست
```
