# TMN Quant Engine — run report

## SHADOW

- Equity: **4,997,751 TMN** (-0.045%)
- Max drawdown: **0.045%**
- Traded volume: 899,480 TMN

![equity](equity_shadow.png)

- Market maker: **1 fills** (1 buys, 0 sells), 0 risk exits, realised PnL **0 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |

- AI supervisor decisions: 24 (sources: {'fallback': 1, 'llm:boxapi': 23})
- Events: {'startup': 30, 'policy': 24, 'quote': 958, 'state_restored': 28, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 441, 'buy_unblocked': 353, 'instance_superseded': 17, 'fill': 1}

### Latest AI decision
```json
{
  "markets": {
    "BNB": 0.35,
    "FIL": 0.3,
    "CHZ": 0.25,
    "WLD": 0.35,
    "AAVE": 0.25
  },
  "pause": false,
  "reasoning": "I pick markets with wide Toman spreads well above the 50 bps round-trip fee and reasonable activity: BNB has spread_bps 81.5 with vol24h_mtmn 74,277 so I quote with h=0.35 to balance flow and adverse selection (fv_vol_bps 39.2). FIL and CHZ have the largest spreads (90.2 and 91.1 bps) and low fv_vol_bps (4.9 and 4.3) so I quote tighter to sit at the top: FIL h=0.30, CHZ h=0.25. WLD has the biggest spread_bps (98.1) but lower volume (vol24h_mtmn 1,494) and moderate fv_vol_bps 27.5 so I use h=0.35. AAVE (spread_bps 67.0, vol24h_mtmn 2,833, fv_vol_bps 5.7) looks calm and wide enough to quote near the top so h=0.25. No markets show buy_blocked or coin-specific shocks, so pause=false.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
