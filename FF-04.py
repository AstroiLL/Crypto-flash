# import dash_bootstrap_components
import plotly
import dash
import dash_bootstrap_components as dbc
from io import StringIO
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
from dbiLL.db_btc import Db, BTC
from sqlalchemy import select

# Diskcache
import diskcache

"""
Flexible Flash
Серая линия сглаженая коротким периодом цена, для устранения шумов 
SMA (красная линия) показывает сглаженое движение цены
WVWMA (синяя линия) показывает взвешенное по объему движение цены
Пересечение SMA и WVWMA с плавным подбором периода
Когда синяя выше красной, объемы в бай
Когда красная выше синей, объемы в селл
Когда цена выше синей и красной, то приоритет в бай
Когда цена ниже синей и красной, то приоритет в селл
"""
cache = diskcache.Cache("/tmp/ff/cache_ff_04")
long_callback_manager = DiskcacheLongCallbackManager(cache)

# READ DATA

PERIOD = '1m'
WVW = 24
VER_P = plotly.__version__
VER_D = dash.__version__
VER_B = dbc.__version__
VERSION = f'BTC Flexible Flash #04, Plotly V{VER_P}, Dash V{VER_D}, Bootstrap V{VER_B}'

# Открытие базы всплесков объемов
db = Db('sqlite', '/home/astroill/Python/Crypto-flash/Data/btc_max_more_10.db')

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
        height=650,
        xaxis_showspikes=True,
        transition_duration=500,
    )
)

all_period = dbc.Input(  # Выбор периода загрузки данных 1 день
    id='all-period', placeholder='all period', type="number", value=60 * 24, step=60, min=60, persistence=True,
    persistence_type='local', debounce=True, inputmode='numeric',
)

vis_period = dbc.Input(  # Выбор периода отображения 12 часов
    id='vis-period', placeholder='vis period', type="number", value=60 * 12, step=60, min=60, persistence=True,
    persistence_type='local', debounce=True, inputmode='numeric',
)

pos = dbc.Switch(
    id="pos",
    label="Позиция",
    value=True,
    persistence=True, persistence_type='local',
),

