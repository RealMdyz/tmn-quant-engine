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

- Equity: **4,946,879 TMN** (-1.062%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 5 (sources: {'llm:boxapi': 5})
- Events: {'coin_skipped': 392, 'live_self_test': 56, 'cancel_all': 4, 'startup': 4, 'regime': 4, 'policy': 5, 'sleeve_order': 68, 'quote': 5, 'buy_blocked': 375, 'buy_unblocked': 347, 'state_restored': 55, 'sleeve_fill': 5, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "CAKE": 0.9,
    "CHZ": 1.2,
    "GALA": 1.4
  },
  "pause": false,
  "reasoning": "I pick CAKE/CHZ/GALA because the bot never quotes where spread_bps < 80: CAKE has the largest Toman spread 143.7 bps (fv_vol 22 bps, calm), CHZ 84.4 bps (fv_vol 87 bps) and GALA 80.5 bps (fv_vol 163.5 bps) are the only candidates ≥80 bps with no buy_blocked. I set CAKE h=0.9% because its fv_vol is very low (22 bps) and volume is reasonable (vol24h 2.14kM TMN) so we can tighten; CHZ h=1.2% because spread is just above threshold (84 bps) with moderate fv_vol (87 bps); GALA h=1.4% because it is quoted_now, has higher fv_vol (163.5 bps) and we want wider protection. pause=false since there is no market-wide shock in news and USDT/TMN is in a rial-weakening regime (48h +4.36%) so sleeves remain active. For sleeves I keep rial at 1.0 (regime cap 1.0, USDT/TMN 48h +4.36%) and reduce beta to 0.9 to be slightly conservative given its recent return -1.39% and higher volatility; beta assets chosen PEPE/ADA/LINK follow the sleeve weights and momentum within the beta universe.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
