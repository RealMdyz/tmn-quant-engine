# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 19 (sources: {'fallback': 1, 'llm:boxapi': 18})
- Events: {'startup': 16, 'policy': 19, 'quote': 537, 'state_restored': 14, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 99, 'buy_unblocked': 58, 'instance_superseded': 6}

### Latest AI decision
```json
{
  "markets": {
    "SOL": 1.2,
    "BNB": 1.0,
    "S": 1.3,
    "SUI": 0.9,
    "ARB": 1.1
  },
  "pause": false,
  "reasoning": "Select up to five liquid markets with wide Toman spreads and stable FV: SOL (vol24h 29,651M TMN, spread 35.3 bps, fv_vol 24.8 bps) gets a conservative half-spread h=1.2% because volume is high but FV volatility is moderate. BNB (vol24h 58,071M, spread 31.1 bps, fv_vol 17.5 bps) is very busy and relatively stable so h=1.0% to be competitive. S (vol24h 12,987M, spread 63.5 bps, fv_vol 21.2 bps) has a large Toman spread so we set h=1.3% to protect against adverse selection. SUI (vol24h 7,402M, spread 105.9 bps, fv_vol 1.9 bps) has the widest spread and very low FV volatility so we quote tighter with h=0.9%. ARB (vol24h 34,203M, spread 25.5 bps, fv_vol 27.7 bps) is liquid but slightly more volatile so h=1.1% to balance spread capture and adverse-selection risk.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
