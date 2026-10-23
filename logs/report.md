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

- Equity: **5,089,693 TMN** (+1.794%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 66 (sources: {'llm:boxapi': 66})
- Events: {'coin_skipped': 427, 'live_self_test': 61, 'cancel_all': 9, 'startup': 9, 'regime': 9, 'policy': 66, 'sleeve_order': 171, 'quote': 1917, 'buy_blocked': 4617, 'buy_unblocked': 4567, 'state_restored': 60, 'sleeve_fill': 10, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "CHZ": 0.9,
    "GALA": 1.3,
    "BCH": 1.2
  },
  "pause": false,
  "reasoning": "I pick CHZ, GALA and BCH because the bot never bids where spread_bps < 80: CHZ has the widest Toman spread (149.8 bps) with low fv_vol_bps (34.1) so I quote tighter (h=0.9%) to capture the large static spread. GALA has spread 98.6 bps, premium 66.5 bps and higher fv_vol_bps (206) so I widen to h=1.3% for protection. BCH has spread 83.2 bps, vol24h_mtmn 1,798 and fv_vol_bps 155.6 so I set h=1.2% to balance activity and adverse-selection risk. I avoid FIL/IMX/UNI/AVAX because buy_blocked or rapid fair-value slides indicate Toman-book instability. For sleeves I keep rial at full 1.0 exposure because USDT/TMN 48h +3.36% (regime cap 1.0) and the rial sleeve is profitable (value_tmn 2,617,522; return 0.1%), and keep beta at current 0.8 scale (beta value 1,905,410, return 4.29%) with assets PEPE/ADA/LINK per the sleeve weights and positive momentum.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
