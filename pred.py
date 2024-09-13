#!/usr/bin/env python3

import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.linear_model import LinearRegression
import datetime as dt
import warnings

warnings.filterwarnings('ignore')

ticker = input('[=] ticker [=]\t').upper()
t = yf.Ticker(ticker)
h = t.history(start='2000-1-1',end=dt.date.today(),interval='1mo')#["Close"]
df = h["Close"] 
ret = df.pct_change()[1:]
mu = ret.rolling(3).mean()
sig = ret.rolling(3).std()
X = np.vstack((mu[3:],sig[3:])).T
y = np.matrix(ret[2:-1]).T
lr  = LinearRegression(fit_intercept=True)
fit = lr.fit(X, np.asarray(y))
print("Score\t",fit.score(X, np.asarray(y)))
x = fit.coef_
print(x)
exp_mu = x[0][0]
print("Factor on mu...\t",exp_mu)
exp_sig = x[0][1]
print("Factor on sigma...\t",exp_sig)
pred = x@np.matrix([mu[-1],sig[-1]]).T
print("Predicted Change...\t",pred.item()*100,'%')
price = df[-1]*(1+pred.item())
print("Current Price...\t",df[-1])
print("Predicted Price...\t",price)
