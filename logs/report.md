# TMN Quant Engine — run report

## SHADOW

- Equity: **4,977,083 TMN** (-0.458%)
- Max drawdown: **0.668%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 31 (sources: {'fallback': 1, 'llm:boxapi': 30})
- Events: {'startup': 41, 'policy': 31, 'quote': 1281, 'state_restored': 38, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 909, 'buy_unblocked': 736, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 7, 'coin_skipped': 63, 'regime': 9, 'sleeve_order': 56, 'sleeve_order_failed': 5, 'sleeve_fill': 26, 'state_reset': 1}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 0.9,
    "AVAX": 1.1,
    "GALA": 1.3
  },
  "pause": false,
  "reasoning": "Selected FIL because its Toman spread is 52.2 bps (above our 50 bps floor), very low FV volatility (fv_vol_bps 7.9) and a large premium (+169.2 bps) — so set a relatively tight half-spread h=0.9% to capture flow. Selected AVAX for its very wide Toman spread (169.1 bps), moderate fv_vol (48.9 bps) and decent 24h volume (3.2k M TMN) — set h=1.1% to be conservative against adverse selection. Selected GALA because spread is wide (99.4 bps) with good volume (2.3k M TMN) but higher fv volatility (296.5 bps) so use h=1.3% to avoid being picked off. No market-wide pause: no Iran/USDT shock or major crypto crash flagged. Sleeves: keep the rial sleeve at full exposure 1.0 because USDT/TMN 48h is +4.28% (regime cap=1.0) and the rial sleeve is already scaled_now=1.0; reduce beta to 0.8 (from scale_now 0.9) because beta has lost -1.25% and is higher-risk despite the favorable USDT/TMN regime — retain the three existing beta assets (PEPE, ADA, LINK) for momentum and simplicity.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
