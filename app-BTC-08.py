# Plotly Dash #13
import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output

from MLDiLL.cryptoA import CryptoA
from MLDiLL.utils import hd, wvwma, sma

# TODO линии по списку с сохранением и фильтрацией
# TODO сохранение параметров
# TODO лента объемов вокруг SMA шириной в зависимости от объема

# READ DATA

PERIOD = '1m'
LIMIT = 800
WVW = 24
VERSION = 'BTC Splash #08'
cry = CryptoA(period=PERIOD, verbose=False)
cry.load(limit=LIMIT)

# create category
# bins = [0, 0.8, 1.2, 100]
# names = ['small', 'similar', 'bigger']
# df['StarSize'] = pd.cut(df['RSTAR'], bins, labels=names)

# LAYOUT

# Global design set
CHARTS_TEMPLATE = go.layout.Template(
    layout=dict(
        font=dict(
            family='Roboto',
            size=10
        ),
        legend=dict(
            orientation='h',
            title_text='',
            x=0,
            y=1.1
        ),
        xaxis_title="Date",
        yaxis_title=f"{cry.crypto}",
        # height=650,
        height=700,
        # width=1400,
        xaxis_rangeslider_visible=False,
        # legend_orientation="h",
        # legend=dict(x=0, y=1, orientation='h'),
        hovermode="x unified",
        # hoverlabel_align='right',
        # margin={"r": 0, "t": 1, "l": 0, "b": 0},
        transition_duration=500

    )
)

options = [{'label': i, 'value': i} for i in [15, 30, 60, 120, 240]]
wvwma_selector = html.Div(
    [
        dbc.Label("WVWMA"),
        dcc.Dropdown(
            id='wvwma-selector',
            options=options,
            value=[],
            multi=True,
            persistence=True, persistence_type='local',
        )]
)
sma_selector = html.Div(
    [
        dbc.Label("SMA"),
        dcc.Dropdown(
            id='sma-selector',
            options=options,
            value=[],
            multi=True,
            persistence=True, persistence_type='local',
        )]
)

vol_level_selector = dcc.RangeSlider(
    id='vol-level-slider',
    min=0,
    max=100,
    value=[25, 50],
    # allowCross=False,
    # pushable=1000000,
    tooltip={'always_visible': True, 'placement': 'bottom'},
    persistence=True, persistence_type='local',
)

price_line = html.Div(
    [
        dbc.Switch(
            id="price-line",
            label="Цена",
            value=True,
            persistence=True, persistence_type='local',
        ),
    ]
)

price_sma = html.Div(
    [
        dbc.Switch(
            id="price-sma",
            label="SMA цены",
            value=True,
            persistence=True, persistence_type='local',
        ),
    ]
)

price_max_vol = html.Div(
    [
        dbc.Switch(
            id="price-max-vol",
            label="Max Volume",
            value=True,
            persistence=True, persistence_type='local',
        ),
    ]
)

sma_period = dbc.Input(
    id='sma-period', type="number", step=1, value=2, min=1, max=30, persistence=True, persistence_type='local'
)

interval_reload = dcc.Interval(
    id='interval-reload',
    interval=60000,  # in milliseconds
    n_intervals=0
)

app = dash.Dash(
    __name__, external_stylesheets=[dbc.themes.FLATLY]
)

app.layout = html.Div(
    [
        interval_reload,
        dbc.Row(
            html.H1(VERSION),
            style={'margin-bottom': 40}
        ),
        dbc.Row(
            [
                dbc.Col(wvwma_selector),
                dbc.Col(sma_selector),
            ],
            style={'margin-bottom': 40}
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Loading(dbc.Button('Refresh', id="refresh", color="primary", outline=True)), width=1),
                dbc.Col(html.Div(id='out-btc')),
                # dbc.Col(dbc.Button('-', id="refresh", color="primary", outline=True), width=1),
                # dbc.Col(dcc.Loading(html.Div(id='out-btc'))),
                dbc.Col(price_line, width=0),
                dbc.Col(sma_period, width=0),
                dbc.Col(price_sma, width=0),
                dbc.Col(price_max_vol, width=0),
            ],
            style={'margin-bottom': 40}
        ),
        dbc.Row(
            [
                html.Div(vol_level_selector),
                html.Div(id='btc-chart')
            ],
            style={'margin-bottom': 40}
        )
    ],
    style={'margin-left': '80px', 'margin-right': '80px'}
)

""" CALLBACK """


@app.callback(
    Output('refresh', 'children'),
    Input('refresh', 'n_clicks'),
    Input('interval-reload', 'n_intervals'),
)
def update_df(n, nn):
    cry.load(limit=LIMIT)
    return 'Refresh'
    # , cry.maxV
    # , [cry.maxV*0.5, cry.maxV*0.75]


