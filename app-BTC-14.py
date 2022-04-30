import dash_bootstrap_components
import plotly
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from dash.long_callback import DiskcacheLongCallbackManager
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from plotly.subplots import make_subplots

from MLDiLL.cryptoA import CryptoA
from MLDiLL.utils import hd, wvwma, sma
from db.db_btc import Db, BTC
from sqlalchemy import select

# Diskcache
import diskcache

cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

# TODO VOL-MAX на графике SMA
# TODO линия позиции
# READ DATA

PERIOD = '1m'
# LIMIT = 800
WVW = 24
VER_P = plotly.__version__
VER_D = dash.__version__
VER_B = dash_bootstrap_components.__version__
VERSION = f'BTC Splash #14, Plotly V{VER_P}, Dash V{VER_D}, Bootstrap V{VER_B}'

# Открытие базы всплесков объемов
db = Db('sqlite', '/home/astroill/Data/CF/btc_max_more_10.db')

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
            y=1
        ),
        # height=650,
        height=800,
        # width=1400,
        # xaxis_rangeslider_visible=True,
        xaxis_showspikes=True,
        # yaxis_showspikes=True,
        # legend_orientation="h",
        # legend=dict(x=0, y=1, orientation='h'),
        # hovermode="x unified",
        # hoverlabel_align='right',
        # margin={"r": 0, "t": 1, "l": 0, "b": 0},
        transition_duration=500

    )
)

options = [{'label': i, 'value': i} for i in [15, 30, 60, 120, 240]]
wvwma_selector = html.Div(
    [
        # "WVWMA",
        dcc.Dropdown(
            id='wvwma-selector',
            options=options,
            value=[],
            multi=True,
            persistence=True, persistence_type='local',
        )]
)
position = html.Div(
    [
        dbc.Input(
            id='position', placeholder='position price', type="number", min=0, persistence=True,
            persistence_type='local', debounce=True
        )], hidden=False
)
pos = html.Div(
    [
        dbc.Switch(
            id="pos",
            label="Позиция",
            value=False,
            persistence=True, persistence_type='local',
        ),
    ]
)

vol_level_selector = dcc.RangeSlider(
    id='vol-level-slider',
    min=0,
    max=100,
    value=[25, 50],
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

aggr_max_vol = html.Div(
    [
        dbc.Switch(
            id="aggr-max-vol",
            label="Aggr Max Volume",
            value=True,
            persistence=True, persistence_type='local',
        ),
    ]
)

sma_period_price = dbc.Input(
    id='sma-period-price', placeholder='period price', type="number", step=1, min=1, max=30, persistence=True,
    persistence_type='local'
)

all_period = dbc.Input(
    id='all-period', placeholder='all period', type="number", step=60, min=60, persistence=True,
    persistence_type='local', debounce=True, inputmode='numeric',
)

sma_period_vol = html.Div(
    [

        dbc.Input(
            id='sma-period-vol', placeholder='period vol', type="number", step=1, min=1, max=30, persistence=True,
            persistence_type='local'
        )
    ]
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
        dcc.Store(id='df', storage_type='local'),
        interval_reload,
        dbc.Row(
            [
                dbc.Col(html.H3(VERSION)),
                dbc.Col(html.Div(id='out-btc')),

            ],
            # style={'margin-bottom': 10}
        ),
        dbc.Row(
            [
                'Period:',
                dbc.Col(all_period),
                "WVWMA:",
                dbc.Col(wvwma_selector),
                'Pos:',
                dbc.Col(position),
                dbc.Col(pos),
            ],
            style={'margin-bottom': 10}
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Loading(dbc.Button('Refresh', id="refresh", color="primary", outline=True)), width=1),
                dbc.Col(price_line, width=0),
                'SMA Vol:',
                dbc.Col(sma_period_vol, width=0),
                'SMA Price:',
                dbc.Col(sma_period_price, width=0),
                dbc.Col(price_sma, width=0),
                dbc.Col(price_max_vol, width=0),
                dbc.Col(aggr_max_vol, width=0),
            ],
            # style={'margin-bottom': 40}
        ),
        dbc.Row(
            [
                html.Div(vol_level_selector),
                html.Div(id='btc-chart')
            ],
            # style={'margin-bottom': 40}
        )
    ],
    style={'margin-left': '80px', 'margin-right': '80px'}
)

