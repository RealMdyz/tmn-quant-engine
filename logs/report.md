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

- Equity: **4,988,344 TMN** (-0.233%)
- Max drawdown: **0.293%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 2 (sources: {'llm:boxapi': 2})
- Events: {'coin_skipped': 385, 'live_self_test': 55, 'cancel_all': 3, 'startup': 3, 'regime': 3, 'policy': 2, 'sleeve_order': 68, 'quote': 5, 'buy_blocked': 97, 'buy_unblocked': 86, 'state_restored': 54, 'sleeve_fill': 5}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 1.1,
    "HYPE": 1.4,
    "CAKE": 0.95
  },
  "pause": false,
  "reasoning": "Pick FIL, HYPE and CAKE because the bot never quotes where spread_bps <80 and these have wide Toman spreads: FIL 95.0 bps, HYPE 103.9 bps, CAKE 99.0 bps. FIL gets a moderate h=1.1% because it is busy (vol24h 5,555M TMN), has very wide USDT spread 212.7 bps and low fv_vol 21.2 bps (stable FV). HYPE gets the widest h=1.4%: spread 103.9 bps, good volume (4,221M) and premium +15.1 bps; widen to avoid being picked off. CAKE is calm (fv_vol 3.8 bps) with spread 99.0 bps so we quote a bit tighter at h=0.95% to capture spread while FV is stable. Do not pause: no market-wide shock detected. Keep full sleeve exposures (rial=1.0, beta=1.0) because USDT/TMN 48h +4.09% (regime cap 1.0) and both sleeves are already scaled (rial value 872,036 TMN, beta value 1,496,155 TMN) and recent strategy shows sleeves profit when rial weakens.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
