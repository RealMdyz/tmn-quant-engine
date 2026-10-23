# TMN Quant Engine — run report

## SHADOW

- Equity: **4,964,229 TMN** (-0.715%)
- Max drawdown: **0.866%**
- Traded volume: 0 TMN

![equity](equity_shadow.png)

- Market maker: **4 fills** (3 buys, 1 sells), 1 risk exits, realised PnL **-10,984 TMN**, maker round trips avg 226.7 bps

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| BNB | 1 | 0 | 0 | 0 |
| FIL | 2 | 1 | 1 | -10,984 |

- AI supervisor decisions: 33 (sources: {'fallback': 1, 'llm:boxapi': 32})
- Events: {'startup': 41, 'policy': 33, 'quote': 1318, 'state_restored': 38, 'quote_skipped': 4, 'usdt_ref_check': 13, 'quote_blocked': 321, 'quote_unblocked': 306, 'error': 5, 'buy_blocked': 1081, 'buy_unblocked': 909, 'instance_superseded': 17, 'fill': 4, 'exit': 1, 'quote_failed': 7, 'coin_skipped': 63, 'regime': 9, 'sleeve_order': 56, 'sleeve_order_failed': 5, 'sleeve_fill': 26, 'state_reset': 1}

### Latest AI decision
```json
{
  "markets": {
    "GALA": 1.0,
    "CHZ": 0.9,
    "DOT": 1.5
  },
  "pause": false,
  "reasoning": "I pick GALA and CHZ because both have Toman spreads above our 80 bps threshold (GALA 100.0 bps, CHZ 83.4 bps) and reasonable 24h TMN volumes (GALA 2,307m, CHZ 1,729m); GALA's fv_vol is moderate (224 bps) so h=1.0% is appropriate, CHZ's fv_vol is low (59 bps) so h=0.9% to quote more aggressively. I include DOT as a third slot because its Toman spread is very wide (137.7 bps) albeit with extreme fv volatility (2,306 bps), so I set h=1.5% to protect against adverse selection. I avoid ARB (buy_blocked: book sliding) and other sub-80-bps markets (e.g. SOL 38 bps, XRP 29.3 bps). For sleeves, USDT/TMN 48h +4.06% keeps us in the rial-weakening regime, so keep rial exposure at 1.0 (full); beta stays at the engine's current scale 0.8 and I keep the beta assets to PEPE/ADA/LINK (the current beta weights) to capture momentum while respecting the sleeve's stop and the end_wind_down schedule.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```

## LIVE

- Equity: **5,035,268 TMN** (+0.705%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 69 (sources: {'llm:boxapi': 69})
- Events: {'coin_skipped': 427, 'live_self_test': 61, 'cancel_all': 9, 'startup': 9, 'regime': 9, 'policy': 69, 'sleeve_order': 171, 'quote': 1965, 'buy_blocked': 4875, 'buy_unblocked': 4823, 'state_restored': 60, 'sleeve_fill': 10, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "CAKE": 0.9
  },
  "pause": false,
  "reasoning": "Only CAKE meets the bot's minimum Toman spread rule (spread_bps 102.7 >= 80) while having low fair-value volatility (fv_vol_bps 54.3) and no buy_blocked flags; vol24h_mtmn is 1026 so liquidity is adequate. I set h=0.9% (near the narrow end) because the Toman spread is wide (102.7 bps) and FV is calm, allowing a tighter quote without excessive adverse selection. Other large spreads (DOT 768.7, PENGU 258.4, CHZ 203.3, FIL 99.9) are excluded because of buy_blocked/fair-value shocks or sliding Toman-book signals. Keep the rial sleeve at full exposure 1.0 because USDT/TMN 48h +3.08% (regime cap 1.0) supports holding rial (rial sleeve currently scale 1.0); keep beta at 0.8 (current scale) because beta has positive return 2.77% and we avoid increasing exposure before the scheduled wind-down.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
