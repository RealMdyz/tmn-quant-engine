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

- Equity: **4,969,107 TMN** (-0.618%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 32 (sources: {'llm:boxapi': 32})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 32, 'sleeve_order': 169, 'quote': 636, 'buy_blocked': 2090, 'buy_unblocked': 2052, 'state_restored': 57, 'sleeve_fill': 8, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "GALA": 1.3,
    "CAKE": 0.95,
    "BCH": 1.1
  },
  "pause": false,
  "reasoning": "I pick up to three markets with Toman spreads >=80 bps and without a buy_blocked or recent fair-value shock. GALA has the widest spread (160.3 bps), decent volume (vol24h 2,135M TMN) and moderate fv_vol 244.8 bps so I quote wide h=1.3% to avoid picking off. CAKE has spread 87.2 bps, low fv_vol 98.9 bps and vol24h 2,269M TMN so I quote tighter h=0.95% to capture spread with lower volatility. BCH (spread 85.0 bps, vol24h 1,235M TMN, fv_vol 368.5 bps) is chosen with h=1.1% as a middle ground. I do not quote FIL/ARB/UNI/others because several show buy_blocked or recent sliding Toman-books (e.g. FIL premium -156 bps, ARB FV fell -89 bps). Sleeves: USDT/TMN 48h +4.33% gives full exposure cap 1.0, so keep rial at 1.0 (rial sleeve size intact; current scale 1.0, value 2,607,586 TMN) and keep beta at current scale 0.8 (beta return +1.15%, value 1,855,339 TMN); beta assets remain PEPE/ADA/LINK per the sleeve weights and momentum.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