# TODO разобраться с disabled=pos
position = dbc.Input(  # Ввод торговой позиции
    id='position', placeholder='position price', type="number", min=0, persistence=True,
    persistence_type='local', debounce=True, disabled=False
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

price_max_vol = html.Div(
    [  # Показывать всплески из объемов основного массива
        dbc.Switch(
            id="price-max-vol",
            label="Max Volume",
            value=True,
            persistence=True, persistence_type='local',
        ),
    ]
)

aggr_max_vol = html.Div(
    [  # Показывать всплески объемов из Aggr-server
        dbc.Switch(
            id="aggr-max-vol",
            label="Aggr Max Volume",
            value=True,
            persistence=True, persistence_type='local',
        ),
    ]
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
         [(60, '1h'), (120, '2h'), (180, '3h'), (240, '4h'), (360, '6h'), (480, '8h'), (600, '10h'), (720, '12h')]}
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

vol_level_selector = dcc.RangeSlider(  # Уровни показа средних и больших всплесков
    id='vol-level-slider',
    min=0,
    max=100,
    value=[25, 50],
    tooltip={'always_visible': True, 'placement': 'bottom'},
    persistence=True, persistence_type='local',
)

interval_reload = dcc.Interval(  # Интервал обновления графика
    id='interval-reload',
    interval=60 * 1000,  # 60 sec in milliseconds
    n_intervals=0
)

app = dash.Dash(  # Выбор темы
    # __name__, external_stylesheets=[dbc.themes.FLATLY]
    # __name__, external_stylesheets=[dbc.themes.SOLAR]
    __name__, external_stylesheets=[dbc.themes.DARKLY]
)

app.layout = html.Div(
    [
        dcc.Store(id='df', storage_type='local'),
        interval_reload,
        dbc.Row(
            [
                dbc.Col(html.H4(VERSION)),
                dbc.Col(html.Div(id='out-btc')),

            ],
            # style={'margin-bottom': 10}
        ),
        dbc.Row(
            [
                'All limit:',
                dbc.Col(all_period),
                'Visual limit:',
                dbc.Col(vis_period),
                dbc.Col(pos),
                'Pos:',
                dbc.Col(position),
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
                dbc.Col(price_max_vol, width=0),
                dbc.Col(aggr_max_vol, width=0),
                'SMA Vol:',
                dbc.Col(sma_period_vol, width=0),
            ],
            # style={'margin-bottom': 40}
        ),
        dbc.Row(
            [
                html.Div(sma_level_selector),
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
    Input('vis-period', 'value'),
    Input('sma-level-slider', 'value'),
    Input('refresh', 'n_clicks'),
    Input('interval-reload', 'n_intervals'),
    manager=long_callback_manager,
)
def update_df(all_limit, vis_limit, sma_level, n, nn):

    cry = CryptoA(period=PERIOD, verbose=False)
    cry.load(limit=all_limit)
    # df = pd.DataFrame()
    df = cry.df[['Open', 'Close', 'Volume']]
    # df.loc[:, ['Open', 'Close', 'Volume']] = cry.df[['Open', 'Close', 'Volume']]
    # print(df.isnull().sum())
    df.loc[:, 'wvwma_f'] = wvwma(df['Open'], df['Volume'], length=sma_level)
    df['sma_f'] = sma(df['Open'], length=sma_level)
    df = df[-vis_limit:]
    return 'Refresh', df.to_json()


@app.callback(
    Output('btc-chart', 'children'),
    Output('out-btc', 'children'),
    Input('df', 'data'),
    Input('refresh', 'n_clicks'),
    Input('sma-level-slider', 'value'),
    Input('vol-level-slider', 'value'),
    Input('interval-reload', 'n_intervals'),
    Input('position', 'value'),
    Input('pos', 'value'),
    Input('price-line', 'value'),
    Input('sma-period-price', 'value'),
    Input('sma-period-vol', 'value'),
    Input('price-sma', 'value'),
    Input('price-max-vol', 'value'),
    Input('aggr-max-vol', 'value'),
)
def update_chart(data, n, sma_level, range_vol_level, nn, position, pos, price_line, sma_period_price, sma_period_vol,
                 price_sma,
                 price_max_vol,
                 aggr_max_vol
                 ):
    """
    from io import StringIO
    import pandas as pd
    data = '{"key": "value"}'
    df = pd.read_json(StringIO(data))
    """
    # print(data)
    df = pd.read_json(StringIO(data))
    # df = pd.read_json(data)
    if df.empty:
        raise PreventUpdate
    # Получаем из dbiLL всплески объемов
    session = db.open()
    stmt = select(BTC)
    btc0 = []
    for btc in session.scalars(stmt):
        # print(btc.time, btc.close, btc.vol)
        btc0.append({'time': btc.time, 'close': btc.close, 'vol': btc.vol, 'd': btc.dir})
    session.close()
    btc_df = pd.DataFrame(btc0)
    # btc_df.set_index('time', inplace=True)
    btc_df = btc_df[btc_df.time >= df.index[0]]
    btc_df = btc_df.sort_values(by=['vol'], ascending=False).iloc[0:10, :]
    btc_df = btc_df.sort_values(by=['time'], ascending=True)
    btc_df['col'] = btc_df.d.where(btc_df.d == 0, 'green').where(btc_df.d == 1, 'orange')
    maxVa = btc_df['vol'].max()
    # print(maxV)
    vol_level0a = (range_vol_level[0] * maxVa) / 100
    vol_level1a = (range_vol_level[1] * maxVa) / 100
    btc_df['max_vol'] = 0
    btc_df['max_vol'] = btc_df['max_vol'].where(btc_df['vol'] < vol_level1a, 21).where(btc_df['vol'] < vol_level0a, 13)
    # print(btc_df)

    maxV = df['Volume'].max()
    print(maxV)
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
                    # size=1,
                    color='white',
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
                    size=dfv['max_vol'],
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
                # size=4,
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
                # size=4,
                color='red',
            ),
            showlegend=True
        ), row=1, col=1
    )
    end_price = df['Close'].iloc[-1]
    end_vol = df['Volume'].iloc[-1]
    print(end_price, hd(end_vol))
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
    # H lines Vol
    fig.add_hline(
        y=vol_level0, line_dash="dash",
        annotation_text=vol_level0,
        annotation_position="top right",
        row=2, col=1
    )
    fig.add_hline(
        y=vol_level1, line_dash="longdash",
        annotation_text=vol_level1,
        annotation_position="top right",
        row=2, col=1
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
        height=670,
        # height=800,
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

    return html1, out_btc


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8051, debug=False, use_reloader=True)
