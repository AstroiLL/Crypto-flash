#!/usr/bin/env python
# import pandas as pd
# from pandas import DataFrame
# import numpy as np
# from datetime import datetime as dt
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots

from DiLL.crypto import Crypto
from DiLL.utils import SMA, hd


exchange = 'BITMEX'
crypto = 'BTC/USD'
cry = Crypto(exchange=exchange, crypto=crypto, period='1h', indexes=True)
cry.update_crypto()
df = cry.load_crypto(limit=2_400)
df_exch = cry.get_list_exch()
refresh = {'1m': 60, '1h': 240, '1d': 400}
# diap_days = 10

refr = 120
maxvols_g = 4
act_g = 'Close'
vol_lev = 0.6

app = dash.Dash()
app.layout = html.Div([
    html.Div([
        dcc.RadioItems(
            id='Crypto',
            options=[{'label': i, 'value': i} for i in df_exch['Crypto']],
            value='BTC/USD', persistence=True, persistence_type='memory', labelStyle={'display': 'inline-block'}
        ),
        dcc.Input(id='newCrypto', persistence=True, persistence_type='memory', debounce=True, value='', type='text'),
        html.Br(),
        # html.Label('Период'),
        dcc.RadioItems(
            id='Period',
            options=[{'label': i, 'value': i} for i in ['1d', '1h', '1m']],
            value='1h'
        ),
        dcc.RadioItems(
            id='Act',
            options=[{'label': i, 'value': i} for i in ['Open', 'Close']],
            value='Close'
        ),
        html.Label('Количество максимумов '),
        dcc.Input(
            id="Maxvols",
            type="number",
            placeholder="Количество максимумов",
            value=4,
            min=0,
        ),
    ], style={'columnCount': 3}),
    # html.Br(),
    # html.Label('Дни'),
    html.Div([
        dcc.Slider(
            id='Days',
            min=1,
            max=400,
            value=100,
            marks={i: str(i) for i in range(0, 401, 50)},
            step=1,
            # updatemode='drag'
        ),
    ]),
    dcc.Interval(
        id='interval-component',
        interval=refr * 1000,  # in milliseconds
        n_intervals=0
    ),
    html.Br(),
    html.Hr(),
    html.Div([
        html.Button('Обновить', id='Button')
    ], style={'display': 'block', 'margin-left': 'calc(50% - 110px)'}),
    html.Div([dcc.Graph(id='out')])
])


@app.callback(
    Output('out', 'figure'),
    [Input('newCrypto', 'value'),
     Input('Crypto', 'value'),
     Input('Period', 'value'),
     Input('Days', 'value'),
     Input('Act', 'value'),
     Input('Button', 'n_clicks'),
     Input('Maxvols', 'value'),
     Input('interval-component', 'n_intervals')])
