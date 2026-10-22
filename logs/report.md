# TMN Quant Engine — run report

## SHADOW

- Equity: **4,989,206 TMN** (-0.216%)
- Max drawdown: **0.445%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 30 (sources: {'fallback': 1, 'llm:boxapi': 29})
- Events: {'startup': 39, 'policy': 30, 'quote': 1254, 'state_restored': 36, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 816, 'buy_unblocked': 663, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 7, 'coin_skipped': 49, 'regime': 7, 'sleeve_order': 54, 'sleeve_order_failed': 5, 'sleeve_fill': 22, 'state_reset': 1}

### Latest AI decision
```json
{
  "markets": {
    "ARB": 1.3,
    "SUI": 1.1,
    "FIL": 1.2
  },
  "pause": false,
  "reasoning": "Select ARB because it has a very wide Toman spread (167.3 bps) and high 24h volume (35,059M TMN) with a positive premium (+20.6 bps), so we can sit wide (h=1.3%). Add SUI: spread 90.8 bps and decent volume (6,539M TMN) so a conservative h=1.1% fits its profile. Include FIL because its Toman spread is >50 bps (52.2 bps) and premium is large (+174.9 bps) with moderate volume (5,787M TMN), so h=1.2% balances pickoff risk and earning spread. Do not quote broken books (HYPE/IMX flagged) and avoid low-spread pairs (XRP/SOL). Keep sleeves fully in the rial regime (rial exposure 1.0 because USDT/TMN 48h +4.28% and regime cap=1.0) and nearly-full beta (0.9) to capture the rial-weakening lift while trimming some beta risk; beta assets = PEPE/ADA/LINK per portfolio weights and momentum.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
