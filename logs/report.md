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

- Equity: **4,986,561 TMN** (-0.269%)
- Max drawdown: **2.501%**
- Traded volume: 118,429 TMN

![equity](equity_live.png)

- Market maker: **1 fills** (1 buys, 0 sells), 0 risk exits, realised PnL **0 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| PENGU | 1 | 0 | 0 | 0 |

- AI supervisor decisions: 77 (sources: {'llm:boxapi': 77})
- Events: {'coin_skipped': 441, 'live_self_test': 63, 'cancel_all': 11, 'startup': 11, 'regime': 11, 'policy': 77, 'sleeve_order': 171, 'quote': 2269, 'buy_blocked': 5514, 'buy_unblocked': 5451, 'state_restored': 62, 'sleeve_fill': 10, 'orphan_adopted': 1, 'fill': 1}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 1.4,
    "FIL": 0.9,
    "CAKE": 1.4
  },
  "pause": false,
  "reasoning": "Pick SUI (spread 119.3 bps, vol24h 3,887M TMN, fv_vol 27.1 bps, quoted_now true) because spread >>80 bps and fair-value volatility is moderate; use wide half-spread h=1.4% to avoid pick-off. Pick FIL (spread 124.1 bps, vol24h 4,487M TMN, fv_vol 7.1 bps) because volume is decent and fv_vol is very low (stable), so a tighter h=0.9% is acceptable while still covering maker fees. Pick CAKE (spread 156.6 bps, vol24h 2,958M TMN, fv_vol 94.9 bps) as a wide, liquid candidate but with high fv volatility so keep h=1.4%. Avoid markets with buy_blocked flags (S, AVAX, ARB, UNI, etc.) and avoid DOT despite huge spread because the book is reported broken. Sleeves: keep rial at full cap 1.0 since USDT/TMN 48h +1.18% (regime cap 1.0) and rial sleeve return is -0.96% but the rial-weakening regime supports holding; keep beta at current scale 0.8 because beta return is +1.36% (pnl 30,410 TMN) and profit-saving/wind-down rules are active but not forcing further reductions.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
