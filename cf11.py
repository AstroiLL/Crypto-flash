#!/usr/bin/env python
import pandas as pd
# from pandas import DataFrame
# import numpy as np
# from datetime import datetime as dt
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
# import plotly.io as pio

from DiLL.crypto import Crypto
from DiLL.utils import hd, HA, vwap, vwapi

cry_1h = Crypto(verbose=False)
df_exch = cry_1h.get_list_exch()
cry_1h.connect(exchange='BITMEX', crypto='BTC/USD', period='1h')
cry_1h.update_crypto()
cry_1h.load_crypto(limit=168)
# print(df_1h.info())

cry_1m = Crypto(verbose=False)
cry_1m.connect(exchange='BITMEX', crypto='BTC/USD', period='1m')
cry_1m.update_crypto()
cry_1m.load_crypto(limit=168*60)
# print(df_1m.info())

# refresh = {'1m': 60, '1h': 240, '1d': 400}

# refr = 120
vol_lev = 0.4

app = dash.Dash()
app.layout = html.Div([
    html.Div([
        # dcc.RadioItems(
        #     id='Period',
        #     options=[{'label': i, 'value': i} for i in ['1d', '1h', '1m']],
        #     value='1h', persistence=True, persistence_type='local',
        # ),
        # html.Label('Type graph '),
        dcc.RadioItems(
            id='Act',
            options=[{'label': i, 'value': i} for i in ['Candle', 'Heiken']],
            value='Heiken', persistence=True, persistence_type='local',
        ),
        # html.Label('Volume level '),
        dcc.Slider(
            id='VolLevel',
            min=200,
            max=500,
            value=300,
            marks={f'{i}': f'{i}M' for i in range(200, 500, 20)},
            step=20,
            tooltip={'always_visible': True, 'placement': 'bottom'},
            persistence=True, persistence_type='local',
        ),
    ],
        # style={'columnCount': 2}
    ),
    html.Br(),
    html.Br(),
    # html.Hr(),
    html.Div([
        dcc.Slider(
            id='Hours',
            min=5,
            max=24 * 7,
            value=48,
            marks={**{f'{6 * i}': f'{6 * i}h' for i in range(1, 4)}, **{f'{24 * i}': f'{i}D' for i in range(1, 8)}},
            step=1,
            tooltip={'always_visible': True, 'placement': 'bottom'}, persistence=True, persistence_type='local',
        )
    ]),
    dcc.Interval(
        id='interval-component',
        interval=60 * 1000,  # in milliseconds
        n_intervals=0
    ),
    html.Br(),
    html.Br(),
    # html.Hr(),
    html.Div([
        html.Button('Refresh', id='Button')
    ], style={'display': 'block', 'margin-left': 'calc(50% - 110px)'}),
    html.Div(id='output-state'),
    html.Div([dcc.Graph(id='out')])
])


@app.callback(
    Output('output-state', 'children'),
    [Input('Button', 'n_clicks'),
     Input('interval-component', 'n_intervals')])
def update_df(but, intervals):
    cry_1h.update_crypto()
    cry_1h.load_crypto(limit=168)
    cry_1m.update_crypto()
    cry_1m.load_crypto(limit=168*60)
    return


@app.callback(
    Output('out', 'figure'),
    [Input('Hours', 'value'),
     Input('VolLevel', 'value'),
     Input('Act', 'value'),
     Input('Button', 'n_clicks'),
     Input('interval-component', 'n_intervals')])
