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

- Equity: **4,964,398 TMN** (-0.712%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 11 (sources: {'llm:boxapi': 11})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 11, 'sleeve_order': 68, 'quote': 58, 'buy_blocked': 774, 'buy_unblocked': 740, 'state_restored': 57, 'sleeve_fill': 5, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 1.2,
    "GALA": 1.4,
    "BCH": 1.3
  },
  "pause": false,
  "reasoning": "Pick SUI/GALA/BCH because the bot never quotes where spread_bps <80 and these three pass: SUI spread 114 bps with usdt_spread 62.6 and fv_vol 93 bps (relatively stable fair value) so I quote at h=1.2%. GALA has spread 101 bps, huge USDT/TMN dislocation (usdt_spread 393 bps) and premium +81.5 bps; fair-value volatility 202.7 bps so I go wider at h=1.4% to avoid being picked off. BCH has spread 88.4 bps, usdt_spread 55.7 and fv_vol 201.5 bps so I set h=1.3% to balance spread capture and volatility. I avoid markets with buy_blocked or frozen USDT books (FIL, DOT, CHZ, CAKE, etc.) and any spread <80 bps (SOL, XRP, ARB, …). Sleeves: keep rial at full exposure 1.0 because USDT/TMN 48h +4.42% (regime cap 1.0) and rial sleeve scale_now=1.0; keep beta at 0.9 (its scale_now 0.9) and select PEPE/ADA/LINK (current beta weights/universe) to retain momentum exposure while not increasing risk ahead of the wind-down schedule.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
