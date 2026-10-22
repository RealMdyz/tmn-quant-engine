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

- Equity: **5,000,000 TMN** (+0.000%)
- Max drawdown: **0.000%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 1 (sources: {'llm:boxapi': 1})
- Events: {'coin_skipped': 273, 'live_self_test': 39, 'cancel_all': 1, 'startup': 1, 'regime': 1, 'policy': 1, 'sleeve_order': 16, 'quote': 5, 'buy_blocked': 2, 'buy_unblocked': 1, 'state_restored': 38}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 1.4,
    "AVAX": 1.4,
    "SUI": 1.2
  },
  "pause": false,
  "reasoning": "I pick FIL, AVAX and SUI because they clear the minimum Toman spread requirement and show a mix of width and activity: FIL spread 111.1 bps with vol24h 5,725M TMN and premium +32.6bps; AVAX spread 116.1 bps with vol24h 3,478M TMN and premium +4.4bps; SUI spread 97.7 bps with vol24h 6,074M TMN and premium -8.6bps. I set wide half-spreads (h 1.4% for FIL and AVAX, 1.2% for SUI) because we have no profitable live round trips yet and historical backtests show narrow quotes are picked off — so prefer the top of the allowed h range to protect vs adverse selection. pause=false because there is no market-wide shock or news trigger. Sleeves: the USDT/TMN regime shows ch48 +4.08% (usdt_tmn 272,056) so the rial is weakening and the exposure cap is 1.0; therefore I keep both sleeves fully allocated (rial=1.0, beta=1.0) and select PEPE/ADA/LINK for beta as they are the current weighted universe and suit high-momentum exposure.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
