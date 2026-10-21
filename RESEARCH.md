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
- Maker version, walk-forward (margin chosen on days 1–5, tested on days 6–10), pessimistic fills/hedges:
  * 9 main coins: 162 fills, +21.3 bps avg, 80% win, **+2.94% in 5 days, max DD 1.96%**
  * 20 other coins: 1,056 fills, +39.0 bps avg, 90% win, **+1.82% in 5 days, max DD 1.18%**
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
