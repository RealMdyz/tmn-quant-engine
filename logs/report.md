# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 2 (sources: {'fallback': 1, 'llm:boxapi': 1})
- Events: {'startup': 3, 'policy': 2, 'quote': 11, 'state_restored': 2}

### Latest AI decision
```json
{
  "enabled_coins": [
    "LINK",
    "AVAX",
    "SOL",
    "PENGU",
    "BNB"
  ],
  "margin_mult": 1.15,
  "usdt_hold_frac": 0.05,
  "pause": false,
  "reasoning": "Equity is 5,000,000 TMN with USDT/TMN = 266,720 TMN (we'll keep 5% in USDT ≈ 250 USDT) to hedge rial moves; round-trip fees are 0.68% so I increase margins slightly. I enable coins that show Toman bids below liquidation (LINK -0.335%, AVAX -0.271%, SOL -0.252%, PENGU -0.189%, BNB -0.031%) where we have potential entry edge. I set margin_mult to 1.15 to demand ~15% more edge than learned margins given tail risks (suspended withdrawals/adverse selection) and zero recent fills across books; minutes to contest end = 2255 so we can run a measured strategy.",
  "tool_trace": [
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "LINK"
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
        "coin": "FIL"
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
        "coin": "UNI"
      }
    },
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
    }
  ],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
