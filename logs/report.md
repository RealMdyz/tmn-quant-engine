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

- Equity: **4,930,710 TMN** (-1.386%)
- Max drawdown: **3.650%**
- Traded volume: 890,411 TMN

![equity](equity_live.png)

- Market maker: **2 fills** (2 buys, 0 sells), 2 risk exits, realised PnL **-4,601 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| DOT | 1 | 0 | 1 | -2,492 |
| PENGU | 1 | 0 | 1 | -2,109 |

- AI supervisor decisions: 112 (sources: {'llm:boxapi': 112})
- Events: {'coin_skipped': 441, 'live_self_test': 63, 'cancel_all': 11, 'startup': 11, 'regime': 14, 'policy': 112, 'sleeve_order': 329, 'quote': 3432, 'buy_blocked': 7715, 'buy_unblocked': 7654, 'state_restored': 62, 'sleeve_fill': 30, 'orphan_adopted': 1, 'fill': 2, 'exit': 2, 'sleeve_reweight': 2}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 1.4,
    "IMX": 1.5,
    "CHZ": 0.9
  },
  "pause": false,
  "reasoning": "I pick FIL, IMX and CHZ because they are the only candidates with Toman spreads >=80 bps (FIL 167 bps, IMX 263.4 bps, CHZ 82.1 bps). FIL has healthy volume (3,970M TMN), wide USDT/TMN spread (305 bps) and moderate FV vol (75 bps) so I quote wide (h=1.4%). IMX offers the largest spread but very high FV volatility (fv_vol_bps 1004.7) so I set the widest h=1.5% to avoid adverse selection. CHZ is extremely stable (fv_vol_bps 1.4) with huge USDT spread (464 bps) but low volume, so I quote tighter (h=0.9%) to be competitive while keeping protection. I avoid DOT and PENGU because live round trips lost money (DOT realised -2,492 TMN, avg -76.1 bps; PENGU realised -2,109 TMN, avg -178.3 bps). Sleeves are set to 0.0 exposure because the USDT/TMN regime shows ch48 +0.71% and the regime cap = 0.0, so no sleeve exposure now; beta_assets listed are PEPE/ADA/LINK (default high-momentum picks).",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
