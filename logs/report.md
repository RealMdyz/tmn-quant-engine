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

- Equity: **4,961,094 TMN** (-0.778%)
- Max drawdown: **1.864%**
- Traded volume: 0 TMN

![equity](equity_live.png)

- AI supervisor decisions: 20 (sources: {'llm:boxapi': 20})
- Events: {'coin_skipped': 406, 'live_self_test': 58, 'cancel_all': 6, 'startup': 6, 'regime': 6, 'policy': 20, 'sleeve_order': 169, 'quote': 202, 'buy_blocked': 1475, 'buy_unblocked': 1435, 'state_restored': 57, 'sleeve_fill': 8, 'orphan_adopted': 1}

### Latest AI decision
```json
{
  "markets": {
    "SUI": 1.0,
    "CAKE": 0.9,
    "GALA": 1.4
  },
  "pause": false,
  "reasoning": "Picked SUI, CAKE and GALA because the bot only quotes markets with Toman spread >=80 bps: SUI spread 96.4 bps (fv_vol 26.3 bps, vol24h 5,175M TMN) and is already quoted (quoted_now=true) so we can attempt tighter quoting (h=1.0%). CAKE has spread 96.3 bps, very low fv_vol 12.5 bps and healthy USDT spread 104.7 bps; it's calm so use narrower h=0.9% to improve fill chance. GALA offers the widest Toman spread 141.1 bps and huge USDT spread 565 bps but high fv_vol 467 bps, so we quote wide (h=1.4%) to protect against adverse selection. Portfolio sleeves kept on because USDT/TMN 48h +4.33% => regime cap=1.0: keep rial at 1.0 (rial sleeve capital ~2.62M TMN, small negative return -0.17%) and keep beta at 0.8 (current scale_now 0.8, beta value run -0.96%); beta assets remain PEPE/ADA/LINK as per the sleeve weights and no coin-specific bad news in their universe.",
  "tool_trace": [],
  "source": "llm:boxapi"
}
```
