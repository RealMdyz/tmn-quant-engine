# TMN Quant Engine — run report

## SHADOW

- Equity: **4,977,685 TMN** (-0.446%)
- Max drawdown: **0.668%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 32 (sources: {'fallback': 1, 'llm:boxapi': 31})
- Events: {'startup': 41, 'policy': 32, 'quote': 1301, 'state_restored': 38, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 991, 'buy_unblocked': 813, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 7, 'coin_skipped': 63, 'regime': 9, 'sleeve_order': 56, 'sleeve_order_failed': 5, 'sleeve_fill': 26, 'state_reset': 1}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 1.5,
    "CAKE": 1.0
  },
  "pause": false,
  "reasoning": "I pick FIL and CAKE because the bot never bids where Toman spread <80 bps: FIL spread_bps=97.3 (quoted_now=true) and CAKE spread_bps=80.4 meet that rule; other wide names (UNI, ARB, CHZ, AVAX, DOT) are buy_blocked or book-frozen so I avoid them. FIL gets a wide half-spread h=1.5% because fv_vol_bps=62.6 is moderate but FIL has prior adverse fills (live FIL bought then fell) and a large premium (143.6 bps), so be defensive; CAKE is calmer (fv_vol_bps=37.6) with supportive usdt_spread_bps=128.1 so I set h=1.0% to be more competitive. Portfolio: keep rial exposure at 1.0 (USDT/TMN 48h +4.45% and ch24 +3.09% justify staying fully in the rial-weakening regime) and keep beta at 0.8 (current scale_now=0.8, sleeves returning -0.79% but still in regime cap=1.0); beta assets remain PEPE/ADA/LINK as per the sleeve weights and universe.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
