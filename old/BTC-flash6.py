#!/usr/bin/env python
# import pandas as pd
# from pandas import DataFrame
# import numpy as np
# from datetime import datetime as dt
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash.dependencies import Input, Output

from DiLL.bitmex import BTC


btc = BTC(period='1h', indexes=True)
btc.update_btc()
df = btc.load_btc(limit=200)
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
            max=100,
            value=10,
            marks={i: str(i) for i in range(0, 101, 10)},
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
    if maxvols == maxvols_g and act == act_g:
        if period == '1h':
            # days = days if days < 60 else 60
            bars = days*24
        elif period == '1m':
            days = days if days < 7 else 7
            bars = days*1440
        btc.period = period
        btc.update_btc()
        df = btc.load_btc(limit=bars)
    maxvols_g = maxvols
    act_g = act
    maxv = df['Volume'].nlargest(maxvols).index
    df_last = df[act][0]
    df['lsl'] = df[act]-df_last
    df['ls_color'] = df['lsl'].where(df['lsl'] >= 0, 'blue').where(df['lsl'] < 0, 'red')
    Voll = df['Volume'][maxv][df['lsl'] < 0].sum()
    Vols = df['Volume'][maxv][df['lsl'] >= 0].sum()
    V_max = df['Close'].max()
    V_min = df['Close'].min()
    grid = int((V_max-V_min)/100)
    df['Prof_Close'] = df['Close'] // grid * grid
    dfg = df[df['Volume'] >= df['Volume'].max()*0.5].groupby(['Prof_Close']).sum()
    # fig = go.Figure()
    fig = make_subplots(rows=1, cols=2, specs=[[{}, {}]], shared_xaxes=False,
                        shared_yaxes=True, vertical_spacing=0.001, horizontal_spacing=0.01, column_widths=[0.8, 0.2])
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[act], mode='lines+markers',
            hovertext=df['Volume']//1e6,
            line=dict(
                width=1,
                color='grey',
            ),
            marker=dict(
                size=2,
                color=df.Volume,
                # colorscale='YlOrRd',
                colorscale='YlGnBu',
                # colorscale='Bluered',
                autocolorscale=False,
                # line=dict(color='black', width=1)
                line=dict(color=df.Volume, width=2)
            ),
            showlegend=False
        ),1,1,
    )
    fig.add_trace(go.Bar(
        x=dfg['Volume'],
        y=dfg.index,
        orientation='h',
        showlegend=False
        ),1,2
    )
    fig.add_trace(
        go.Scatter(
            x=[df.index[0]],
            y=[df[act][0]],
            text=df[act][0],
            textposition="top right",
            mode="text",
            showlegend=False,
    ),1,1)
    fig.add_trace(
        go.Scatter(
            x=[df.index[0] for i in range(maxvols)],
            y=df[act][maxv],
            text=df[act][maxv],
            textposition="top right",
            mode="text",
            showlegend=False
        ),1,1)
    [fig.add_shape(
        dict(
            type="line", xref='x', yref='y', x0=maxv[i], x1=df.index[0],
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
            hovertext=f"{df[act][maxv][i]:.1f}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            ax=-40,
            ay=-40
        )
    ) for i in range(maxvols)]
    fig.update_layout(
        title=f"BTC6 {bars}:{period} {days}:D  Vol V:{Vols:,.0f} Vol ^:{Voll:,.0f}",
        xaxis_title="Время",
        yaxis_title="BTC",
        height=700,
        font=dict(
            family="Courier New, monospace",
            size=18,
            color="blue"
        )
    )
    return fig


if __name__ == '__main__':
    app.run_server(port=8056, debug=True, use_reloader=True)
