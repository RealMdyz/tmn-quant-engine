# TMN Quant Engine — run report

## SHADOW

- Equity: **4,997,044 TMN** (-0.059%)
- Max drawdown: **0.441%**
- Traded volume: 3,977,145 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 27 (sources: {'fallback': 1, 'llm:boxapi': 26})
- Events: {'startup': 32, 'policy': 27, 'quote': 1195, 'state_restored': 30, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 590, 'buy_unblocked': 491, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 6}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 1.1,
    "SHIB": 0.9,
    "AVAX": 1.0,
    "ENA": 1.0,
    "WLD": 1.1
  },
  "pause": false,
  "reasoning": "I selected markets with Toman spreads comfortably above our 50 bps cutoff and reasonable 24h activity: SUI (spread 137.5 bps, vol 5,965M TMN) and WLD (spread 138.7 bps, vol 1,626M) merit the widest half-spread (h=1.1%) because of their very wide Toman spreads; AVAX and ENA (spreads 81.2 and 83.5 bps, vols 3,616M and 2,220M) get h=1.0% to respect elevated spreads while remaining competitive; SHIB (spread 58.6 bps, vol 5,184M) is narrower at h=0.9% because it is busy but closer to our minimum spread threshold. I avoided FIL despite high spread because our live round trips there lost (realised_pnl -10,984 TMN, avg round trip 3.5 bps), and I excluded low-spread/high-volume coins (e.g. BNB) since spread_bps <50.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
