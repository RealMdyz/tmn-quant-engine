# TMN Quant Engine — run report

## SHADOW

- Equity: **4,964,229 TMN** (-0.715%)
- Max drawdown: **0.866%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 33 (sources: {'fallback': 1, 'llm:boxapi': 32})
- Events: {'startup': 41, 'policy': 33, 'quote': 1318, 'state_restored': 38, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 1081, 'buy_unblocked': 909, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 7, 'coin_skipped': 63, 'regime': 9, 'sleeve_order': 56, 'sleeve_order_failed': 5, 'sleeve_fill': 26, 'state_reset': 1}

### Latest AI decision
```json
{
  "markets": {
    "GALA": 1.0,
    "CHZ": 0.9,
    "DOT": 1.5
  },
  "pause": false,
  "reasoning": "I pick GALA and CHZ because both have Toman spreads above our 80 bps threshold (GALA 100.0 bps, CHZ 83.4 bps) and reasonable 24h TMN volumes (GALA 2,307m, CHZ 1,729m); GALA's fv_vol is moderate (224 bps) so h=1.0% is appropriate, CHZ's fv_vol is low (59 bps) so h=0.9% to quote more aggressively. I include DOT as a third slot because its Toman spread is very wide (137.7 bps) albeit with extreme fv volatility (2,306 bps), so I set h=1.5% to protect against adverse selection. I avoid ARB (buy_blocked: book sliding) and other sub-80-bps markets (e.g. SOL 38 bps, XRP 29.3 bps). For sleeves, USDT/TMN 48h +4.06% keeps us in the rial-weakening regime, so keep rial exposure at 1.0 (full); beta stays at the engine's current scale 0.8 and I keep the beta assets to PEPE/ADA/LINK (the current beta weights) to capture momentum while respecting the sleeve's stop and the end_wind_down schedule.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

- Equity: **4,933,482 TMN** (-1.330%)
- Max drawdown: **3.519%**
- Traded volume: 234,959 TMN

![equity](equity_live.png)

- Market maker: **1 fills** (1 buys, 0 sells), 1 risk exits, realised PnL **-2,109 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| PENGU | 1 | 0 | 1 | -2,109 |

- AI supervisor decisions: 92 (sources: {'llm:boxapi': 92})
- Events: {'coin_skipped': 441, 'live_self_test': 63, 'cancel_all': 11, 'startup': 11, 'regime': 14, 'policy': 92, 'sleeve_order': 329, 'quote': 2763, 'buy_blocked': 6462, 'buy_unblocked': 6401, 'state_restored': 62, 'sleeve_fill': 30, 'orphan_adopted': 1, 'fill': 1, 'exit': 1}

### Latest AI decision
```json
{
  "markets": {
    "APE": 0.9,
    "CHZ": 1.3,
    "HYPE": 1.4
  },
  "pause": false,
  "reasoning": "I pick APE, CHZ and HYPE because they are the only candidates with Toman spreads comfortably >=80 bps: APE spread 175.4 bps (vol24h 5305 M TMN, fv_vol 91.2 bps) so I can quote relatively tight h=0.9; CHZ spread 147.0 bps (usdt_spread 261.3 bps, vol24h 505 M TMN) but very noisy fv_vol 764 bps so I widen to h=1.3; HYPE spread 92.4 bps (vol24h 2002 M TMN) is chosen cautiously despite a low usdt_spread 6.1 bps and fv_vol 215.2 bps, so I set a wide h=1.4. I avoid markets with buy blocks or frozen USDT books (PENGU avg round trip -178.3 bps and buy_blocked; GALA/WLD frozen; IMX/DOT/AVAX sliding) and any market with spread_bps <80 (e.g. SOL, BNB, ARB). Sleeves are set to zero because the regime cap is 0.0 (USDT/TMN 48h +0.71% -> no exposure cap allowed), so rial and beta exposures remain 0.0; beta_assets mirror the sleeve weights PEPE/ADA/LINK.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
