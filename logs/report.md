# TMN Quant Engine — run report

## SHADOW

- Equity: **4,983,557 TMN** (-0.329%)
- Max drawdown: **0.445%**
- Traded volume: 3,977,145 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 29 (sources: {'fallback': 1, 'llm:boxapi': 28})
- Events: {'startup': 37, 'policy': 29, 'quote': 1245, 'state_restored': 35, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 762, 'buy_unblocked': 625, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 7, 'coin_skipped': 35, 'regime': 5, 'sleeve_order': 40, 'sleeve_order_failed': 5, 'sleeve_fill': 19}

### Latest AI decision
```json
{
  "markets": {
    "BCH": 1.0,
    "ENA": 1.1,
    "WLD": 1.0
  },
  "pause": false,
  "reasoning": "I pick BCH/ENA/WLD because they have spreads >50 bps (BCH 52.8, ENA 64.2, WLD 67.7) while higher-liquidity names are either <50 bps or have buy-blocks or frozen USDT books. I avoid FIL despite its wide Toman spread (90.8 bps) because our live round trips there lost -10,984 TMN (avg RT 3.5 bps) — that signals adverse selection. I set half-spreads wide (h=1.0–1.1%) because fv_vol is elevated (BCH 102.5, ENA 233.8, WLD 126.4 bps) and the backtest shows losses with narrow quotes; wider quoting reduces pick-off risk. Sleeves: USDT/TMN is +3.47% over 48h so the rial-weakening regime allows full rial exposure (1.0) given sleeve performance (rial return -0.03% recently but regime supportive). I keep beta scaled back to 0.8 (not full 1.0) to limit drawdown after recent beta PnL -12,024 TMN while selecting ADA/PEPE/LINK (high momentum names in the beta universe) and no coin-specific bad headlines.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

_No records yet._
