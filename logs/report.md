# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 17 (sources: {'fallback': 1, 'llm:boxapi': 16})
- Events: {'startup': 9, 'policy': 17, 'quote': 317, 'state_restored': 7, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 317, 'quote_unblocked': 304, 'error': 5}

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
  "reasoning": "USDT trend data returned only a spot price (270,987 TMN) with no 6h/24h change, so we do not enable a USDT directional position (usdt_hold_frac=0). SHIB is disabled because its USDT reference has been stale for 21 minutes (note message) making liquidation-based quoting unsafe; its current dev_now_bps is 110.0. Other coins show short-lived 'Toman book sliding' guards (PENGU, APE, BNB) but no persistent long deviation or fills, so keep them enabled. No market-wide news indicating a rial strengthening or systemic shock, so do not pause and keep margin_mult at 1.0.",
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
