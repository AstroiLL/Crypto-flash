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
from DiLL.utils import SMA

exchange = 'BINANCE'
crypto = 'PERL/BTC'
# exchange = 'BITMEX'
# crypto = 'BTC'
cry = Crypto(exchange=exchange, crypto=crypto, period='1h', indexes=True)
cry.update_crypto()
df = cry.load_crypto(limit=2400)
refresh = {'1m': 60, '1h': 240, '1d': 400}
# diap_days = 10

refr = 120
maxvols_g = 4
act_g = 'Close'

app = dash.Dash()
app.layout = html.Div([
    html.Div([
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
    # html.Label('Дни'),
    html.Div([
        dcc.Slider(
            id='Days',
            min=1,
            max=200,
            value=100,
            marks={i: str(i) for i in range(0, 201, 10)},
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
    [Input('Period', 'value'),
     Input('Days', 'value'),
     Input('Act', 'value'),
     Input('Button', 'n_clicks'),
     Input('Maxvols', 'value'),
     Input('interval-component', 'n_intervals')])
def update_graph(period, days, act, but, maxvols, intervals):
    global df, refr, maxvols_g, act_g
    refr = refresh[period]
    bars = days
    sbars = 1
    if period == '1h':
        # days = days if days < 60 else 60
        bars = days * 24
        sbars = 24
    elif period == '1m':
        sbars = 1440
        days = days if days < 30 else 30
        bars = days * 1440
    if maxvols == maxvols_g and act == act_g:
        cry.period = period
        cry.update_crypto()
        df = cry.load_crypto(limit=bars)
    maxvols_g = maxvols
    act_g = act
    maxv = df['Volume'].nlargest(maxvols).index
    df_last = df[act][-1]
    df['lsl'] = df[act] - df_last
    df['ls_color'] = df['lsl'].where(df['lsl'] >= 0, 'blue').where(df['lsl'] < 0, 'red')
    Voll = df['Volume'][maxv][df['lsl'] < 0].sum()
    Vols = df['Volume'][maxv][df['lsl'] >= 0].sum()
    Price_max = df[act].max()
    Price_min = df[act].min()
    grid = (Price_max - Price_min) / 100
    df['Prof_Act'] = df[act] // grid * grid
    dfg = df[df['Volume'] >= df['Volume'].max() * 0.5].groupby(['Prof_Act']).sum()
    print(df['Volume'][maxv].apply(lambda x: int(x/df['Volume'][maxv].max()*20)))
    fig = make_subplots(rows=1, cols=2, specs=[[{}, {}]], shared_xaxes=False,
                        shared_yaxes=True, vertical_spacing=0.001, horizontal_spacing=0.01, column_widths=[0.8, 0.2])
    # Grafik
    # fig.add_trace(
    #     go.Scatter(
    #         x=df.index, y=df[act], mode='lines+markers',
    #         hovertext=df['Volume']//1e6,
    #         line=dict(
    #             width=1,
    #             color='grey',
    #         ),
    #         marker=dict(
    #             size=2,
    #             color=df.Volume,
    #             # colorscale='YlOrRd',
    #             colorscale='YlGnBu',
    #             # colorscale='Bluered',
    #             autocolorscale=False,
    #             # line=dict(color='black', width=1)
    #             line=dict(color=df.Volume, width=2)
    #         ),
    #         showlegend=False
    #     ),1,1,
    # )
    # Grafik Candelstik
    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df['Open'], close=df['Close'], high=df['High'], low=df['Low'],
            increasing_line_color='blue', decreasing_line_color='red',
            showlegend=False
        ), 1, 1,
    )
    # SMA(30)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=SMA(df[act], 30 * sbars), mode='lines',
            line=dict(
                width=2,
                color='blue',
            ),
            showlegend=False
        ), 1, 1,
    )
    # SMA(60)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=SMA(df[act], 60 * sbars), mode='lines',
            line=dict(
                width=2,
                color='red',
            ),
            showlegend=False
        ), 1, 1,
    )
    # Hor Vol
    if not dfg.empty:
        fig.add_trace(go.Bar(
            x=dfg['Volume'],
            y=dfg.index,
            orientation='h',
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
        ), 1, 1)
    # Level price
    fig.add_trace(
        go.Scatter(
            x=[df.index[-1] for i in range(maxvols)],
            y=df[act][maxv],
            text=df[act][maxv],
            textposition="top right",
            mode="text",
            showlegend=False
        ), 1, 1)
    # Vol Flash
    fig.add_trace(
        go.Scatter(
            x=[maxv[i] for i in range(maxvols)],
            y=df[act][maxv],
            marker=dict(
                size=df['Volume'][maxv].apply(lambda x: int(x/df['Volume'][maxv].max()*30)),
                color='yellow',
                # color=df.Volume[maxv],
                # colorscale='YlOrRd',
                # colorscale='YlGnBu',
                # colorscale='Bluered',
                # autocolorscale=False,
                # line=dict(color='black', width=1)
                line=dict(color=df.Volume, width=1)
            ),
            mode='markers',
            # text=df[act][maxv],
            # textposition="top right",
            # mode="text",
            showlegend=False
        ), 1, 1)
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
        title=f"Crypto-flash1 {exchange} {crypto} {bars}:{period} {days}:D  SMA(30+60) Vol V:{Vols:,.0f} Vol ^:{Voll:,.0f}",
        xaxis_title="Время",
        yaxis_title=f"{crypto}",
        height=700,
        xaxis_rangeslider_visible=False,
        font=dict(
            family="Courier New, monospace",
            size=9,
            color="blue"
        )
    )
    return fig


if __name__ == '__main__':
    app.run_server(port=8051, debug=True, use_reloader=True)
