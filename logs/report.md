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

- Equity: **4,928,965 TMN** (-1.421%)
- Max drawdown: **3.650%**
- Traded volume: 890,411 TMN

![equity](equity_live.png)

- Market maker: **2 fills** (2 buys, 0 sells), 2 risk exits, realised PnL **-4,601 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| DOT | 1 | 0 | 1 | -2,492 |
| PENGU | 1 | 0 | 1 | -2,109 |

- AI supervisor decisions: 145 (sources: {'llm:boxapi': 145})
- Events: {'coin_skipped': 441, 'live_self_test': 63, 'cancel_all': 11, 'startup': 11, 'regime': 14, 'policy': 145, 'sleeve_order': 329, 'quote': 4280, 'buy_blocked': 10472, 'buy_unblocked': 10412, 'state_restored': 62, 'sleeve_fill': 30, 'orphan_adopted': 1, 'fill': 2, 'exit': 2, 'sleeve_reweight': 2, 'sleeve_stop': 2}

### Latest AI decision
```json
{
  "markets": {
    "CAKE": 1.0,
    "GALA": 1.4,
    "CHZ": 1.2
  },
  "pause": false,
  "reasoning": "I pick CAKE, GALA and CHZ because I never bid where Toman spread <80 bps — CAKE spread 96.6 bps (vol24h 3,325M TMN), GALA spread 152.8 bps (vol24h 2,366M) and CHZ spread 193.2 bps (quoted_now) pass the threshold. I avoid DOT and PENGU because DOT has a recent live round-trip loss (avg_round_trip_bps -76.1 and buy blocked) and PENGU has a very negative avg_round_trip_bps (-178.3), so both are high adverse-selection risk. I set half-spreads wide where either FV volatility or adverse selection risk is high: GALA h=1.4% (fv_vol_bps 1,210), CHZ h=1.2% (very large spread 193 bps but tiny vol so conservative), CAKE h=1.0% (spread 96.6 bps, fv_vol_bps 269 — calmer so slightly narrower). Sleeves are set to 0.0 because the portfolio regime cap is 0.0 (USDT/TMN 48h -1.17% → exposure cap 0.0) and both sleeves are currently stopped (rial stop-loss -5.36%, beta stopped -7.53%), so we must not add exposure now.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
