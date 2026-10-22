# TMN Quant Engine — backtest report (corrected 2026-10-22)

The first version of this report showed +2.9% / +1.8% in 5 days with 80-90% win rates. Those numbers
were an artefact: the hedge was priced at stale coin/USDT candle closes (most 5-minute bars on the
Wallex USDT books have no trade). See RESEARCH.md §5 for the diagnosis.

## Diagnosis of the original fills (margin 0.8%, original model)

| original fills | n | avg net | win |
|---|---|---|---|
| all | 2400 | +36 bps | 81% |
| coin/USDT really traded in the hedge bar | 640 | **-78 bps** | 30% |
| no coin/USDT trade in the hedge bar (stale price) | 1760 | +78 bps | 99% |

After a fill, the next REAL coin/USDT trade was a median **-147 bps** below the fair value used to
place the bid (which itself sat -148 bps below it): the Toman dips were real price moves.

## Hedge at the next real coin/USDT trade (no guard, one fill per 15-min episode, 22 coins)

| margin | fills / 10 days | avg net | win |
|---|---|---|---|
| 0.4% | 1507 | -73 bps | 30% |
| 0.8% | 893 | -63 bps | 34% |
| 1.3% | 418 | -59 bps | 34% |
| 2.0% | 170 | -28 bps | 36% |
| 3.0% | 70 | +14 bps | 59% |

## Current model (`python run.py backtest --cached`): flash-dip guard + real-trade hedge, worst of close/low

`pooled_by_margin` = [margin %, mean net bps per fill, fills per coin per 10 days].

```json
{
  "data/m5_all.json": {
    "chosen_margins_from_train": {
      "ADA": 2.0
    },
    "test_days": 5.0,
    "test_fills": 0,
    "test_avg_net_bps_per_fill": null,
    "test_win_rate_pct": null,
    "test_return_pct": 0.0,
    "test_max_drawdown_pct": 0.0,
    "pooled_by_margin": [
      [
        1.3,
        -82.0,
        2.0
      ],
      [
        2.0,
        -105.2,
        0.75
      ],
      [
        3.0,
        16.2,
        0.5
      ]
    ],
    "assumptions": "flash-dip guard; trade-through fills; fill size <= 25% of the bar's Toman volume; hedge at the next REAL coin/USDT trade (worst of close/low); full taker fees on hedge"
  },
  "data/m5_extra.json": {
    "chosen_margins_from_train": {
      "FIL": 2.0,
      "SHIB": 1.3,
      "WLD": 1.3
    },
    "test_days": 5.0,
    "test_fills": 2,
    "test_avg_net_bps_per_fill": 176.9,
    "test_win_rate_pct": 100.0,
    "test_return_pct": 0.708,
    "test_max_drawdown_pct": 0.0,
    "pooled_by_margin": [
      [
        1.3,
        -49.6,
        3.6
      ],
      [
        2.0,
        -23.0,
        1.4
      ],
      [
        3.0,
        47.8,
        0.67
      ],
      [
        4.0,
        -69.0,
        0.2
      ]
    ],
    "assumptions": "flash-dip guard; trade-through fills; fill size <= 25% of the bar's Toman volume; hedge at the next REAL coin/USDT trade (worst of close/low); full taker fees on hedge"
  }
}
```

Conclusion: no margin shows a statistically reliable edge; only deep (~3%) flash dips are positive,
on ~12 fills in 10 days across 29 coins. The live engine therefore quotes only deep margins, only
while its guards pass, and the shadow test (trade-tape fill simulator) measures the real edge.
