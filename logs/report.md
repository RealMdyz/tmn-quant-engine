# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 13 (sources: {'fallback': 1, 'llm:boxapi': 12})
- Events: {'startup': 7, 'policy': 13, 'quote': 210, 'state_restored': 6, 'quote_skipped': 4, 'usdt_ref_check': 6, 'quote_blocked': 122, 'quote_unblocked': 115, 'error': 3}

### Latest AI decision
```json
{
  "enabled_coins": [
    "FIL",
    "PENGU",
    "AAVE",
    "GALA",
    "ADA",
    "TRX",
    "CAKE",
    "AVAX",
    "WLD",
    "APE",
    "HYPE",
    "SHIB",
    "LINK",
    "DOGE",
    "UNI",
    "PUMP",
    "BNB",
    "SOL"
  ],
  "margin_mult": 1.0,
  "usdt_hold_frac": 0.0,
  "pause": false,
  "reasoning": "No concrete disable triggers: all coins have 0 fills and no coin shows persistent >200 bps negative displacement (LINK is -86.2 bps which is within normal noise). USDT trend data is unavailable (USDT/TMN = 270,147; change_6h and change_24h null), so per rule we must keep usdt_hold_frac = 0. Market-wide headlines show no rial-strongening intervention; round-trip fees ~68 bps, equity TMN 5,000,000 and 2084 minutes remaining — keep default margins (margin_mult 1.0) and do not pause.",
  "tool_trace": [
    {
      "tool": "get_usdt_tmn_trend",
      "args": {}
    },
    {
      "tool": "get_news",
      "args": {
        "topic": "iran"
      }
    }
  ],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