def update_graph(newCrypto, crypto, period, days, act, but, maxvols, intervals):
    global df, cry, refr, maxvols_g, act_g, df_exch, df_exch
    refr = refresh[period]
    bars = days
    sbars = 1
    print('>' + newCrypto + '<')
    if newCrypto != '':
        crypto = newCrypto
    if crypto == 'BTC/USD':
        exchange = 'BITMEX'
    else:
        exchange = 'BINANCE'
    if period == '1h':
        # days = days if days < 60 else 60
        bars = days * 24
        sbars = 24
    elif period == '1m':
        sbars = 1440
        days = days if days < 30 else 30
        bars = days * 1440
    if maxvols == maxvols_g and act == act_g:
        cry = Crypto(exchange=exchange, crypto=crypto, period=period, indexes=True)
        cry.update_crypto()
        df = cry.load_crypto(limit=bars)
        bars = cry.limit
        if period == '1h':
            # days = days if days < 60 else 60
            bars = days * 24
            sbars = 24
        elif period == '1m':
            sbars = 1440
            days = days if days < 30 else 30
            bars = days * 1440
    df_exch = cry.get_list_exch()
    maxvols_g = maxvols
    act_g = act
    maxv = df['Volume'].nlargest(maxvols).index
    df_last = df[act][-1]
    df['lsl'] = df[act] - df_last
    df['ls_color'] = df['lsl'].where(df['lsl'] >= 0, 'blue').where(df['lsl'] < 0, 'red')
    Voll = df['Volume'][df['lsl'] < 0].sum()
    Vols = df['Volume'][df['lsl'] >= 0].sum()
    Price_max = df[act].max()
    Price_min = df[act].min()
    grid = (Price_max - Price_min) / 100
    df['Prof_Act'] = df[act] // grid * grid
    dfg = df[df['Volume'] >= df['Volume'].max() * vol_lev].groupby(['Prof_Act']).sum()
    fig = make_subplots(rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": False}]], shared_xaxes=True,
                        shared_yaxes=True, vertical_spacing=0.001, horizontal_spacing=0.01, column_widths=[0.8, 0.2])
    # Grafik Candelstik
    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df['Open'], close=df['Close'], high=df['High'], low=df['Low'],
                increasing_line_color='blue', decreasing_line_color='red', showlegend=False
        ), 1, 1, secondary_y=False,
    )
    # SMA(7d)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=SMA(df[act], 7 * sbars), mode='lines', name='SMA(7d)',
            line=dict(
                width=2,
                color='magenta',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # SMA(30d)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=SMA(df[act], 30 * sbars), mode='lines', name='SMA(30d)',
            line=dict(
                width=2,
                color='blue',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # SMA(60d)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=SMA(df[act], 60 * sbars), mode='lines', name='SMA(60d)',
            line=dict(
                width=2,
                color='red',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # Vert Vol
    fig.add_trace(
        go.Bar(x=df.index, y=df['Volume'].where(df['Volume'] >= df['Volume'].max()*vol_lev, 0), name='VolV',
            marker_color='black', showlegend=True, opacity=0.7, width=4000000),
        row=1, col=1, secondary_y=True)
    # Hor Vol
    if dfg.shape[0] > 1:
        fig.add_trace(go.Bar(
            x=dfg['Volume'],
            y=dfg.index,
            orientation='h',
            marker_color='blue',
            name='VolH',
            showlegend=False
        ), 1, 2
        )
    # End price
    fig.add_trace(
        go.Scatter(
            x=[df.index[-1]],
            y=[df[act][-1]],
            text=df[act][-1],
            textposition="top right",
            mode="text",
            showlegend=False,
            # font=dict(
            #     # family="Courier New, monospace",
            #     family="Roboto mono",
            #     size=18,
            #     color="red"
            # )
        ), 1, 1, secondary_y=False)
    # Level price
    fig.add_trace(
        go.Scatter(
            x=[df.index[-1] for i in range(maxvols)],
            y=df[act][maxv],
            text=df[act][maxv],
            textposition="top right",
            mode="text",
            showlegend=False
        ), 1, 1, secondary_y=False)
    # Vol Flash
    fig.add_trace(
        go.Scatter(
            x=[maxv[i] for i in range(maxvols)],
            y=df[act][maxv],
            marker=dict(
                size=(df['Volume'][maxv] / df['Volume'][maxv].max() * 30).astype('int64'),
                # size=df['Volume'][maxv].rank()*5,
                color=df['ls_color'][maxv],
                line=dict(color=df.Volume, width=1)
            ),
            mode='markers',
            # text=df[act][maxv],
            # textposition="top right",
            # mode="text",
            showlegend=False
        ), 1, 1, secondary_y=False)
    # Line
    [fig.add_shape(
        dict(
            type="line", xref='x', yref='y', x0=maxv[i], x1=df.index[-1],
            y0=df[act][maxv][i], y1=df[act][maxv][i], line=dict(color=df['ls_color'][maxv][i])
        )
    ) for i in range(maxvols)]
    # Levels
    [fig.add_annotation(
        dict(
            x=maxv[i],
            y=df[act][maxv][i],
            xref="x",
            yref="y",
            text=f"V:{df['Volume'][maxv][i]:,.0f}",
            hovertext=f"{df[act][maxv][i]}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            ax=-40,
            ay=-40
        )
    ) for i in range(maxvols)]
    fig.update_layout(
        title=f"Crypto-flash5 {exchange} {crypto} {bars}*{period}={days}D  SMA(7d+30d+60d)  VolUp: {hd(Voll-Vols)}",
        xaxis_title="Время",
        yaxis_title=f"{crypto}",
        height=700,
        xaxis_rangeslider_visible=False,
        # legend_orientation="h",
        legend=dict(x=0, y=1, orientation='h'),
        font=dict(
            # family="Courier New, monospace",
            family="Roboto mono",
            size=9,
            color="blue"
        )
    )
    return fig


if __name__ == '__main__':
    app.run_server(port=8052, debug=True, use_reloader=True)
