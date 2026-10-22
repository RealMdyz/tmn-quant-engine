# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 23 (sources: {'fallback': 1, 'llm:boxapi': 22})
- Events: {'startup': 25, 'policy': 23, 'quote': 823, 'state_restored': 23, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 337, 'buy_unblocked': 259, 'instance_superseded': 13}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 0.3,
    "LINK": 0.3,
    "AVAX": 0.3,
    "UNI": 0.5,
    "AAVE": 0.25
  },
  "pause": false,
  "reasoning": "Select up to 5 markets with wide Toman spreads and reasonable volume while avoiding books flagged as sliding. FIL (spread 90.8 bps, vol 4,881M TMN, fv_vol 11.1 bps) looks prime so quote tight at h=0.3% to sit near top of book. LINK (71.7 bps, vol 3,269M, fv_vol 14.1) and AVAX (72.8 bps, vol 3,651M, fv_vol 11.6) also show healthy spread and low FV volatility -> h=0.3%. UNI (67.2 bps, vol 8,528M, fv_vol 81.9) is liquid but more FV movement, widen to h=0.5%. AAVE (50.3 bps, vol 2,827M, fv_vol 9.6) has just-above-fee spread and very low fv_vol so we quote more aggressively at h=0.25%. I avoid any markets with buy_blocked flags (e.g. ARB, DOT, PENGU, ENA, IMX, CHZ) and avoid very tight-spread or high FV-volatility coins (e.g. ETH/XRP/DOGE/SOL with spreads <45 bps or extreme fv_vol) to reduce adverse selection.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
