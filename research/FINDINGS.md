# Research log (live Wallex data, 2026-10-22)

## Account / package facts (from API)
- Hackathon package id 183: loan 5,000,000 TMN, assurance 0, liquidation limit 900 TMN, 3 days, no daily fee.
- Unavailable markets: ~300 (list via /v1/prop/packages/183). Majors allowed: BTC, ETH, USDT, XRP, DOGE, SOL, TRX, ADA, BNB, PEPE, XAUT (+ their USDT pairs).
- Account fee tier 1 (user screenshot): TMN maker 0.25% / taker 0.30%; USDT maker 0.10% / taker 0.13%.
- Next TMN tier at 100M TMN 30-day volume: 0.20/0.25.
- 5M TMN ~= 18.7 USDT -> our size has ~zero market impact on majors.
- Candle API: res=1 works for ~1 day spans; res=15 returns 1-min bars for 10 days; res=60 gives ~29 days.

## Directional strategies (net of real fees)
- Hourly 29d, TMN fee 0.35%: Donchian -73bps/trade, EMA cross -34, momentum -46, dip-buy -37, RSI MR +16 (weak).
- 5-min 10d, USDT markets fee 0.13%: all ~ -1 to -53 bps/trade. TMN markets fee 0.30%: -38 to -75.
- Rolling 3-day windows: even best trend rules ~50% win. => no robust directional edge at these costs.

## Structural factors
- USDTTMN +17.5% in 29 days (rial depreciation), but lumpy (10d: +0.27%, daily vol 1.6%).
- Fair value FV = coinUSDT x USDTTMN. Deviation std 17-57 bps (majors), up to 99 bps (ADA); mean-reverting (ac60 0.1-0.4).
- |dev| > 1% episodes in 10 days: TRX 134, ADA 126, PEPE 103, DOGE 55, BNB 55, SOL 25, XRP 11, ETH 9, BTC 2.

## Candidate primary strategy: cross-market fair-value arbitrage / hedged market making
- Taker triangle TMN->coin->USDT->TMN costs ~0.73%; live book sampler started to measure executable edge.
- Maker variant: rest bids on coinTMN below liquidation value (coinUSDT_bid x USDTTMN_bid) minus costs; hedge instantly on fill.
