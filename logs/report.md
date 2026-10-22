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

- Equity: **4,965,527 TMN** (-0.689%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 19 (sources: {'llm:boxapi': 19})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 19, 'sleeve_order': 169, 'quote': 185, 'buy_blocked': 1370, 'buy_unblocked': 1334, 'state_restored': 57, 'sleeve_fill': 7, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "CAKE": 0.8,
    "CHZ": 0.9,
    "SUI": 1.0
  },
  "pause": false,
  "reasoning": "Pick CAKE, CHZ and SUI because all three have Toman spreads >= ~96–129 bps (CAKE 96.2, CHZ 129.2, SUI 99.8) and reasonable 24h volumes (CAKE 2.5bn TMN, CHZ 2.6bn, SUI 5.2bn). CAKE has very low FV volatility (fv_vol_bps 16.5) so I quote more aggressively (h=0.8%) to capture the wide Toman spread while limiting adverse selection; CHZ also has low FV vol (35.8) so h=0.9% is chosen to be slightly more conservative given its larger spread (129.2 bps). SUI shows higher FV volatility (88.1 bps) so I widen to h=1.0% to reduce pickoff risk. I avoid markets with buy_blocked or sliding Toman-book signals (e.g. ARB/UNI/FIL/DOT/WLD) and skip markets with spread_bps <80 (e.g. XRP, BNB). For sleeves the USDT/TMN 48h +4.33% gives a full exposure cap (cap=1.0) so keep rial at 1.0 (rial sleeve historically +0.88% when entered in this regime) and keep beta at its current scaled exposure 0.8 (beta sleeve presently scale_now 0.8, return -0.8%) with its three existing assets PEPE/ADA/LINK to retain momentum exposure while limiting risk.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
