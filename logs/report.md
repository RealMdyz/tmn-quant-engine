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

- Equity: **5,018,925 TMN** (+0.378%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 72 (sources: {'llm:boxapi': 72})
- Events: {'coin_skipped': 427, 'live_self_test': 61, 'cancel_all': 9, 'startup': 9, 'regime': 9, 'policy': 72, 'sleeve_order': 171, 'quote': 2018, 'buy_blocked': 5112, 'buy_unblocked': 5065, 'state_restored': 60, 'sleeve_fill': 10, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "CHZ": 0.9,
    "FIL": 0.95,
    "GALA": 1.2
  },
  "pause": false,
  "reasoning": "Pick CHZ, FIL, GALA because they have the widest Toman spreads: CHZ 170.7 bps, GALA 120.0 bps, FIL 98.0 bps; CHZ and FIL also show low fv_vol (53.7 and 56.2 bps) so we can quote slightly tighter. Set h conservative near upper-mid range: CHZ 0.9% (large spread, low fv_vol), FIL 0.95% (large premium 137.9 bps and wide USDT spread 368 bps), GALA 1.2% (higher fv_vol 208.9 bps so wider to avoid adverse selection). No pause — no market-wide shock visible. Sleeves: keep rial at full 1.0 exposure because USDT/TMN 48h +3.08% (regime cap=1.0) and the sleeve is sized for rial weakening, and keep beta at 0.8 (current scale_now 0.8, beta returning +2.22% on value_tmn 1.867M); beta assets remain PEPE/ADA/LINK per current weights and momentum.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
