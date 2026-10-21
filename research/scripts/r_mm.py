import json, numpy as np, pandas as pd
d = json.load(open('data/m5_all.json'))
def S(s, k): return np.array(d[s][k], dtype=float)
u_c = S('USDTTMN','c')
FM_T, FT_T, FT_U = 0.0025, 0.003, 0.0013   # TMN maker, TMN taker, USDT taker
cost = FM_T + FT_U + FT_T                   # buy coin TMN maker, sell coin USDT taker, sell USDT->TMN taker
rows = []
for co in ['BTC','ETH','XRP','DOGE','SOL','TRX','ADA','BNB','PEPE']:
    tl, tc = S(co+'TMN','l'), S(co+'TMN','c')
    uc, uo = S(co+'USDT','c'), S(co+'USDT','o')
    n = len(tl)
    for m in (0.002, 0.004, 0.006, 0.01):
        pn = []
        for i in range(1, n-1):
            fv = uc[i-1] * u_c[i-1]                     # fair value known at start of bar i
            bid = fv * (1 - cost - m)                   # our resting bid on coinTMN
            if tl[i] <= bid:                            # filled during bar i
                # hedge at END of bar i (conservative: includes whatever crash caused the fill)
                proceeds = uc[i] * u_c[i] * (1 - FT_U) * (1 - FT_T)
                pn.append(proceeds / (bid / (1 - FM_T)) - 1)
        a = np.array(pn)
        rows.append([co, m*100, len(a), round(a.mean()*1e4,1) if len(a) else None,
                     round((a>0).mean()*100) if len(a) else None, round(a.sum()*100,2) if len(a) else 0])
r = pd.DataFrame(rows, columns=['coin','margin%','fills','avg_bps','win%','sum%'])
print(r.to_string())
print('\nbuy-side cost assumed %.2f%%' % (cost*100))
