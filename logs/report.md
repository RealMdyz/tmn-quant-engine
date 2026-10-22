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

- Equity: **4,992,529 TMN** (-0.149%)
- Max drawdown: **0.462%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 4 (sources: {'llm:boxapi': 4})
- Events: {'coin_skipped': 385, 'live_self_test': 55, 'cancel_all': 3, 'startup': 3, 'regime': 3, 'policy': 4, 'sleeve_order': 68, 'quote': 5, 'buy_blocked': 252, 'buy_unblocked': 238, 'state_restored': 54, 'sleeve_fill': 5}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 0.9,
    "GALA": 1.0,
    "AVAX": 1.3
  },
  "pause": false,
  "reasoning": "I pick SUI (spread 185.3 bps, vol24h 5,790M TMN, fv_vol 83.6 bps) because its Toman spread is wide and book is currently quoted; set h=0.9% to be reasonably aggressive given the wide spread. GALA has a 100.2 bps spread and very large USDT/TMN spread (446.9 bps) with decent activity (vol24h 2,225M TMN) so I quote at h=1.0% to capture that premium while remaining cautious. AVAX meets the 80 bps minimum (93.4 bps) but has higher fv volatility (140.9 bps), so I set h=1.3% to avoid being picked off; it is quoted now and vol24h 3,064M TMN. No market pause — no headline shock detected and several suitable wide spreads exist. Sleeves: USDT/TMN 48h +4.38% gives full exposure cap (1.0), so keep rial at 1.0 (benefits from rial weakness) and keep beta at 1.0; beta_assets are PEPE/ADA/LINK (the current sleeve weights and highest momentum names in the beta universe).",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