@app.callback(
    Output('btc-chart', 'children'),
    Output('out-btc', 'children'),
    Input('refresh', 'n_clicks'),
    Input('vol-level-slider', 'value'),
    Input('interval-reload', 'n_intervals'),
    Input('wvwma-selector', 'value'),
    Input('sma-selector', 'value'),
    Input('price-line', 'value'),
    Input('sma-period', 'value'),
    Input('price-sma', 'value'),
    Input('price-max-vol', 'value'),
)
def update_chart(n, range_vol_level, nn, wvwma_select, sma_select, price_line, sma_period, price_sma, price_max_vol):
    if cry.df.empty:
        raise dash.exceptions.PreventUpdate
        # cry.load(limit=LIMIT)
    df = cry.df
    # print(df)
    maxV = cry.maxV
    # range_open = {'min': df['Open'].min(), 'max': df['Open'].max()}
    vol_level0 = (range_vol_level[0]*maxV)/100
    vol_level1 = (range_vol_level[1]*maxV)/100
    # Фильтровать по критерию Vol >= уровень
    df['max_vol'] = 0
    df['max_vol'] = df['max_vol'].where(df['Volume'] < vol_level0, 13).where(df['Volume'] < vol_level1, 21)
    big_max_vol = df[df['max_vol'] == 21][['max_vol', 'Open']]
    # count_big_max_vol = big_max_vol['max_vol'].count()
    # print(big_max_vol['Open'].values)
    df['max_vol_color'] = 'gray'
    df['max_vol_color'] = df['Open'].where(df['Open'] >= df['Close'], 'blue').where(df['Open'] < df['Close'], 'red')
    out_btc = f"Max Vol: {hd(maxV)} Vol0: {hd(vol_level0)} {round((vol_level0 / maxV) * 100)} %" \
              f" Vol1: {hd(vol_level1)} {round((vol_level1 / maxV) * 100)} %"
    Max_Vol = df['max_vol'] >= 13
    dfv = df[Max_Vol]
    for wvw in wvwma_select:
        df[f'wvwma_{wvw}'] = wvwma(df['Open'], df['Volume'], length=wvw)
    for s in sma_select:
        df[f'sma_{s}'] = sma(df['Open'], length=s)
    # Price SMA
    df['sma'] = sma(df['Open'], length=sma_period)
    fig = go.Figure()
    # Price line
    if price_line:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['Open'],
                name='Price',
                mode='lines',
                line=dict(
                    # size=1,
                    color='grey',
                ),
            )
        )
    # Max Vol
    if price_max_vol:
        fig.add_trace(
            go.Scatter(
                x=dfv.index, y=dfv['Open'],
                name='Max Vol',
                mode='markers',
                marker=dict(
                    size=dfv['max_vol'],
                    color=dfv['max_vol_color'],
                ),
            )
        )
    # WVWMA()
    for wvw in wvwma_select:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df[f'wvwma_{wvw}'], mode='lines', name=f'WVWMA({wvw})',
                # hoverinfo='none',
                # line=dict(
                # size=4,
                # color='black',
                # ),
                showlegend=True
            )
        )
    # Price SMA
    if price_sma:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['sma'], mode='lines', name=f'Price SMA',
                # hoverinfo='none',
                line=dict(
                    width=1,
                    color='black',
                ),
                showlegend=True
            )
        )
    # SMA_X
    for s in sma_select:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df[f'sma_{s}'], mode='markers', name=f'SMA({s})',
                # hoverinfo='none',
                marker=dict(
                    # width=2,
                    # color='black',
                ),
                showlegend=True
            )
        )
    # Indicator
    end_vol = df['Volume'][-1]
    pre_end_vol = df['Volume'][-2]
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=end_vol,
            number={'prefix': "Vol:"},
            delta={'position': "top", 'reference': pre_end_vol},
            domain={'x': [0, 0], 'y': [0, 0]},
            # showlegend=True,
        )
    )
    # End price
    end_price = df['Close'][-1]
    fig.add_trace(
        go.Scatter(
            x=[df.index[-1]],
            y=[end_price],
            text=f" {end_price}",
            name='EndPrice',
            textposition="middle right",
            mode="text+markers",
            marker=dict(color='black', size=12, symbol='star'),
            showlegend=True,
            hovertemplate=f"{end_price}"
        )
    )
    # H lines
    for i in big_max_vol['Open']:
        fig.add_hline(
            y=i, line_dash="dot",
            annotation_text=i,
            annotation_position="top right"
        )
    # fig.add_hline(
    #     y=40000, line_dash="dash", exclude_empty_subplots=False,
    #     annotation_text='Test1',
    #     annotation_position="top right"
    #     )

    fig.update_layout(template=CHARTS_TEMPLATE)
    html1 = [html.Div('BTC/USD ' + PERIOD, className='header_plots'),
             dcc.Graph(figure=fig)]

    return html1, out_btc


if __name__ == '__main__':
    app.run_server(port=8053, debug=True)
