# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 18 (sources: {'fallback': 1, 'llm:boxapi': 17})
- Events: {'startup': 16, 'policy': 18, 'quote': 514, 'state_restored': 14, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 72, 'buy_unblocked': 37, 'instance_superseded': 6}

### Latest AI decision
```json
{
  "markets": {
    "ARB": 2.0,
    "S": 1.9,
    "SOL": 1.5,
    "ETH": 1.2,
    "DOGE": 1.3
  },
  "pause": false,
  "reasoning": "Select markets with large Toman spreads and decent activity while avoiding any with buy guards or bad live fills (none reported). ARB has a wide spread (57.6 bps) and high volume (33,981M TMN) so I use a wide half‑spread 2.0% to protect vs adverse selection. S shows an especially wide spread (87.9 bps) and solid volume (12,907M TMN) so I set h=1.9% to capture the premium (premium 37.6 bps) while being cautious. SOL (spread 30.4 bps, vol 29,639M TMN) and DOGE (15.8 bps, vol 41,479M TMN) are active — I use medium h of 1.5% and 1.3% respectively. ETH is the busiest (76,934M TMN) with a moderate spread (15.7 bps) and calm premium (-4.5 bps), so I place a tighter h=1.2% to try to earn safe round trips while keeping fees/adverse selection in mind.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
