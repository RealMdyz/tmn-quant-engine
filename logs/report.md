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

- Equity: **4,930,642 TMN** (-1.387%)
- Max drawdown: **3.650%**
- Traded volume: 564,491 TMN

![equity](equity_live.png)

- Market maker: **2 fills** (2 buys, 0 sells), 1 risk exits, realised PnL **-2,109 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| DOT | 1 | 0 | 0 | 0 |
| PENGU | 1 | 0 | 1 | -2,109 |

- AI supervisor decisions: 96 (sources: {'llm:boxapi': 96})
- Events: {'coin_skipped': 441, 'live_self_test': 63, 'cancel_all': 11, 'startup': 11, 'regime': 14, 'policy': 96, 'sleeve_order': 329, 'quote': 2892, 'buy_blocked': 6735, 'buy_unblocked': 6675, 'state_restored': 62, 'sleeve_fill': 30, 'orphan_adopted': 1, 'fill': 2, 'exit': 1, 'sleeve_reweight': 1}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 1.2,
    "BCH": 1.3,
    "GALA": 1.4
  },
  "pause": false,
  "reasoning": "I pick FIL, BCH and GALA because they have wide Toman spreads (FIL 188.4 bps, BCH 126.8 bps, GALA 124.7 bps) and reasonable 24h liquidity (FIL vol 3,932M TMN, BCH 2,133M, GALA 1,157M) with no buy-blocks. I avoid markets with active buy blocks or recent losing live fills (PENGU had a -2,109 TMN loss / avg -178 bps and is excluded; several others show Toman-book sliding). I set half-spreads h wider where fair-value volatility is higher: FIL h=1.2% (fv_vol 149.2 bps), BCH h=1.3% (fv_vol 259.3 bps) and GALA h=1.4% (fv_vol 338.9 bps) to protect against adverse selection. Sleeves are set to zero exposure (rial=0.0, beta=0.0) because USDT/TMN 48h only +0.71% -> regime cap 0.0 and historically sleeves lost when entered outside the rial-weakening regime; beta assets listed as PEPE and ADA (high-momentum names) in case scale is later allowed.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
