# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 3 (sources: {'fallback': 1, 'llm:boxapi': 2})
- Events: {'startup': 3, 'policy': 3, 'quote': 19, 'state_restored': 2}

### Latest AI decision
```json
{
  "enabled_coins": [
    "LINK",
    "PENGU",
    "SOL",
    "BNB",
    "AVAX",
    "AAVE"
  ],
  "margin_mult": 1.15,
  "usdt_hold_frac": 0.08,
  "pause": false,
  "reasoning": "Equity is 5,000,000 TMN and we currently hold no USDT, while USDT/TMN is ~266,720 TMN — keep a small USDT reserve (8%) to absorb FX moves. Focus on coins showing negative Toman deviation: LINK -32.5%, PENGU -27.2%, SOL -22.3%, BNB -12.8%, AVAX -10.2% and AAVE -9.5% where our strategy historically finds buys below liquidation. Use a slightly conservative margin multiplier 1.15 (vs learned 1.0) because drawdown is penalised and structural dislocations are a real tail risk; round-trip fees are 0.68% so require extra edge. No pause — market shows no news-driven break but keep sizing/tight margins to limit adverse-selection risk.",
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
      "tool": "get_market_stats",
      "args": {
        "coin": "LINK"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "SOL"
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
        "coin": "BNB"
      }
    },
    {
      "tool": "get_market_stats",
      "args": {
        "coin": "AVAX"
      }
    }
  ],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
