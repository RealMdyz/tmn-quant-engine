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

- Equity: **5,022,904 TMN** (+0.458%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 43 (sources: {'llm:boxapi': 43})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 43, 'sleeve_order': 169, 'quote': 987, 'buy_blocked': 3080, 'buy_unblocked': 3040, 'state_restored': 57, 'sleeve_fill': 8, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "CAKE": 1.2,
    "GALA": 1.3,
    "FIL": 1.5
  },
  "pause": false,
  "reasoning": "I pick CAKE, GALA and FIL because each has Toman spread well above our 80 bps cutoff (CAKE 155 bps, GALA 137.5 bps, FIL 208.6 bps) and reasonable 24h TMN volume (CAKE 2,336m, GALA 1,412m, FIL 4,745m). I set wide half-spreads because FV volatility or adverse-selection risks are nontrivial: CAKE h=1.2 (fv_vol 136 bps moderate), GALA h=1.3 (fv_vol 382 bps), and FIL h=1.5 because although FIL’s fv_vol is low (24.3 bps) we have prior adverse-selection evidence (live FIL buy then -1.8%) so use the maximum h. I avoid markets with buy blocks or stale/unverifiable USDT books (e.g. CHZ, AVAX, DOT, IMX flagged) and skip all spreads <80 bps (many candidates). For sleeves I keep rial at 1.0 and beta at 0.8 because USDT/TMN 48h is +4.33% (regime cap =1.0) so the rial strategy remains supported and beta has positive recent returns (beta return 1.79% with scale_now 0.8); I allocate beta to PEPE/ADA/LINK following the existing weights and momentum.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
