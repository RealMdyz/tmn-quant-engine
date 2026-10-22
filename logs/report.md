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

- Equity: **4,962,018 TMN** (-0.760%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 6 (sources: {'llm:boxapi': 6})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 6, 'sleeve_order': 68, 'quote': 26, 'buy_blocked': 504, 'buy_unblocked': 471, 'state_restored': 57, 'sleeve_fill': 5, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "BNB": 1.0,
    "CAKE": 0.9,
    "GALA": 1.2
  },
  "pause": false,
  "reasoning": "I choose up to three markets with Toman spread >=80 bps and no active buy-block: BNB (spread 81.5 bps, vol24h 80,944M TMN, fv_vol 146.3 bps) as the main slot with h=1.0% for balanced width vs activity; CAKE (spread 85.2 bps, fv_vol 39.8 bps, vol24h 2,557M) gets a tighter h=0.9% because FV is very calm; GALA (spread 161.6 bps, usdt_spread 391.1 bps, fv_vol 223 bps, quoted_now=true) gets h=1.2% to protect against its higher FV volatility. I avoid FIL/CHZ/DOT/AVAX/UNI/etc. because they show Toman-book sliding or buy_blocked flags or spreads below our 80 bps threshold. Sleeves: keep rial at 1.0 exposure (USDT/TMN 48h +4.41% → regime cap 1.0 and rial currently scale 1.0, value_tmn 2,601,842) and keep beta at 0.9 (current scale_now 0.9, return -0.98%) with beta assets PEPE/ADA/LINK (existing universe weights) because the rial-weakening regime and capital caps justify maintaining exposure while slightly cautious on beta by not increasing beyond current 0.9.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
