# TMN Quant Engine — run report

## SHADOW

- Equity: **4,997,136 TMN** (-0.057%)
- Max drawdown: **0.441%**
- Traded volume: 3,977,145 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 26 (sources: {'fallback': 1, 'llm:boxapi': 25})
- Events: {'startup': 30, 'policy': 26, 'quote': 1151, 'state_restored': 28, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 530, 'buy_unblocked': 437, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 5}

### Latest AI decision
```json
{
  "markets": {
    "UNI": 0.3,
    "AVAX": 0.3,
    "ENA": 0.8,
    "APE": 0.25,
    "BNB": 0.35
  },
  "pause": false,
  "reasoning": "Pick UNI (spread 72.1 bps, vol24h 8.9k MTMN, fv_vol 49.8) and AVAX (spread 83.0 bps, vol 3.6k, fv_vol 40.5) because wide Toman spreads well above the 50 bps fee hurdle and low FV volatility — use tight h=0.3 to sit near top of book. Keep APE (spread 50.4 bps, vol 6.5k, fv_vol 36.4) with a narrow h=0.25 to compete at the NBBO. ENA has a large spread (70.4 bps) but high FV volatility (fv_vol 339.6) so use wide h=0.8 to protect vs adverse selection. Include BNB (huge volume 76.3k MTMN, spread 45.4 bps, fv_vol 139.7) with h=0.35 because its deep liquidity and our existing BNB inventory (≈899k TMN) justify active quoting despite spread slightly under 50 bps; avoid markets with buy_blocked or recent losses (FIL: buy_blocked and realised PnL -10,984 TMN).",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
