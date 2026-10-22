# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 6 (sources: {'fallback': 1, 'llm:boxapi': 5})
- Events: {'startup': 5, 'policy': 6, 'quote': 73, 'state_restored': 4, 'quote_skipped': 4}

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
  "usdt_hold_frac": 0.05,
  "pause": false,
  "reasoning": "Keep all coins enabled: none shows prolonged deviation or deposit/halt signals (minutes_below_-2pct = 0 for every coin). No coin has negative realised fill performance (live_fills = 0 and avg_fill_bps null for all). Macro/news check shows no rial or exchange-breaking headlines; USDT/TMN is 266,720 and account equity is 5,000,000 TMN, so hold a small USDT buffer (5%) as a directional hedge. Use the learned margins (margin_mult = 1.0) and do not pause quoting.",
  "tool_trace": [
    {
      "tool": "get_account_state",
      "args": {}
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
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "FIL"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "PENGU"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "AAVE"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "GALA"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "ADA"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "TRX"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "CAKE"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "AVAX"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "WLD"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "APE"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "HYPE"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "SHIB"
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
        "coin": "DOGE"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "UNI"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "PUMP"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "BNB"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "SOL"
      }
    }
  ],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
