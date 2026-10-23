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

- Equity: **5,022,846 TMN** (+0.457%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 44 (sources: {'llm:boxapi': 44})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 44, 'sleeve_order': 169, 'quote': 1011, 'buy_blocked': 3190, 'buy_unblocked': 3155, 'state_restored': 57, 'sleeve_fill': 8, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "CHZ": 0.9,
    "CAKE": 1.1,
    "DOT": 1.4
  },
  "pause": false,
  "reasoning": "Pick CHZ because spread_bps is very wide (228.9 bps) with low fv_vol_bps (41.5) and reasonable vol24h_mtmn (3026) — favour tighter half-spread h=0.9% to capture the large Toman spread with low fair-value volatility. Pick CAKE because spread_bps is above our 80 bps floor (88.8 bps), quoted_now (active) and moderate fv_vol_bps (165.4) so use medium h=1.1% to avoid being picked off. Pick DOT as a wide-spread, liquid candidate (spread_bps 146.7) but very high fv_vol_bps (1014.3) so set wide h=1.4% to protect versus volatility. Do not pause (no market-wide shock in news). Keep the 'rial' sleeve fully exposed (1.0) because USDT/TMN 48h +4.33% places us in the rial-weakening regime (cap 1.0) and the rial sleeve has held steady (return -0.01%). Keep 'beta' at 0.8 (current scale_now) since beta has returned 2.23% on capital 2.25M TMN and is performing well, so retain PEPE/ADA/LINK as the 3 beta assets.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
