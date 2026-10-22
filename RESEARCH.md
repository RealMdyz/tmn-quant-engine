# Research log — how the strategy was chosen

All numbers come from real Wallex data pulled on 2026-10-22 (10 days of 1-minute bars aggregated
to 5 minutes for 29 coins on both the Toman and Tether books, plus 29 days of hourly bars) and from
the live order books. Scripts are in `research/scripts/`, data in `data/`.

## 1. Facts measured from the API
| item | value |
|---|---|
| challenge package | id 183, loan 5,000,000 TMN, no collateral, no daily fee, 3 days, liquidation at 900 TMN |
| allowed markets | everything except ~300 listed in `/v1/prop/packages/183` → `unavailableMarkets` |
| account fees (tier 1) | Toman maker 0.25% / taker 0.30% · Tether maker 0.10% / taker 0.13% |
| capital in USD | 5M TMN ≈ 18.7 USDT → zero market impact on liquid books |
| USDT/TMN | +17.5% in 29 days, but lumpy (10-day +0.27%, daily vol 1.6%) |
| candle API quirk | `resolution=15` returns 1-minute bars for 10 days; `60` returns ~29 days |

## 2. Rejected: directional strategies (net of real fees)
| strategy (data) | trades | avg net / trade |
|---|---|---|
| Donchian breakout, hourly, 27 coins | 395 | −73 bps |
| 24h momentum, hourly | 426 | −46 bps |
| EMA 12/48 cross, hourly | 218 | −34 bps |
| dip-buy 3×ATR, hourly | 278 | −37 bps |
| RSI<28 mean reversion, hourly | 96 | +16 bps (not significant) |
| RSI / Bollinger / breakout / EMA on 5-min, USDT books (fee 0.13%) | 128–396 each | −1 to −53 bps |
| same on Toman books (fee 0.30%) | 128–250 each | −38 to −75 bps |
| ML triple-barrier gradient boosting (v1 of this repo) | — | negative after fees in walk-forward |

In rolling 3-day windows even the best trend rule on USDT/TMN won only ~50% of the time.
Literature agrees: intraday crypto momentum break-even costs are 3–10 bps (Shen, Urquhart & Wang 2022).

## 3. Accepted: hedged fair-value arbitrage between Toman and Tether books
- Deviation of the Toman price from `COINUSDT × USDTTMN` (1-min closes): std 17–99 bps,
  strongly mean-reverting (autocorrelation 0.1–0.4 after 60 min).
- Episodes with |deviation| > 1% in 10 days: TRX 134, ADA 126, PEPE 103, DOGE 55, BNB 55, SOL 25 …
- Taker-only triangle (buy Toman ask, sell USDT bid, sell USDT) costs ~0.73%: live book sampling at
  night found no taker opportunities → the edge must be captured with **maker** bids.
- Maker version, walk-forward (margin chosen on days 1–5, tested on days 6–10): the first backtest
  reported +21 / +39 bps per fill and 80–90% wins. **These numbers are wrong — see §5.**
- Adverse selection is real and coin-specific: ETH, XRP, PEPE, SOL, SUI, S, ARB lose because their
  Toman dips are genuine crashes that the USDT book confirms → excluded / learned by the bandit.
- A supervised classifier predicting which fills will be profitable reached only AUC 0.58 out of
  sample and did not beat per-market margins chosen on the train half → we use per-market
  Thompson-sampling bandits (online learning from live fills) instead.

## 4. Role of the LLM — evidence-based
"The Alpha Illusion" (2026) shows reported LLM-agent trading alpha does not survive leakage and cost
controls; recommended use is upstream context/news extraction with final authority in audited modules.
Our agent therefore supervises (market enable/disable on structural dislocations, margin scaling in
news shocks, USDT inventory policy) and never sizes or executes trades itself.

## 5. Correction (2026-10-22): the backtest edge was a stale-price artefact
Found while investigating why the shadow test made zero fills.

**Data fact.** The Wallex coin/USDT books are thin: share of 5-minute bars with at least one trade —
TRXUSDT 14%, ADAUSDT 20%, DOGEUSDT 20%, PENGUUSDT 6%, AAVEUSDT 7% (BTCUSDT 63%). A candle close is
therefore usually a price from tens of minutes earlier.

**The bug.** The first backtest priced both the fair value and the HEDGE at that stale close. When a
global move hit, the Toman book moved first, our bid "filled", and the backtest sold on USDT at the
pre-move price that no longer existed.

| original fills (0.8% margin) | n | avg net | win |
|---|---|---|---|
| all | 2400 | +36 bps | 81% |
| coin/USDT actually traded in the hedge bar | 640 | **-78 bps** | 30% |
| no coin/USDT trade in the hedge bar (stale price) | 1760 | +78 bps | 99% |

After a fill the next real coin/USDT trade was a median **-147 bps** below the fair value used for the
bid (the bid sat at -148 bps): the dips were real price moves (adverse selection), not hasty sellers.

**Re-run with the hedge at the next REAL coin/USDT trade** (22 coins, one fill per 15-min episode):
0.4% margin -73 bps (30% win) · 0.8% -63 · 1.3% -59 · 2% -28 · 3% +14 bps (70 fills in 10 days).

**Only candidate edge — sudden dips out of a calm book.** Keeping only fills where the Toman price was
not already below fair value in the previous bar: 1.3% +3 bps (38 fills), 2% +40 (13), 3% +68 (8);
with the worst-of hedge price (`python run.py backtest --cached`): 1.3% -54, 2% -33, 3% +42 bps
(12 fills over 29 coins). First half vs second half disagree in sign at 1.3–2%. **No margin shows a
statistically reliable edge.**

**Live order books agree.** 136 samples (30 s apart, 2026-10-22 10:12–11:17) from the shadow run:
the Toman best bid stays within roughly ±10–70 bps (std) of the live liquidation value; it was below
-108 bps (fees + smallest margin) in 0–1.5% of samples and never below -148 bps. USDT/TMN best bid
was exactly 266,720 in all samples (65 min) — verified now every minute against /v1/depth and trades.

**Consequences in the code.**
- Backtest rewritten (`bot/backtest_arb.py`): flash-dip guard, hedge at next real trade (worst of
  close/low), margins 1.3–4%; pooled per-margin results feed one realistic bandit prior for all coins.
- Live/shadow guards (`ArbEngine.update_guard`): no quote while the Toman book slides >0.3% below its
  30-min baseline, while the coin/USDT fair value fell >0.5% in 60 s, while the coin/USDT top of book
  has been frozen 15 min, or while USDT/TMN trades print outside the book.
- Shadow fills now come from the real trade tape (a print below our bid fills us); the old book-only
  simulator could not see a seller sweeping through our level, so it could never fill.
- `logs/books_<mode>.csv` records top of book of every market every 10 s to measure the real edge
  (both directions) from live data.

**Competition.** Other teams may run the same idea. Price-time priority means the shallowest bids are
hit first — and the evidence above says shallow fills are the toxic ones, so competitors quoting
tighter absorb adverse flow before it reaches our deep bids; a large panic sell sweeps every
participant (each holds ~18.7 USDT). Our bids are randomised by the bandit's margin choice.
