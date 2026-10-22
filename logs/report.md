# TMN Quant Engine — run report

## SHADOW

- Equity: **4,995,848 TMN** (-0.083%)
- Max drawdown: **0.441%**
- Traded volume: 3,977,145 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 25 (sources: {'fallback': 1, 'llm:boxapi': 24})
- Events: {'startup': 30, 'policy': 25, 'quote': 1070, 'state_restored': 28, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 510, 'buy_unblocked': 420, 'instance_superseded': 17, 'fill': 4, 'exit': 1}

### Latest AI decision
```json
{
  "markets": {
    "BNB": 0.3,
    "AAVE": 0.25,
    "FIL": 0.6,
    "CHZ": 0.6,
    "SUI": 0.5
  },
  "pause": false,
  "reasoning": "Keep BNB (spread 53.5 bps, vol 74,277M TMN) with tight h=0.3 to sit at top of the book and monetize its high volume; fv_vol 92.4 bps is moderate. Include AAVE (spread 55.2 bps, vol 2,833M) with h=0.25 because fv_vol is low (15.2 bps) so narrow quoting is safe. Add FIL (spread 88.6 bps, vol 4,878M) with wider h=0.6 because spread is large but fv_vol is elevated (112.7 bps) so we need protection. Add CHZ (spread 83.1 bps, vol 1,667M) with h=0.6 for similar reasons (spread high but fv_vol ~98 bps). Add SUI (spread 56.1 bps, vol 6,016M) with h=0.5: spread covers fees and volume is reasonable but fv_vol 88 bps suggests a moderate cushion. Avoid markets flagged buy_blocked or with recent FV slides.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
