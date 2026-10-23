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

- Equity: **4,971,430 TMN** (-0.571%)
- Max drawdown: **2.798%**
- Traded volume: 234,959 TMN

![equity](equity_live.png)

- Market maker: **1 fills** (1 buys, 0 sells), 1 risk exits, realised PnL **-2,109 TMN**

| coin | buys | sells | exits | realised PnL TMN |
|---|---|---|---|---|
| PENGU | 1 | 0 | 1 | -2,109 |

- AI supervisor decisions: 81 (sources: {'llm:boxapi': 81})
- Events: {'coin_skipped': 441, 'live_self_test': 63, 'cancel_all': 11, 'startup': 11, 'regime': 13, 'policy': 81, 'sleeve_order': 303, 'quote': 2354, 'buy_blocked': 5699, 'buy_unblocked': 5637, 'state_restored': 62, 'sleeve_fill': 24, 'orphan_adopted': 1, 'fill': 1, 'exit': 1}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 0.9,
    "HYPE": 1.3,
    "FIL": 1.4
  },
  "pause": false,
  "reasoning": "I pick SUI, HYPE and FIL because each has Toman spread above our 80 bps cutoff (SUI 113.2, HYPE 118.8, FIL 106.6) and reasonable 24h volume (SUI 3.7bn, HYPE 1.6bn, FIL 3.5bn TMN). SUI has low fair-value volatility (fv_vol 52.8 bps) so I quote tighter (h=0.9%) to capture spread with lower adverse-selection risk; HYPE shows higher fv_vol (161.2 bps) so I widen to h=1.3%. FIL has very low fv_vol (30.2 bps) but known micro shocks and previous rapid adverse fills, so I set it wide (h=1.4%) to reduce being picked off despite its attractive premium (premium +122.7 bps). I avoid PENGU and CHZ because PENGU produced a large losing round trip (realised -2,109 TMN, avg -178.3 bps) and CHZ has a frozen USDT book, and I skip markets with buy_blocked sliding notes. For sleeves: USDT/TMN 48h +1.40% gives full regime cap, so I partially re-enable exposure — rial 0.75 to capture continued rial weakness (rial sleeve historically +0.88% when entered in the rial-weakening regime) while limiting downside, and beta 0.5 because beta sleeve is higher volatility (historical +1.28% but larger swings); I keep beta assets to PEPE/ADA/LINK per the sleeve weights/universe.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
