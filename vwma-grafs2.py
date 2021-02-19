import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from DiLL.crypto import Crypto

period = '1h'
pairs = {'BTC/USD': 'BITMEX',
         'ETH/USD': 'BITMEX',
         'ETH/BTC': 'BINANCE',
         'ADA/BTC': 'BINANCE',
         'ADA/USDC': 'BINANCE',
         'DOT/BTC': 'BINANCE',
         'FET/BTC': 'BINANCE',
         'ETC/BTC': 'BINANCE',

         }
crypto = 'ETC/BTC'
exchange = pairs[crypto]
cry = Crypto(verbose=False)
cry.open(exchange=exchange, crypto=crypto, period=period, update=True)
cry.updating()

length = 168
df = cry.load(limit=length*4)

def wvwma(length=24):
    return ta.wma(df['Open'] * df['Volume'], length=length) / ta.wma(df['Volume'], length=length)


def plot(dff, data='Open', name='', color_u='blue', color_d='red', width=2, row=1, col=1):
    fig.add_trace(go.Scatter(x=dff.index, y=dff[data],
        mode='markers+lines',
        line=dict(color=color_u),
        marker=dict(
            colorscale=[[0, color_d], [1, color_u]],
            color=(dff[data] >= 0).astype('int'),
            size=width,
        ),
        name=name), row=row, col=col)

len_d = 48
data_w = f'Wvwma_{length}'
data_d = f'Wvwma_{len_d}'
data_wd = f'Wvwma_{len_d}-{length}'
data_o = f'Open_Wvwma_{length}'
data_od = f'Open_Wvwma_{len_d}'
df[data_w] = wvwma(length=length)
df[data_d] = wvwma(length=len_d)
df[data_o] = df['Open'] - df[data_w]
df[data_wd] = df[data_d] - df[data_w]
df[data_od] = df['Open'] - df[data_d]


df = df[-length*2:]

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[0.4, 0.1, 0.4])
plot(df, data='Open', name='Open', color_u='black', color_d='black', width=4, row=1, col=1)

plot(df, data=data_w, name=data_w, color_u='red', color_d='red', width=4, row=1, col=1)
plot(df, data=data_d, name=data_d, color_u='cyan', color_d='cyan', width=2, row=1, col=1)

fig.add_trace(
    go.Bar(x=df.index, y=df['Volume'].where(df['Volume'] >= df['Volume'].max() * 0.2, 0), name='Volume',
           marker=dict(color='grey'), showlegend=True, opacity=0.4,
           hoverinfo='none'
           ),
    row=2, col=1)

plot(df, data=data_o, name=data_o, color_u='blue', color_d='red', width=4, row=3, col=1)
# plot(df, data=data_od, name=data_od, color_u='blue', color_d='red', width=4, row=3, col=1)
plot(df, data=data_wd, name=data_wd, color_u='cyan', color_d='orange', width=2, row=3, col=1)

fig.update_layout(title=f"{exchange} {crypto} 1h", xaxis_title="Date", yaxis_title=f"{exchange}.{crypto}", )
fig.show()