def update_graph(hours, lev, act, but, intervals):
    # global refr
    # refr = refresh['1h']
    # print('update_graph', but, intervals)
    bars = hours
    df = cry_1h.df
    lev *= 1e6
    vwap_info_w = '1W'
    vwap_info_d = '1D'
    vwap_info_i = 12
    df = vwap(df, period=vwap_info_w)
    df = vwap(df, period=vwap_info_d)
    df = vwap(df, period=vwap_info_i)
    # print(df)

    df['lsl'] = df['Open'] - cry_1m.df['Close'][-1]
    df['ls_color'] = df['lsl'].where(df['lsl'] >= 0, 'blue').where(df['lsl'] < 0, 'red')
    vol_l = df['Volume'][df['lsl'] < 0].sum()
    vol_s = df['Volume'][df['lsl'] >= 0].sum()

    df = df[-hours:]

    maxv = df[df['Volume'] >= lev].index
    # print(len(maxv))
    df['rank'] = df['Volume'][maxv].rank()
    # берем из массива минут, группируем по часам, находим в каждом часе индекс максимума и
    # Open максимума этого часа прописываем в Open_max массива часов
    # TODO добавить время всплеска объема
    df['Open_max'] = cry_1m.df['Open'][cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax()].resample('1h').mean()
    # print(df['Open_max'][maxv])
    #  TODO dfg исправить
    grid = (df['Open_max'].max() - df['Open_max'].min()) / 100
    df['Prof_Act'] = df['Open_max'] // grid * grid
    dfg = df[df['Volume'] >= df['Volume'].max() * vol_lev].groupby(['Prof_Act']).sum()
    fig = make_subplots(rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": False}]], shared_xaxes=True,
                        shared_yaxes=True, vertical_spacing=0.001, horizontal_spacing=0.01, column_widths=[0.9, 0.1])
    # Grafik Candlestik
    df_ha = HA(df)
    df_act = df if act == 'Candle' else df_ha
    # print(maxv)
    fig.add_trace(
        go.Candlestick(
            x=df_act.index, open=df_act['Open'], close=df_act['Close'], high=df_act['High'], low=df_act['Low'],
            increasing=dict(line=dict(color='blue', width=1)),
            decreasing=dict(line=dict(color='red', width=1)),
            showlegend=False,
            opacity=0.4
        ), 1, 1, secondary_y=False,
    )
    fig.add_trace(
        go.Candlestick(
            x=maxv, open=df_act['Open'][maxv], close=df_act['Close'][maxv], high=df_act['High'][maxv], low=df_act['Low'][maxv],
            increasing=dict(line=dict(color='green', width=3)),
            decreasing=dict(line=dict(color='purple', width=3)),
            showlegend=False,
            opacity=1
        ), 1, 1, secondary_y=False,
    )
    # VWAP(1W)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[f'vwap_{vwap_info_w}'], mode='markers', name=f'VWAP({vwap_info_w})',
            marker=dict(
                # width=2,
                color='purple',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # if period == '1h' or period == '1m':
    # VWAP(1D)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[f'vwap_{vwap_info_d}'], mode='markers', name=f'VWAP({vwap_info_d})',
            marker=dict(
                # width=2,
                color='black',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # VWAP(i)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[f'vwap_{vwap_info_i}'], mode='markers', name=f'VWAP({vwap_info_i})',
            marker=dict(
                # width=1,
                color='yellow',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # Vert Vol
    if True:
        fig.add_trace(
            go.Bar(x=df.index, y=df['Volume'].where(df['Volume'] >= lev*0.8, 0), name='VolV',
                   marker=dict(color='grey'), showlegend=True, opacity=0.2,
                   # width=3000000
                   ),
            row=1, col=1, secondary_y=True)
    # Hor Vol
    if dfg.shape[0] > 1:
        fig.add_trace(go.Bar(
            x=dfg['Volume'],
            y=dfg.index,
            orientation='h',
            # marker=dict(color='blue'),
            name='VolH',
            showlegend=False,
            marker_color=dfg['Volume'],
            # texttemplate='%{x}', textposition='outside',
            # width=10
        ), 1, 2
        )
    # End price
    fig.add_trace(
        go.Scatter(
            x=[cry_1m.df.index[-1]],
            y=[cry_1m.df['Close'][-1]],
            text=f"{cry_1m.df['Close'][-1]}",
            textposition="middle right",
            mode="text+markers",
            showlegend=False,
        ), 1, 1, secondary_y=False)
    # Level price
    fig.add_trace(
        go.Scatter(
            x=[df.index[-1] for _ in range(len(maxv))],
            y=df['Open_max'][maxv],
            text=df['Open_max'][maxv],
            textposition="top right",
            mode="text",
            showlegend=False
        ), 1, 1, secondary_y=False)
    # Vol Flash
    fig.add_trace(
        go.Scatter(
            x=[maxv[i] for i in range(len(maxv))],
            y=df['Open_max'][maxv],
            marker=dict(
                size=(df['Volume'][maxv] / df['Volume'][maxv].max() * 30).astype('int64'),
                # size=df_1h['Volume'][maxv].rank()*5,
                color=df['ls_color'][maxv],
                line=dict(color=df.Volume, width=1)
            ),
            mode='markers',
            # text=df_1h['Open'][maxv],
            # textposition="top right",
            # mode="text",
            showlegend=False
        ), 1, 1, secondary_y=False)
    # Line
    [fig.add_shape(
        dict(
            type="line", xref='x', yref='y', x0=maxv[i], x1=df.index[-1],
            y0=df['Open_max'][maxv][i], y1=df['Open_max'][maxv][i],
            line=dict(color=df['ls_color'][maxv][i], width=df['rank'][maxv][i])
        )
    ) for i in range(len(maxv))]
    # Levels
    [fig.add_annotation(
        dict(
            x=maxv[i],
            y=df['Open_max'][maxv][i],
            xref="x",
            yref="y",
            text=f"V:{df['Volume'][maxv][i]:,.0f}",
            hovertext=f"{df['Open_max'][maxv][i]}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            ax=-40,
            ay=-40
        )
    ) for i in range(len(maxv))]
    voldir = vol_l - vol_s
    dirs = '^' if voldir >= 0 else 'v'
    fig.update_layout(
        title=f"Crypto-flash-11 BITMEX BTC/USD {bars}h {dirs} {hd(voldir,sign=True)} {hd(lev, precision=0)} {intervals}",
        xaxis_title="Date",
        yaxis_title=f"BTC/USD",
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
    # pio.write_image(fig=fig, file=f'btc{intervals}.jpg', format='jpg')
    # pio.write_json(fig=fig, file=f'btc{intervals}.json', pretty=True)
    return fig


if __name__ == '__main__':
    app.run_server(port=8051, debug=True, use_reloader=True)
