import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
from sklearn.linear_model import LinearRegression
import datetime as dt

ticker = input("ticker <<\t").upper()
t = yf.Ticker(ticker)
h=t.history(start='2002-1-1',end=dt.date.today(),interval='3mo')#["Close"]
print(h)
h.to_csv('data.csv')

csv = pd.read_csv('./csv/dtr.csv')
csv['Time'] = pd.to_datetime(csv['Date'])
aapl = pd.read_csv('data.csv')
aapl = pd.DataFrame({'Time':pd.to_datetime(aapl.iloc[:,0]),'Close':aapl['Close']})

df = pd.concat([aapl,csv],1).dropna()
print(df.dropna())

df.to_csv('treasury.csv')

yc = []
for i in range(0,len(df)):
	target = df.iloc[i,2:]
	d1 = float((target['2 Mo'] - target['1 Mo'])/target['1 Mo'])
	d2 = float((target['3 Mo'] - target['2 Mo'])/target['2 Mo'])
	d3 = float((target['4 Mo'] - target['3 Mo'])/target['3 Mo'])
	d4 = float((target['6 Mo'] - target['4 Mo'])/target['4 Mo'])
	d5 = float((target['1 Yr'] - target['6 Mo'])/target['6 Mo'])
	d6 = float((target['2 Yr'] - target['1 Yr'])/target['1 Yr'])
	d7 = float((target['3 Yr'] - target['2 Yr'])/target['2 Yr'])
	d8 = float((target['5 Yr'] - target['3 Yr'])/target['3 Yr'])
	d9 = float((target['7 Yr'] - target['5 Yr'])/target['5 Yr'])
	d10 = float((target['10 Yr'] - target['7 Yr'])/target['7 Yr'])
	d11 = float((target['20 Yr'] - target['10 Yr'])/target['10 Yr'])
	d12 = float((target['30 Yr'] - target['20 Yr'])/target['20 Yr'])
	yc.append([d1,d2,d3,d4,d5,d6,d7,d8,d9,d10,d11,d12])
	
ret = df['Close'].pct_change()[1:]
A = np.array(yc)[:-2]
b = np.array(ret,dtype='float')[1:]
reg = LinearRegression().fit(A,b)
x = reg.coef_
print('Score\t',reg.score(A,b))

m1 = 5.13 # 1 month
m2 = 5.19 # 2 months
m3 = 5.05 # 3 months
m4 = 5.02 # 4 months
m6 = 4.72 # 6 months
m12 = 4.1 # 1 year
m24 = 3.65 # 2y
m36 = 3.54 # 3y
m60 = 3.49 # 5Y
m84 = 3.59 # 7 Year
m120 = 3.71 # 10 Year
m240 = 4.10 # 20 Year
m360 = 4.02 # 30 Year

d1 = (m2-m1)/m1#float((target['2 Mo'] - target['1 Mo'])/target['1 Mo'])
d2 = (m3-m2)/m2#0.005565862709#1#(5.42-5.39)/5.39 
d3 = (m4-m3)/m3#float((target['4 Mo'] - target['3 Mo'])/target['3 Mo'])
d4 = (m6 - m4)/m4
d5 = (m12-m6)/m6#float((target['1 Yr'] - target['6 Mo'])/target['6 Mo'])
d6 = (m24-m12)/m12#float((target['2 Yr'] - target['1 Yr'])/target['1 Yr'])
d7 = (m36-m24)/m24#float((target['3 Yr'] - target['2 Yr'])/target['2 Yr'])
d8 = (m60 - m36)/m36#float((target['5 Yr'] - target['3 Yr'])/target['3 Yr'])
d9 = (m84 - m60)/m60#float((target['7 Yr'] - target['5 Yr'])/target['5 Yr'])
d10 = (m120 - m84)/m84#float((target['10 Yr'] - target['7 Yr'])/target['7 Yr'])
d11 = (m240 - m120)/m120# float((target['20 Yr'] - target['10 Yr'])/target['10 Yr'])
d12 = (m360 - m240)/m240#float((target['30 Yr'] - target['20 Yr'])/target['20 Yr'])

f = x[0]*d1+x[1]*d2+x[2]*d3+x[3]*d4+x[4]*d5+x[5]*d6+x[6]*d7+x[7]*d8+x[8]*d9+x[9]*d10+x[10]*d11+x[11]*d12
print(f)
def fuc(s0,r,t):
	return s0*np.exp(r*t)
print("expected change {f}%".format(f=np.round(f*100,3)))   
print("expected price {f}".format(f=fuc(df['Close'][len(df)-1],f,12/12)))   
print("current price {f}".format(f=df['Close'][len(df)-1]))  
