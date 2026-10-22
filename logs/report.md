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

- Equity: **4,959,378 TMN** (-0.812%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 17 (sources: {'llm:boxapi': 17})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 17, 'sleeve_order': 131, 'quote': 169, 'buy_blocked': 1294, 'buy_unblocked': 1259, 'state_restored': 57, 'sleeve_fill': 6, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 1.4,
    "GALA": 1.35
  },
  "pause": false,
  "reasoning": "I pick FIL and GALA because the bot never quotes where Toman spread <80 bps and these two clear that threshold: FIL spread 93.2 bps with decent liquidity (vol24h 4,932M TMN) and USDT spread 79 bps; GALA spread 80.3 bps with USDT spread 393 bps and premium 71.6 bps. Both show elevated fv_vol (FIL fv_vol_bps 278, GALA fv_vol_bps 315) so I set wide half-spreads to control adverse selection (h=1.4% for FIL, 1.35% for GALA). I avoid IMX and DOT because IMX's Toman book is flagged as broken and DOT has active buy_blocked sliding alerts. Portfolio: keep the rial sleeve at full exposure 1.0 because USDT/TMN 48h +4.33% (regime cap 1.0) and 24h +1.84% supports staying invested; reduce beta to 0.8 (was 0.9) because beta sleeve return is slightly negative (-0.96%) and coins are volatile, so trim risk while keeping upside. I keep beta assets to the current weighted trio (PEPE, ADA, LINK) which match the sleeve weights and universe.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
