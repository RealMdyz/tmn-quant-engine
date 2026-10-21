import json, numpy as np, pandas as pd
d = json.load(open('data/m5_all.json'))
def S(s, k): return np.array(d[s][k], dtype=float)
u_c, u_l = S('USDTTMN','c'), S('USDTTMN','l')
FM_T, FT_T, FT_U = 0.0025, 0.003, 0.0013
cost = FM_T + FT_U + FT_T
rows = []
N = len(u_c); half = N // 2
for co in ['BTC','ETH','XRP','DOGE','SOL','TRX','ADA','BNB','PEPE']:
    tl = S(co+'TMN','l'); uc = S(co+'USDT','c'); ul = S(co+'USDT','l'); tv = S(co+'TMN','v')
    for m in (0.004, 0.006, 0.008, 0.01):
        res = {'first': [], 'second': []}
        for i in range(1, N-1):
            fv = uc[i-1] * u_c[i-1]
            bid = fv * (1 - cost - m)
            if tl[i] <= bid * 0.999:                       # price must trade THROUGH our bid
                # pessimistic hedge: worst of (bar close, next bar low) on both USDT legs
                h_coin = min(uc[i], ul[i+1]); h_usdt = min(u_c[i], u_l[i+1])
                r = h_coin * h_usdt * (1-FT_U) * (1-FT_T) / (bid / (1-FM_T)) - 1
                res['first' if i < half else 'second'].append(r)
        for k, a in res.items():
            a = np.array(a)
            rows.append([co, m*100, k, len(a), round(a.mean()*1e4,1) if len(a) else None,
                         round((a>0).mean()*100) if len(a) else None])
r = pd.DataFrame(rows, columns=['coin','margin%','half','fills','avg_bps','win%'])
print(r.pivot_table(index=['coin','margin%'], columns='half', values=['fills','avg_bps','win%']).to_string())
