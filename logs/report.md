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

- Equity: **4,931,604 TMN** (-1.368%)
- Max drawdown: **3.650%**
- Traded volume: 564,491 TMN

![equity](equity_live.png)

- Market maker: **2 fills** (2 buys, 0 sells), 1 risk exits, realised PnL **-2,109 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| DOT | 1 | 0 | 0 | 0 |
| PENGU | 1 | 0 | 1 | -2,109 |

- AI supervisor decisions: 97 (sources: {'llm:boxapi': 97})
- Events: {'coin_skipped': 441, 'live_self_test': 63, 'cancel_all': 11, 'startup': 11, 'regime': 14, 'policy': 97, 'sleeve_order': 329, 'quote': 2953, 'buy_blocked': 6858, 'buy_unblocked': 6795, 'state_restored': 62, 'sleeve_fill': 30, 'orphan_adopted': 1, 'fill': 2, 'exit': 1, 'sleeve_reweight': 1}

### Latest AI decision
```json
{
  "markets": {
    "CAKE": 0.9,
    "FIL": 1.4,
    "GALA": 1.1
  },
  "pause": false,
  "reasoning": "I pick CAKE (spread_bps 102.5, vol24h_mtmn 2964, fv_vol_bps 34.0) as a calm, wide-Toman-spread market and quote fairly tight at h=0.9. I include FIL because its Toman spread is very wide (193.7 bps) and USDT spread 232.2 bps, but FIL has adverse-selection history so I set a wide h=1.4. GALA (spread_bps 124.0, quoted_now true, vol24h_mtmn 1157) is attractive for capture of large spread with medium fv_vol_bps 244.5 so I use h=1.1. I avoid markets with buy blocks or frozen USDT book (DOT, SUI, S, AVAX, PENGU, etc.) and I do not quote where spread_bps <80 (e.g. SOL, XRP, UNI). Portfolio sleeves are set to zero (rial=0.0, beta=0.0) because the USDT/TMN regime shows ch48 +0.71% with cap 0.0 so the regime disallows scaling and the engine is in end_wind_down; beta_assets listed (PEPE, ADA, LINK) follow the sleeve universe and current weight priorities.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
