# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 9 (sources: {'fallback': 1, 'llm:boxapi': 8})
- Events: {'startup': 5, 'policy': 9, 'quote': 127, 'state_restored': 4, 'quote_skipped': 4}

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
  "reasoning": "Keep the portfolio running with learned margins (margin_mult=1.0). I disabled only APE because its dev_mean_pct is 1720.58% (dev_std 1301.19%) and bandit post_mean_bps are strongly negative at small margins, a clear sign of structural dislocation. USDT/TMN is 270,368 so I allow a small USDT buffer (5% of equity) given recent rial moves but avoid larger exposure. No market‑wide headline or minutes_below_-2pct metrics justify pausing or disabling other coins.",
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
        "topic": "all"
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
