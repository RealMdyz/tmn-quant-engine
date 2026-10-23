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

- Equity: **4,956,475 TMN** (-0.870%)
- Max drawdown: **3.064%**
- Traded volume: 234,959 TMN

![equity](equity_live.png)

- Market maker: **1 fills** (1 buys, 0 sells), 1 risk exits, realised PnL **-2,109 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| PENGU | 1 | 0 | 1 | -2,109 |

- AI supervisor decisions: 83 (sources: {'llm:boxapi': 83})
- Events: {'coin_skipped': 441, 'live_self_test': 63, 'cancel_all': 11, 'startup': 11, 'regime': 13, 'policy': 83, 'sleeve_order': 303, 'quote': 2391, 'buy_blocked': 5748, 'buy_unblocked': 5686, 'state_restored': 62, 'sleeve_fill': 24, 'orphan_adopted': 1, 'fill': 1, 'exit': 1}

### Latest AI decision
```json
{
  "markets": {
    "CHZ": 0.9,
    "CAKE": 1.0,
    "GALA": 1.3
  },
  "pause": false,
  "reasoning": "I pick CHZ, CAKE and GALA because they clear the 80 bps minimum spread filter: CHZ spread 173.3 bps with low fv_vol 31.2 bps (calm) so I quote relatively tight at h=0.9% to earn the fat spread while avoiding being too aggressive. CAKE has spread 104.2 bps, vol24h 2.744bn TMN and fv_vol 69.9 bps so I set h=1.0% (moderate width). GALA is borderline but spread 80.5 bps with high USDT spread 163.9 bps and fv_vol 205.6 bps so I widen to h=1.3% to protect against volatility. I avoid PENGU and FIL: PENGU produced a live loss (realised -2,109 TMN, avg round trip -178.3 bps) so I stop quoting it; FIL had prior adverse fills and is quoted_now so I avoid it. Sleeves: USDT/TMN 48h +1.49% places us in the rial-weakening regime (cap 1.0), so I keep the rial sleeve at scale_now 0.75 (matches current scale and targets BTC/ETH mix) and keep beta at 0.5 (current scale_now 0.5 and positive small performance), with beta assets PEPE/ADA/LINK per the sleeve weights and universe.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
