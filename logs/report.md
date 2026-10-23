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

- Equity: **5,012,367 TMN** (+0.247%)
- Max drawdown: **2.103%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 74 (sources: {'llm:boxapi': 74})
- Events: {'coin_skipped': 427, 'live_self_test': 61, 'cancel_all': 9, 'startup': 9, 'regime': 9, 'policy': 74, 'sleeve_order': 171, 'quote': 2070, 'buy_blocked': 5311, 'buy_unblocked': 5259, 'state_restored': 60, 'sleeve_fill': 10, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "FIL": 1.4,
    "CHZ": 1.2,
    "BCH": 1.3
  },
  "pause": false,
  "reasoning": "Pick FIL, CHZ and BCH because each has Toman spread >= 80 bps (FIL 94.7 bps, CHZ 159.1 bps, BCH 82.0 bps) so they meet the minimum 80 bps rule and have reasonable 24h Toman activity (FIL vol 4,275M, BCH 1,983M, CHZ 1,440M TMN). Use wide half-spreads due to fair-value or market volatility: FIL fv_vol 313 bps => very volatile so h=1.4% (near top), CHZ fv_vol 472 bps so h=1.2%, BCH fv_vol 347 bps so h=1.3% to protect vs adverse selection. I avoid CAKE and several other names because buy was blocked (CAKE: \"Toman book sliding\") or fair-value sliding (AVAX/IMX/ENA) — i.e. clear short-term Toman-book instability. Sleeves: keep rial at full exposure 1.0 because USDT/TMN 48h +2.11% (regime cap=1.0) and the rial sleeve is sized to 2,620,000 TMN (current value ~2,590,804 TMN, return -0.93%) so retain exposure to the ongoing rial-weakening trend; keep beta at 0.8 (current scale_now 0.8, value 1,859,134 TMN, return +1.75%) and limit beta to the existing 0.8 because it already outperformed short-term but is higher-volatility. Beta assets chosen are PEPE, LINK and ADA (current beta weights/universe entries with momentum and no coin-specific negative flags).",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
