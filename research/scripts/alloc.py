import json, numpy as np, pandas as pd
d = json.load(open('data/hourly.json'))
def ser(s):
    x = d[s]; t = x['t0'] + np.array(x['t']) * 3600
    return pd.Series(x['c'], index=pd.to_datetime(t, unit='s'))
px = pd.DataFrame({s: ser(s) for s in d}).ffill().dropna()
FEE = 0.0035
def trend_alloc(sym, N, band=0.003, fee=FEE):
    c = px[sym]; e = c.ewm(span=N, adjust=False).mean()
    pos = 0; eq = [1.0]; trades = 0
    for i in range(1, len(c) - 1):
        want = 1 if c.iloc[i] > e.iloc[i] * (1 + band) else (0 if c.iloc[i] < e.iloc[i] * (1 - band) else pos)
        r = eq[-1]
        if want != pos:
            r *= (1 - fee); trades += 1; pos = want
        if pos: r *= c.iloc[i + 1] / c.iloc[i]
        eq.append(r)
    eq = pd.Series(eq, index=c.index[:len(eq)])
    return eq, trades
out = {}
for s in ['USDTTMN', 'BTCTMN', 'XAUTTMN', 'BNBTMN', 'TRXTMN', 'ETHTMN']:
    for N in (48, 96, 144):
        eq, tr = trend_alloc(s, N)
        r3 = (eq.shift(-72) / eq - 1).dropna()          # all rolling 3-day windows
        dd = (1 - eq / eq.cummax()).max()
        bh3 = (px[s].shift(-72) / px[s] - 1).dropna()
        out[f'{s}_ema{N}'] = dict(total=round((eq.iloc[-1]-1)*100, 2), trades=tr, maxDD=round(dd*100, 2),
                                  win3d=round((r3 > 0).mean()*100), med3d=round(r3.median()*100, 2),
                                  p10_3d=round(r3.quantile(.1)*100, 2), bh_med3d=round(bh3.median()*100, 2),
                                  bh_win3d=round((bh3 > 0).mean()*100), bh_p10=round(bh3.quantile(.1)*100, 2))
print(pd.DataFrame(out).T.to_string())
