import json, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
d = json.load(open('data/m5_all.json'))
def S(s, k): return np.array(d[s][k], dtype=float)
u_c, u_l = S('USDTTMN','c'), S('USDTTMN','l')
FM_T, FT_T, FT_U = 0.0025, 0.003, 0.0013
cost = FM_T + FT_U + FT_T
N = len(u_c); half = N//2
rows = []
coins = ['BTC','ETH','XRP','DOGE','SOL','TRX','ADA','BNB','PEPE']
for ci, co in enumerate(coins):
    tc, tl, th, tv = S(co+'TMN','c'), S(co+'TMN','l'), S(co+'TMN','h'), S(co+'TMN','v')
    uc, ul = S(co+'USDT','c'), S(co+'USDT','l')
    fv = uc * u_c
    dev = tc / fv - 1
    ret_u3 = np.r_[np.zeros(3), np.log(uc[3:]/uc[:-3])]
    ret_u12 = np.r_[np.zeros(12), np.log(uc[12:]/uc[:-12])]
    usdt3 = np.r_[np.zeros(3), np.log(u_c[3:]/u_c[:-3])]
    rng = (th - tl) / tc
    dev_mean = pd.Series(dev).rolling(288, min_periods=48).mean().values
    dev_sd = pd.Series(dev).rolling(288, min_periods=48).std().values
    vol12 = pd.Series(np.log(uc)).diff().rolling(12).std().values
    for m in (0.004, 0.006, 0.008, 0.01, 0.013):
        for i in range(300, N-1):
            bid = fv[i-1] * (1 - cost - m)
            if tl[i] <= bid * 0.999:
                h = min(uc[i], ul[i+1]) * min(u_c[i], u_l[i+1])
                r = h * (1-FT_U)*(1-FT_T) / (bid/(1-FM_T)) - 1
                rows.append(dict(coin=ci, m=m, half=int(i>=half), t=i, r=r,
                    dev_prev=dev[i-1], dev_z=(dev[i-1]-dev_mean[i-1])/dev_sd[i-1] if dev_sd[i-1] else 0,
                    dev_mean=dev_mean[i-1], dev_sd=dev_sd[i-1], ret_u3=ret_u3[i-1], ret_u12=ret_u12[i-1],
                    usdt3=usdt3[i-1], rng=rng[i-1], vol12=vol12[i-1]))
X = pd.DataFrame(rows).dropna()
F = ['m','dev_prev','dev_z','dev_mean','dev_sd','ret_u3','ret_u12','usdt3','rng','vol12']
tr, te = X[X.half==0], X[X.half==1]
clf = HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.05, min_samples_leaf=30, l2_regularization=1.0, random_state=0)
clf.fit(tr[F], (tr.r > 0).astype(int))
p = clf.predict_proba(te[F])[:,1]
print('train fills', len(tr), 'test fills', len(te), 'test AUC', round(roc_auc_score((te.r>0).astype(int), p),3))
# compare policies on test half: dedupe per (coin,t) -> choose one quote margin
te = te.assign(p=p)
for th in (0.0, 0.6, 0.7, 0.8, 0.85):
    sel = te[te.p >= th]
    # one fill per coin/time: keep the smallest margin that passes (that's the order we'd have quoted)
    sel = sel.sort_values('m').groupby(['coin','t']).head(1)
    print(f'ML p>={th}: fills {len(sel)} avg {sel.r.mean()*1e4:.1f}bps win {(sel.r>0).mean()*100:.0f}% sum {sel.r.sum()*100:.1f}%')
# static baseline: per-coin best margin chosen on TRAIN half, applied on test
best = tr.groupby(['coin','m']).r.mean().reset_index()
choice = {}
for ci, g in best.groupby('coin'):
    g = g[g.r > 0.001]
    if len(g): choice[ci] = g.sort_values('m').iloc[0].m
base = te[te.apply(lambda r: choice.get(r.coin) == r.m, axis=1)]
print(f'static per-coin margin (from train): fills {len(base)} avg {base.r.mean()*1e4:.1f}bps win {(base.r>0).mean()*100:.0f}% sum {base.r.sum()*100:.1f}%  choice={ {coins[int(k)]:v for k,v in choice.items()} }')
