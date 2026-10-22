# TMN Quant Engine — run report

## SHADOW

- Equity: **4,990,377 TMN** (-0.192%)
- Max drawdown: **0.441%**
- Traded volume: 3,977,145 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 28 (sources: {'fallback': 1, 'llm:boxapi': 27})
- Events: {'startup': 34, 'policy': 28, 'quote': 1226, 'state_restored': 32, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 650, 'buy_unblocked': 530, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 7, 'coin_skipped': 14, 'regime': 2, 'sleeve_order': 18, 'sleeve_order_failed': 5, 'sleeve_fill': 15}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 1.2,
    "UNI": 0.9,
    "CHZ": 1.0
  },
  "pause": false,
  "reasoning": "I pick SUI, UNI and CHZ (max 3). SUI has an enormous Toman spread 322.2 bps and reasonable 24h volume 6,380M TMN so I quote wide (h=1.2%) to avoid pick‑offs; it is already quoted_now. UNI has 65.8 bps spread, good USDT/TMN arbitrage buffer (usdt_spread 79.9 bps) and healthy volume 9,228M TMN so I set h=0.9% to be competitive. CHZ has 102.6 bps Toman spread and very large USDT spread (197.4 bps) so I quote wide at h=1.0% to prioritise safety. I avoid FIL (live round trips realised -10,984 TMN) and DOT (buy_blocked) as instructed. Portfolio: USDT/TMN 48h +3.45% gives full regime cap, so keep rial exposure 1.0 (rial sleeve scale_now=1.0) and keep beta at 1.0 to capture the rial-weakening upside; I select PEPE, ADA and LINK from the beta universe for momentum and liquidity.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
