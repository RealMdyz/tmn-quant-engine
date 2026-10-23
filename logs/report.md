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

- Equity: **5,100,196 TMN** (+2.004%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 56 (sources: {'llm:boxapi': 56})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 56, 'sleeve_order': 171, 'quote': 1508, 'buy_blocked': 4153, 'buy_unblocked': 4118, 'state_restored': 57, 'sleeve_fill': 10, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "PENGU": 1.2,
    "GALA": 1.4,
    "CAKE": 1.1
  },
  "pause": false,
  "reasoning": "I pick PENGU, GALA and CAKE because I only quote markets with Toman spread >= 80 bps: PENGU spread 182.8 bps (quoted_now), GALA 117.4 bps and CAKE 86.4 bps. I avoid FIL and CHZ because FIL is buy_blocked (Toman book sliding vs 200 bps baseline) and CHZ has its USDT book frozen (33 min), both make FV unreliable. I set half-spreads h wide given adverse-selection evidence: PENGU h=1.2% (very wide market, vol24h 1.85bn TMN, fv_vol 181.7 bps), GALA h=1.4% (high fv_vol 312 bps -> extra protection) and CAKE h=1.1% (spread 86.4 bps and low fv_vol 41.7 bps so a bit tighter). Sleeves: USDT/TMN 48h +3.45% gives full exposure cap 1.0 so keep rial at 1.0 (rial sleeve return +0.4%, value 2,625,450 TMN) and keep beta at current scale 0.8 (beta return +4.42%, value 1,915,203 TMN); keep beta assets PEPE/ADA/LINK as current weighted winners and no coin-specific negative news.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
