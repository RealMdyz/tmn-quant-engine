# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 5 (sources: {'fallback': 1, 'llm:boxapi': 4})
- Events: {'startup': 4, 'policy': 5, 'quote': 57, 'state_restored': 3, 'quote_skipped': 4}

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
  "reasoning": "Equity is 5,000,000 TMN with no USDT on hand and zero realised PnL or fills, so keep the preselected universe (no coin shows multiple losing fills). Current deviations are small (range approx -0.891% LINK to +1.114% FIL) and every coin has fills=0 in the snapshot, so no minutes_below_-2% signal of a sustained dislocation. Open quotes exist for AVAX, CAKE, FIL, AAVE, GALA, PENGU, TRX, ADA with margins already set — keep learned margins (margin_mult=1.0) and hold a small USDT buffer (5% of equity) given recent rial volatility. Not pausing: no market-wide news triggered and drawdown is zero.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
