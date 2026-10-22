# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 7 (sources: {'fallback': 1, 'llm:boxapi': 6})
- Events: {'startup': 5, 'policy': 7, 'quote': 95, 'state_restored': 4, 'quote_skipped': 4}

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
  "usdt_hold_frac": 0.05,
  "pause": false,
  "reasoning": "APE shows a massive dev_now_pct = 2672.57% (sample mean same) and poor bandit post-fill stats at tight margins (e.g. -28.6 bps), indicating a structural dislocation likely from halted flows — disabling it. All other coins have small deviations (LINK -1.02%, SHIB -0.44%, etc.) and zero live fills, so keep default margins (margin_mult=1.0). Keep a small USDT buffer (5% of equity) given USDT/TMN ~268,891 Toman and recent currency volatility; no market-wide pause — headlines show macro news but no immediate crypto market halt.",
  "tool_trace": [
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "APE"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "LINK"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "SHIB"
      }
    },
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