""" CALLBACK """


@app.long_callback(
    Output('refresh', 'children'),
    Output('df', 'data'),
    Input('all-period', 'value'),
    Input('refresh', 'n_clicks'),
    Input('interval-reload', 'n_intervals'),
    manager=long_callback_manager,
)
def update_df(limit, n, nn):
    cry = CryptoA(period=PERIOD, verbose=False)
    cry.load(limit=limit)
    df = cry.df[['Open', 'Close', 'Volume']]
    return 'Refresh', df.to_json()


@app.callback(
    Output('btc-chart', 'children'),
    Output('out-btc', 'children'),
    Input('df', 'data'),
    Input('refresh', 'n_clicks'),
    Input('vol-level-slider', 'value'),
    Input('interval-reload', 'n_intervals'),
    Input('wvwma-selector', 'value'),
    Input('position', 'value'),
    Input('pos', 'value'),
    Input('price-line', 'value'),
    Input('sma-period-price', 'value'),
    Input('sma-period-vol', 'value'),
    Input('price-sma', 'value'),
    Input('price-max-vol', 'value'),
    Input('aggr-max-vol', 'value'),
)
def update_chart(data, n, range_vol_level, nn, wvwma_select, position, pos, price_line, sma_period_price, sma_period_vol,
                 price_sma,
                 price_max_vol,
                 aggr_max_vol
                 ):
    df = pd.read_json(data)
    if df.empty:
        raise PreventUpdate
    # Получаем из db всплески объемов
    session = db.open()
    stmt = select(BTC)
    # print(stmt)
    # print(pd.read_sql(stmt, con=session.bind))
    # btc_df = pd.read_sql(
    # print(session.query(stmt))
        # , session.bind)
    btc0 = []
    for btc in session.scalars(stmt):
        # print(btc.time, btc.close, btc.vol)
        btc0.append({'time': btc.time, 'close': btc.close, 'vol': btc.vol, 'd': btc.dir})
    # print(btc0)
    btc_df = pd.DataFrame(btc0)
    # btc_df.set_index('time', inplace=True)
    btc_df = btc_df[btc_df.time >= df.index[0]]
    btc_df = btc_df.sort_values(by=['vol'], ascending=False).iloc[0:5, :]
    btc_df = btc_df.sort_values(by=['time'], ascending=True)
    btc_df['col'] = btc_df.d.where(btc_df.d == 0, 'green').where(btc_df.d == 1, 'orange')
    # print(btc_df)
    session.close()

    maxV = df['Volume'].max()
    print(maxV)
    # range_open = {'min': df['Open'].min(), 'max': df['Open'].max()}
    vol_level0 = (range_vol_level[0] * maxV) / 100
    vol_level1 = (range_vol_level[1] * maxV) / 100
    # Фильтровать по критерию Vol >= уровень
    df['max_vol'] = 0
    df['max_vol'] = df['max_vol'].where(df['Volume'] < vol_level0, 13).where(df['Volume'] < vol_level1, 21)
    big_max_vol = df[df['max_vol'] == 21][['Volume', 'max_vol', 'Open']]
    # count_big_max_vol = big_max_vol['max_vol'].count()
    # print(big_max_vol['Open'].values)
    df['max_vol_color'] = 'gray'
    df['max_vol_color'] = df['Open'].where(df['Open'] >= df['Close'], 'blue').where(df['Open'] < df['Close'], 'red')
    out_btc = f"Max Vol: {hd(maxV)} Vol0: {hd(vol_level0)} {round((vol_level0 / maxV) * 100)} %" \
              f" Vol1: {hd(vol_level1)} {round((vol_level1 / maxV) * 100)} %"
    Max_Vol = df['max_vol'] >= 13
    dfv = df[Max_Vol]
    # Price SMA
    df['sma'] = sma(df['Open'], length=sma_period_price)
    # Volume SMA
    df['sma_v'] = sma(df['Volume'], length=sma_period_vol)
    for wvw in wvwma_select:
        df[f'wvwma_{wvw}'] = wvwma(df['Open'], df['Volume'], length=wvw)
        df[f'sma_{wvw}'] = sma(df['Open'], length=wvw)
        df[f'w_s_{wvw}'] = (df[f'wvwma_{wvw}'] - df[f'sma_{wvw}']) / df['sma']
        df[f'o_s_{wvw}'] = (df['sma'] - df[f'sma_{wvw}']) / df['sma']
    # Make Figures
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        row_width=[0.21, 0.33, 0.46],
        start_cell='top-left',
        # vertical_spacing=0.03,
        # print_grid=True,
    )
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
            ), row=1, col=1
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
            ), row=1, col=1
        )
    # Max Vol from aggr
    if aggr_max_vol:
        fig.add_trace(
            go.Scatter(
                x=btc_df.time, y=btc_df.close,
                name='Max Vol aggr',
                mode='markers',
                text=btc_df.vol,
                marker=dict(
                    size=16,
                    color=btc_df.col,
                ),
            ), row=1, col=1
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
            ), row=1, col=1
        )
    # WVWMA, SMA, DIFF
    for wvw in wvwma_select:
        # WVWMA_X
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df[f'wvwma_{wvw}'], mode='lines', name=f'WVWMA({wvw})',
                # hoverinfo='none',
                # line=dict(
                # size=4,
                # color='black',
                # ),
                showlegend=True
            ), row=1, col=1
        )
        # SMA_X
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df[f'sma_{wvw}'], mode='markers', name=f'SMA({wvw})',
                # hoverinfo='none',
                marker=dict(
                    # width=2,
                    # color='black',
                ),
                showlegend=True
            ), row=1, col=1
        )
        # WVWMA-SMA
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df[f'w_s_{wvw}'], mode='lines', name=f'WVWMA(SMA)',
                line=dict(
                    # size=1,
                    color='lime',
                ),
            ), row=2, col=1
        )
        # WVWMA-Open
        if price_sma:
            fig.add_trace(
                go.Scatter(
                    x=df.index, y=df[f'o_s_{wvw}'], mode='lines', name=f'Open(SMA)',
                    line=dict(
                        # size=1,
                        color='grey',
                    ),
                ), row=2, col=1
            )
    fig.add_hline(
        y=0, line_dash="dot",
        annotation_text='SMA',
        annotation_position="top right",
        row=2, col=1
    )
    end_price = df['Close'][-1]
    end_vol = df['Volume'][-1]
    print(end_price, hd(end_vol))
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
        ), row=1, col=1
    )

    # H lines
    for i in big_max_vol['Open']:
        fig.add_hline(
            y=i, line_dash="dot",
            annotation_text=i,
            annotation_position="top right",
            row=1, col=1
        )
    # Position
    if pos:
        fig.add_hline(
            y=position, line_dash="longdash",
            annotation_text=f'Позиция {position}',
            annotation_position="top right",
            # color='blue',
            row=1, col=1
        )
    # Vert Vol
    fig.add_trace(
        go.Bar(
            x=df.index, y=df['Volume'], name='Volume',
            marker=dict(color='grey'), showlegend=True, opacity=0.5,
            # hoverinfo='none'
        ), row=3, col=1
    )
    # Vol SMA
    if price_sma:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['sma_v'], mode='lines', name=f'Vol SMA',
                # hoverinfo='none',
                line=dict(
                    width=1,
                    color='black',
                ),
                showlegend=True
            ), row=3, col=1
        )
    # H lines Vol
    fig.add_hline(
        y=vol_level0, line_dash="dash",
        annotation_text=vol_level0,
        annotation_position="top right",
        row=3, col=1
    )
    fig.add_hline(
        y=vol_level1, line_dash="longdash",
        annotation_text=vol_level1,
        annotation_position="top right",
        row=3, col=1
    )

    fig.update_layout(template=CHARTS_TEMPLATE)
    fig.update_yaxes(
        title='Price',
        row=1, col=1
    )
    fig.update_yaxes(
        title='SMA',
        row=2, col=1
    )
    fig.update_yaxes(
        title='Volume',
        row=3, col=1
    )
    fig.update_xaxes(
        title='Date',
        row=3, col=1
    )

    html1 = [
        html.Div('BTC/USD ' + PERIOD, className='header_plots'),
        dcc.Graph(figure=fig),
    ]

    return html1, out_btc


if __name__ == '__main__':
    app.run_server(port=8052, debug=True)
