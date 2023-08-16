# import dash_bootstrap_components
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
# import plotly.io as pio

from MLDiLL.cryptoA2 import CryptoA
from MLDiLL.utils import hd, wvwma, sma
# from dbiLL.db_btc import Db, BTC
# from sqlalchemy import select

# Diskcache
import diskcache

"""
BTC Bunch of Lines
Серая линия сглаженая коротким периодом цена, для устранения шумов 
SMA (красная линия) показывает сглаженое движение цены
WVWMA (синяя линия) показывает взвешенное по объему движение цены
Пересечение SMA и WVWMA с плавным подбором периода
Когда синяя выше красной, объемы в бай
Когда красная выше синей, объемы в селл
Когда цена выше синей и красной, то приоритет в бай
Когда цена ниже синей и красной, то приоритет в селл
"""
cache = diskcache.Cache("/tmp/ff/cache_bbol_01")
long_callback_manager = DiskcacheLongCallbackManager(cache)

# READ DATA

PERIOD = '1m'
WVW = 24
VER_P = plotly.__version__
VER_D = dash.__version__
VER_B = dbc.__version__
VERSION = f'BTC Bunch of Lines #01, Plotly V{VER_P}, Dash V{VER_D}, Bootstrap V{VER_B}'

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
        height=750,
        xaxis_showspikes=True,
        transition_duration=500,
    )
)

all_period = dbc.Input(  # Выбор периода загрузки данных 1 день
    id='all-period', placeholder='all period', type="number", value=60 * 24, step=60, min=60, persistence=True,
    persistence_type='local', debounce=True, inputmode='numeric',
)

vis_period = dbc.Input(  # Выбор периода отображения 12 часов
    id='vis-period', placeholder='vis period', type="number", value=60 * 12, step=60, min=60, max=1440, persistence=True,
    persistence_type='local', debounce=False, inputmode='numeric',
)

price_line = html.Div(
    [  # Показывать цену
        dbc.Switch(
            id="price-line",
            label="Цена",
            value=False,
            persistence=True, persistence_type='local',
        ),
    ]
)

price_sma = html.Div(
    [  # Показывать SMA цены
        dbc.Switch(
            id="price-sma",
            label="SMA цены",
            value=True,
            persistence=True, persistence_type='local',
        ),
    ]
)

sma_period_price = dbc.Input(  # Период сглаживания SMA цены
    id='sma-period-price', placeholder='period price', type="number", step=1, min=1, max=30, persistence=True,
    persistence_type='local'
)

sma_period_vol = html.Div(
    [  # Период SMA на графике объема
        dbc.Input(
            id='sma-period-vol', placeholder='period vol', type="number", step=1, min=1, max=30, persistence=True,
            persistence_type='local'
        )
    ]
)

marks = {i: j for i, j in
         [(60, '1h'), (120, '2h'), (240, '4h'), (480, '8h'), (720, '12h'), (1080, '18h'), (1440, '1D')]}
sma_level_selector = dcc.Slider(  # Слайдер уровня SMA
    id='sma-level-slider',
    # min=60,
    # max=720,
    # value=60,
    step=None,
    marks=marks,
    tooltip={'always_visible': True, 'placement': 'bottom'},
    persistence=True, persistence_type='local',
)

interval_reload = dcc.Interval(  # Интервал обновления графика
    id='interval-reload',
    interval=5 * 60000,  # 5 minutes
    n_intervals=0
)

app = dash.Dash(  # Выбор темы
    __name__, external_stylesheets=[dbc.themes.DARKLY]
)

