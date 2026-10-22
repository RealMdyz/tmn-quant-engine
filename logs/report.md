# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 20 (sources: {'fallback': 1, 'llm:boxapi': 19})
- Events: {'startup': 20, 'policy': 20, 'quote': 616, 'state_restored': 18, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 170, 'buy_unblocked': 114, 'instance_superseded': 9}

### Latest AI decision
```json
{
  "markets": {
    "BNB": 0.6,
    "SOL": 0.9,
    "ETH": 0.6,
    "XRP": 0.8,
    "SUI": 1.0
  },
  "pause": false,
  "reasoning": "Select up to 5 liquid, stable markets while staying wide: BNB has very high volume (60,821M TMN), a healthy Toman spread (31.1 bps) and very low FV volatility (fv_vol 2.0 bps) so use a conservative narrow half-spread 0.6% to capture flow. ETH is the deepest (76,607M TMN) with low fv_vol 4.4 bps and moderate spread 21.5 bps, so 0.6% to be selective. SOL has strong volume (29,625M TMN), wide spread 34.3 bps but higher fv_vol (13.0 bps) so widen to 0.9% to reduce adverse selection. XRP is very active (36,731M TMN), spread 24.0 bps and fv_vol 9.5 bps so use 0.8%. SUI offers a large Toman spread (80.9 bps) and reasonable fv_vol 7.3 bps but lower vol (5,360M TMN), so keep widest protection at 1.0% to avoid fills before adverse moves. Avoid markets with buy blocks or rapidly sliding Toman books (e.g., LTC, DOT, IMX, PENGU) as flagged.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
