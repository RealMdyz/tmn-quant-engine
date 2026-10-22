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

- Equity: **4,967,086 TMN** (-0.658%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 7 (sources: {'llm:boxapi': 7})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 7, 'sleeve_order': 68, 'quote': 35, 'buy_blocked': 546, 'buy_unblocked': 513, 'state_restored': 57, 'sleeve_fill': 5, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "CAKE": 0.9,
    "SUI": 1.4,
    "GALA": 1.5
  },
  "pause": false,
  "reasoning": "I pick CAKE, SUI and GALA (max 3). CAKE has a very wide Toman spread 105.0 bps and extremely low fv_vol_bps 4.9 so I quote tighter (h=0.9%) to capture the rich spread with low adverse-vol risk; CAKE is already quoted_now true so continuity matters. SUI has spread 83.3 bps with decent volume 5,796M TMN but high fv_vol_bps 124.8 and a positive premium 32.5 bps, so I set a wide h=1.4% to avoid being picked off. GALA has spread 100.6 bps and high usdt_spread_bps 391.1 (quoted_now true); fv_vol_bps 165.3 is elevated so I place the widest h=1.5% to protect against informed flow. I do not quote markets with spread_bps <80 (SOL/XRP/etc) or those with buy_blocked flags (AAVE/DOT/IMX). Sleeves: USDT/TMN 48h +4.54% gives full exposure cap 1.0, so keep the rial sleeve at 1.0 (current scale 1.0) and keep beta at 0.9 (current scale_now) given its small recent negative return (-1.07%) and higher risk; I keep the beta assets as the existing PEPE/ADA/LINK basket.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
