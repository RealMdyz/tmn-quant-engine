import json, numpy as np, pandas as pd
d = json.load(open('data/m5_all.json'))
def df(s):
    x = d[s]; return pd.DataFrame({k: x[k] for k in 'ohlcv'}, index=pd.to_datetime(x['t'], unit='s'))
coins = ['BTC','ETH','XRP','DOGE','SOL','TRX','ADA','BNB','PEPE']
def ema(s, n): return s.ewm(span=n, adjust=False).mean()
def rsi(c, n=14):
    dd = c.diff(); up = dd.clip(lower=0).ewm(alpha=1/n).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=1/n).mean()
    return 100 - 100/(1+up/dn)
def run(x, entry, tp, sl, H, fee):
    c,h,l,o = x.c.values, x.h.values, x.l.values, x.o.values
    tr=[]; i=50; n=len(c)
    while i < n-2:
        if entry[i]:
            pin=o[i+1]; j=i+1; out=None
            while j < min(n-1, i+1+H):
                if l[j] <= pin*(1-sl): out=pin*(1-sl); break
                if h[j] >= pin*(1+tp): out=pin*(1+tp); break
                j+=1
            if out is None: out=c[j]
            tr.append(out/pin*(1-fee)**2-1); i=j+1
        else: i+=1
    return tr
rows=[]
for mkt in ['USDT','TMN']:
    fee = 0.0013 if mkt=='USDT' else 0.003
    for name in ['rsi_mr','bb_mr','breakout','ema_trend']:
        for (tp,sl,H) in [(0.006,0.006,24),(0.01,0.008,48),(0.02,0.012,144)]:
            allt=[]
            for co in coins:
                x=df(co+mkt); c=x.c
                if name=='rsi_mr': e=(rsi(c)<25).values
                elif name=='bb_mr': m=c.rolling(48).mean(); s=c.rolling(48).std(); e=(c<m-2.5*s).values
                elif name=='breakout': e=(c>x.h.rolling(48).max().shift(1)).values & (x.v>x.v.rolling(48).mean()*2).values
                else: f=ema(c,24); s_=ema(c,96); e=((f>s_)&(f.shift(1)<=s_.shift(1))).values
                allt += run(x,e,tp,sl,H,fee)
            a=np.array(allt)
            rows.append([mkt,name,f'{tp*100:.1f}/{sl*100:.1f}/{H*5//60}h',len(a),round(a.mean()*1e4,1) if len(a) else None, round((a>0).mean()*100) if len(a) else None])
print(pd.DataFrame(rows,columns=['mkt','strat','tp/sl/h','n','avg_bps','win%']).to_string())
