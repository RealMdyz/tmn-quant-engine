# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 4 (sources: {'fallback': 1, 'llm:boxapi': 3})
- Events: {'startup': 4, 'policy': 4, 'quote': 41, 'state_restored': 3, 'quote_skipped': 4}

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
  "usdt_hold_frac": 0.08,
  "pause": false,
  "reasoning": "Keep all coins enabled: no coin shows the long-lived >-2% dislocation flag and there are zero losing fills (fills=0). Equity is 5,000,000 TMN with USDT/TMN spot 266,720; round-trip fees 0.68% are already accounted for so I keep margin_mult at 1.0. We hold a modest USDT buffer (8% of equity) to reflect recent rial pressure while staying within the 0–0.3 limit. No headline or market shock warrants pausing — open quotes exist on 5 coins and no realised PnL or drawdown to force defensive action.",
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
    },
    {
      "tool": "get_account_state",
      "args": {}
    }
  ],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
