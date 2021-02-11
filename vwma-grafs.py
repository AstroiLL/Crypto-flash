import pandas_ta as ta
import plotly.graph_objects as go

from DiLL.crypto import Crypto

period = '1h'
crypto = 'BTC/USD'
# crypto = 'ETH/USD'
# crypto = 'ADA/USD'
exchange = 'BITMEX'
# exchange = 'BINANCE'
cry = Crypto(verbose=False)
cry.open(exchange=exchange, crypto=crypto, period=period, update=True)
cry.updating()
df = cry.load(limit=168 * 2)


def wvwma(length=24):
    return ta.wma(df['Open'] * df['Volume'], length=length) / ta.wma(df['Volume'], length=length)


def plot_wvwma(length=24, color='black', width=2):
    df['Wvwma'] = wvwma(length=length)
    fig.add_trace(go.Scatter(x=df.index[-48:], y=df['Wvwma'][-48:], line_color=color, line_width=width,
                             name=f'WVWMA-{length / 24:.2f}D'))


df['sma-2'] = ta.sma(df['Open'], length=2)
fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index[-48:], y=df['sma-2'][-48:], line_color='black', line_width=4, name='SMA-2'))
plot_wvwma(length=6, color='cyan', width=2)
plot_wvwma(length=12, color='blue', width=2)
plot_wvwma(length=24, color='green', width=2)
plot_wvwma(length=48, color='orange', width=2)
plot_wvwma(length=168, color='red', width=4)
fig.update_layout(title=f"{exchange}.{crypto}", xaxis_title="Date", yaxis_title=f"{exchange}.{crypto}", )
fig.show()
