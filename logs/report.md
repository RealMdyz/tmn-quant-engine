# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 22 (sources: {'fallback': 1, 'llm:boxapi': 21})
- Events: {'startup': 25, 'policy': 22, 'quote': 699, 'state_restored': 23, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 276, 'buy_unblocked': 207, 'instance_superseded': 13}

### Latest AI decision
```json
{
  "markets": {
    "ETH": 0.6,
    "XRP": 0.6,
    "SOL": 0.7,
    "DOGE": 0.9
  },
  "pause": false,
  "reasoning": "Select 4 markets that are liquid and have stable FV: ETH (vol24h 75,194M TMN, spread 27.2 bps, fv_vol 21.9 bps) and XRP (35,781M, spread 28.1 bps, fv_vol 31.4 bps) are top liquidity with low fv volatility so we quote tighter at h=0.6%. SOL (vol24h 28,740M, spread 21.0 bps, fv_vol 58.6 bps) is moderately volatile so we widen to h=0.7%. DOGE (vol24h 42,271M, spread 21.9 bps) has high fv volatility (259.7 bps) so we use a conservative wide h=0.9%. We avoid any markets with Toman-book sliding / buy_blocked (e.g. BNB, SUI, ARB) and avoid markets with frozen USDT books; no pause because no market-wide shock is present.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