app.layout = html.Div(
    [
        dcc.Store(id='df', storage_type='local'),
        dcc.Store(id='end_price', storage_type='local'),
        interval_reload,
        dbc.Row(
            [
                dbc.Col(html.H4(VERSION)),
            ],
            # style={'margin-bottom': 10}
        ),
        dbc.Row(
            [
                'All limit:',
                dbc.Col(all_period),
                'Visual limit:',
                dbc.Col(vis_period),
            ],
            style={'margin-bottom': 10}
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Loading(dbc.Button('Refresh', id="refresh", color="primary", outline=True)), width=1),
                dbc.Col(price_line, width=0),
                dbc.Col(price_sma, width=0),
                'SMA цены:',
                dbc.Col(sma_period_price, width=0),
                'SMA Vol:',
                dbc.Col(sma_period_vol, width=0),
            ],
            # style={'margin-bottom': 40}
        ),
        dbc.Row(
            [
                html.Div(sma_level_selector),
                # html.Div(vol_level_selector),
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
    Output('end_price', 'value'),
    Output('vis-period', 'max'),
    Input('all-period', 'value'),
    Input('refresh', 'n_clicks'),
    Input('interval-reload', 'n_intervals'),
    manager=long_callback_manager,
)
def update_df(all_limit, n, nn):
    cry = CryptoA(period=PERIOD, verbose=False)
    cry.load(limit=all_limit)
    df = cry.df[['Open', 'Close', 'Volume']]
    end_price = df['Close'][-1]
    end_vol = df['Volume'][-1]
    print(f'{end_price=}', f'{hd(end_vol)=}')
    df = df[['Open', 'Volume']]
    print(df)
    return 'Refresh', df.to_json(), end_price, all_limit


@app.callback(
    Output('btc-chart', 'children'),
    Input('df', 'data'),
    Input('end_price', 'value'),
    Input('refresh', 'n_clicks'),
    Input('sma-level-slider', 'value'),
    Input('interval-reload', 'n_intervals'),
    Input('price-line', 'value'),
    Input('sma-period-price', 'value'),
    Input('sma-period-vol', 'value'),
    Input('price-sma', 'value'),
    Input('vis-period', 'value'),
)
def update_chart(data, end_price, n, sma_level,
                 nn,
                 price_line, sma_period_price, sma_period_vol,
                 price_sma,
                 vis_limit
                 ):
    df = pd.read_json(data)
    if df.empty:
        raise PreventUpdate

    df.loc[:, f'wvwma_f'] = wvwma(df['Open'], df['Volume'], length=sma_level)
    df[f'sma_f'] = sma(df['Open'], length=sma_level)
    # Price SMA
    df['sma'] = sma(df['Open'], length=sma_period_price)
    # Volume SMA
    df['sma_v'] = sma(df['Volume'], length=sma_period_vol)
    df = df[-vis_limit:]

    # Make Figures
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_width=[0.21, 0.46],
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
                    width=2,
                    color='grey',
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
                    color='white',
                ),
                showlegend=True
            ), row=1, col=1
        )
    # WVWMA, SMA, DIFF
    # WVWMA
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[f'wvwma_f'], mode='lines', name=f'WVWMA({sma_level})',
            # hoverinfo='none',
            line=dict(
                width=4,
                color='blue',
            ),
            showlegend=True
        ), row=1, col=1
    )
    # SMA
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[f'sma_f'], mode='lines', name=f'SMA({sma_level})',
            # hoverinfo='none',
            line=dict(
                width=4,
                color='red',
            ),
            showlegend=True
        ), row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=[df.index[-1]],
            y=[end_price],
            text=f" {end_price}",
            name='EndPrice',
            textposition="middle right",
            mode="text+markers",
            marker=dict(color='yellow', size=12, symbol='star'),
            showlegend=True,
            hovertemplate=f"{end_price}"
        ), row=1, col=1
    )
    # Vert Vol
    fig.add_trace(
        go.Bar(
            x=df.index, y=df['Volume'], name='Volume',
            marker=dict(color='grey'), showlegend=True, opacity=0.5,
            # hoverinfo='none'
        ), row=2, col=1
    )
    # Vol SMA
    if price_sma:
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df['sma_v'], mode='lines', name=f'Vol SMA',
                # hoverinfo='none',
                line=dict(
                    width=1,
                    color='white',
                ),
                showlegend=True
            ), row=2, col=1
        )

    # fig.update_layout(template=CHARTS_TEMPLATE)
    fig.update_layout(
        template='plotly_dark',
        legend=dict(
            orientation='h',
            title_text='',
            x=0,
            y=1
        ),
        # plot_bgcolor='rgb(17,17,17)',
        # paper_bgcolor='rgb(17,17,17)',
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
        transition_duration=500,
    )
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
        row=2, col=1
    )
    fig.update_xaxes(
        title='Date',
        row=2, col=1
    )

    html1 = [
        html.Div('BTC/USD ' + PERIOD, className='header_plots'),
        dcc.Graph(figure=fig),
    ]

    return html1
    # out_btc


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8052, debug=False, use_reloader=True)
