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
from DiLL.utils import hd, HA, vwap

cry_1h = Crypto(verbose=True)
df_exch = cry_1h.get_list_exch()
cry_1h.connect(exchange='BITMEX', crypto='BTC/USD', period='1h')
cry_1h.update_crypto()
df_1h = cry_1h.load_crypto(limit=168)
start = False
print(df_1h.info())

refresh = {'1m': 60, '1h': 240, '1d': 400}

refr = 120
vol_lev = 0.4

app = dash.Dash()
app.layout = html.Div([
    # TODO починить сохранение сессии
    # dcc.Store(id='Global', data={'act_g': 'Heiken', 'maxvols_g': 4}, storage_type='local'),
    html.Details([
        html.Summary('Select crypto', style={"font-size": "22"}),
        html.Div([
            dcc.RadioItems(
                id='Crypto',
                options=[{'label': i, 'value': i} for i in df_exch['Crypto']],
                value='BTC/USD', persistence=True, persistence_type='local', labelStyle={'display': 'inline-block'}
            ),
            dcc.Input(id='new_crypto', persistence=True, persistence_type='local', debounce=True, value='',
                      type='text'),
        ]),
    ]),
    html.Div([
        dcc.RadioItems(
            id='Period',
            options=[{'label': i, 'value': i} for i in ['1d', '1h', '1m']],
            value='1h', persistence=True, persistence_type='local',
        ),
        dcc.RadioItems(
            id='Act',
            options=[{'label': i, 'value': i} for i in ['Candle', 'Heiken']],
            value='Heiken', persistence=True, persistence_type='local',
        ),
        html.Label('Number of peaks '),
        dcc.Input(
            id="Maxvols",
            type="number",
            placeholder="Number of peaks",
            value=4,
            min=0, persistence=True, persistence_type='local',
        ),
    ], style={'columnCount': 3}),
    html.Div([
        dcc.Slider(
            id='Hours',
            min=4,
            max=24 * 7,
            value=48,
            marks={**{f'{6 * i}': f'{6 * i}h' for i in range(1, 4)}, **{f'{24 * i}': f'{i}D' for i in range(1, 8)}},
            step=1,
            tooltip={'always_visible': True, 'placement': 'bottom'}, persistence=True, persistence_type='local',
        )
    ]),
    dcc.Interval(
        id='interval-component',
        interval=refr * 1000,  # in milliseconds
        n_intervals=0
    ),
    html.Br(),
    html.Hr(),
    html.Div([
        html.Button('Refresh', id='Button')
    ], style={'display': 'block', 'margin-left': 'calc(50% - 110px)'}),
    html.Div([dcc.Graph(id='out')])
])


@app.callback(
    # TODO сделать разные callback's
    Output('out', 'figure'),
    [Input('Hours', 'value'),
     Input('Act', 'value'),
     Input('Button', 'n_clicks'),
     Input('Maxvols', 'value'),
     Input('interval-component', 'n_intervals')])
def update_graph(hours, act, but, maxvols, intervals):
    global refr, start
    refr = refresh['1h']
    bars = hours
    df = cry_1h.df
    vwap_info_w = '1W'
    vwap_info_d = '1D'
    df = vwap(df, vwap_info_w)
    df = vwap(df, vwap_info_d)
    df = df[-hours:]
    df['lsl'] = df['Open'] - df['Open'][-1]
    df['ls_color'] = df['lsl'].where(df['lsl'] >= 0, 'blue').where(df['lsl'] < 0, 'red')
    vol_l = df['Volume'][df['lsl'] < 0].sum()
    vol_s = df['Volume'][df['lsl'] >= 0].sum()
    grid = (df['Open'].max() - df['Open'].min()) / 100
    df['Prof_Act'] = df['Open'] // grid * grid
    maxv = df['Volume'].nlargest(maxvols).index
    df['rank'] = df['Volume'][maxv].rank()
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
            decreasing=dict(line=dict(color='green', width=3)),
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
    # Vert Vol
    # if False:
    #     fig.add_trace(
    #         go.Bar(x=df_1h.index, y=df_1h['Volume'].where(df_1h['Volume'] >= df_1h['Volume'].max() * vol_lev, 0), name='VolV',
    #                marker=dict(color='black'), showlegend=True, opacity=0.7, width=4000000),
    #         row=1, col=1, secondary_y=True)
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
            x=[df.index[-1]],
            y=[df['Open'][-1]],
            text=df['Open'][-1],
            textposition="top right",
            mode="text",
            showlegend=False,
        ), 1, 1, secondary_y=False)
    # Level price
    fig.add_trace(
        go.Scatter(
            x=[df.index[-1] for _ in range(maxvols)],
            y=df['Open'][maxv],
            text=df['Open'][maxv],
            textposition="top right",
            mode="text",
            showlegend=False
        ), 1, 1, secondary_y=False)
    # Vol Flash
    fig.add_trace(
        go.Scatter(
            x=[maxv[i] for i in range(maxvols)],
            y=df['Open'][maxv],
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
            y0=df['Open'][maxv][i], y1=df['Open'][maxv][i],
            line=dict(color=df['ls_color'][maxv][i], width=df['rank'][maxv][i])
        )
    ) for i in range(maxvols)]
    # Levels
    [fig.add_annotation(
        dict(
            x=maxv[i],
            y=df['Open'][maxv][i],
            xref="x",
            yref="y",
            text=f"V:{df['Volume'][maxv][i]:,.0f}",
            hovertext=f"{df['Open'][maxv][i]}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            ax=-40,
            ay=-40
        )
    ) for i in range(maxvols)]
    voldir = vol_l - vol_s
    dirs = '^' if voldir >= 0 else 'v'
    fig.update_layout(
        title=f"Crypto-flash9 BITMEX BTC/USD {bars}h {dirs} {hd(voldir,sign=True)} {but} {intervals}",
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
    return fig


if __name__ == '__main__':
    app.run_server(port=8051, debug=True, use_reloader=True)
