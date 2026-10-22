# TMN Quant Engine — run report

## SHADOW

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- AI supervisor decisions: 21 (sources: {'fallback': 1, 'llm:boxapi': 20})
- Events: {'startup': 20, 'policy': 21, 'quote': 677, 'state_restored': 18, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 251, 'buy_unblocked': 189, 'instance_superseded': 9}

### Latest AI decision
```json
{
  "markets": {
    "BNB": 1.0,
    "ETH": 0.9,
    "SOL": 0.9,
    "SUI": 1.0,
    "XRP": 0.8
  },
  "pause": false,
  "reasoning": "I pick up to five busy, stable markets with no buy blocks: BNB (vol24h 60,821M TMN, very wide spread 86.6 bps and low fv_vol 27.9 => wide h=1.0). ETH (vol24h 76,607M, fv_vol 17.9 is low so relatively safer, spread 15.4 bps => h=0.9). SOL (vol24h 29,625M, spread 16.3 bps, fv_vol 32.0 => keep wide at h=0.9). SUI (spread 23.0 bps, premium 28.7 bps and fv_vol 36.6; smaller volume but attractive premium so cautious wide h=1.0). XRP (high volume 36,731M, low fv_vol 28.6 but narrow spread 8.5 bps so tighter h=0.8 to avoid excessive quoting cost). No market-wide shocks or frozen USDT books present for these, so pause=false.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
