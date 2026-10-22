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

- Equity: **4,952,678 TMN** (-0.946%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 22 (sources: {'llm:boxapi': 22})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 22, 'sleeve_order': 169, 'quote': 259, 'buy_blocked': 1557, 'buy_unblocked': 1521, 'state_restored': 57, 'sleeve_fill': 8, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 0.9,
    "GALA": 1.5,
    "CAKE": 1.2
  },
  "pause": false,
  "reasoning": "Picked SUI (spread 143.8 bps, low fv_vol 25 bps and quoted_now) so I can quote tighter at h=0.9% to capture wide Toman spread with low FV volatility. Picked GALA because its Toman spread is 161.3 bps and USDT spread 565 bps but fv_vol is large (922.5 bps) so I widen to h=1.5% to avoid being picked off. Picked CAKE (spread 92.5 bps, fv_vol 65.6 bps, vol24h 2.3bn TMN) with h=1.2% as a moderate-width choice. No market-wide pause: several markets show buy_blocked (FIL, DOT, BNB, AVAX) so I avoided them. Sleeves: keep rial at full 1.0 exposure because USDT/TMN 48h +4.33% (regime cap=1.0) and rial sleeve scale_now=1.0 with return -0.59%; keep beta at 0.8 matching current scale_now (capital scaled) and continue with PEPE/ADA/LINK which are the sleeve weights and available momentum candidates.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
