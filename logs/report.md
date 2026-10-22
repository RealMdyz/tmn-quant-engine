# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 8 (sources: {'fallback': 1, 'llm:boxapi': 7})
- Events: {'startup': 5, 'policy': 8, 'quote': 103, 'state_restored': 4, 'quote_skipped': 4}

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
  "reasoning": "Keep the default setup for all coins except APE which shows a massive persistent Toman dislocation (dev_now_pct 2664.226, mean 1969.512 over 595 samples) consistent with structural mismatch. No coin shows minutes_below_-2pct indicating a deposits/withdrawal halt except WLD at 0.1 min which is negligible. Bandit post-fill stats look healthy for our existing margins on the remaining universe, so keep margin_mult=1. I recommend holding 5% of equity in USDT (usdt_hold_frac=0.05) as a small hedge against further rial moves; do not pause quoting.",
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
        "coin": "CAKE"
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
        "coin": "PENGU"
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
        "coin": "BNB"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "WLD"
      }
    }
  ],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
