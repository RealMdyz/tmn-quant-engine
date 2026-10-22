# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 14 (sources: {'fallback': 1, 'llm:boxapi': 13})
- Events: {'startup': 7, 'policy': 14, 'quote': 219, 'state_restored': 6, 'quote_skipped': 4, 'usdt_ref_check': 7, 'quote_blocked': 144, 'quote_unblocked': 129, 'error': 3}

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
  "reasoning": "USDT trend data are unavailable (change_6h_pct and change_24h_pct are null) so the rule requires usdt_hold_frac = 0; USDT/TMN ref is 270,812 but no positive short-term trend. Account equity is 5,000,000 TMN with 0 USDT; minutes to end 2,064. Several coins are currently blocked by the sliding- Toman-book guard (e.g. WLD dev -44.6 bps with sliding -131 bps vs -26 bps baseline; AAVE dev -31.6 bps sliding -108 bps), which are temporary safety blocks — no persistent deposit/withdrawal or realised-loss signal, so keep all coins enabled. No market-wide news indicating a rial-strengthening intervention; keep margin_mult at 1.0 and do not pause quoting.",
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
