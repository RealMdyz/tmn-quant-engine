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

- Equity: **4,961,444 TMN** (-0.771%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 8 (sources: {'llm:boxapi': 8})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 8, 'sleeve_order': 68, 'quote': 38, 'buy_blocked': 611, 'buy_unblocked': 575, 'state_restored': 57, 'sleeve_fill': 5, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 1.4,
    "BNB": 1.3
  },
  "pause": false,
  "reasoning": "I pick SUI and BNB because they are the only liquid markets above our 80 bps Toman-spread threshold without persistent buy blocks: SUI spread_bps=82.0 with vol24h_mtmn=5753 and fv_vol_bps=168.1 (still busy but somewhat noisy), so I set a wide half-spread h=1.4% to protect against adverse selection. BNB has high activity (vol24h_mtmn=81910) and spread_bps=81.4 with fv_vol_bps=131.5 so I quote slightly tighter at h=1.3% to capture flow while respecting our caution. I avoid GALA and CHZ because both show Toman-book sliding alerts (GALA: premium 6bps vs 52bps baseline; CHZ buy-blocked), and many other coins have spread_bps <80 so they are wasted slots. For sleeves I keep 'rial' at full exposure 1.0 (USDT/TMN 48h +4.64% gives cap=1.0 and rial sleeve return is only -0.28%) and keep 'beta' at current 0.9 (beta sleeve is already scaled 0.9, return -0.64%) selecting PEPE/ADA/LINK which are the current weights and fit the high-momentum preference. Overall I favor being wide and cautious (h near the top of 0.8–1.5) because fv_vol and past fills indicate adverse selection risk.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
