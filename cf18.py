import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots

from MLDiLL.crypto2 import Crypto
from MLDiLL.utils import hd, HA, wvwma

cry_1h = Crypto(exchange="ftx", verbose=False)
cry_1m = Crypto(exchange="ftx", verbose=False)

vol_lev_hor = 0.3

locations = dcc.Location(id="url")
dropdown = dbc.DropdownMenu(
    children=[
        dbc.DropdownMenuItem("BTC", href="/"),
        dbc.DropdownMenuItem("ETH", href="/ETH"),
        dbc.DropdownMenuItem("XRP", href="/XRP"),
        # dbc.DropdownMenuItem("LTC", href="/LTC"),
    ],
    nav=True,
    in_navbar=True,
    label="Crypto",
)
max_vol_options = html.Div(
    [
        dbc.Checkbox(
            id='max_vol_options',
            persistence=True, persistence_type='local',
        ),
        dbc.Label(
            "MaxV Lines",
            html_for="max_vol_options",
        ),
    ],
)
type_bars = dbc.RadioItems(
    id='Bar',
    options=[{'label': i, 'value': i} for i in ['Candle', 'Heiken']],
    value='Heiken', persistence=True, persistence_type='local',
)
period_wvwma = dbc.InputGroup(
    [
        dbc.InputGroupText("Черная линия"),
        dbc.Input(
            id="period_wvwma", type="number", min=168, step=168, value=336,
            persistence=True, persistence_type='local'
        ),
        dbc.InputGroupText("(h)"),
    ]
)
all_period_input = dbc.InputGroup(
    [
        dbc.InputGroupText("Весь диапазон"),
        dbc.Input(
            id="all_period", type="number", min=168, step=168, value=504,
            persistence=True, persistence_type='local'
        ),
        dbc.InputGroupText("(h)"),
    ]
)
period_input_v = dbc.InputGroup(
    [
        dbc.InputGroupText("Диапазон по объему"),
        dbc.Input(
            id="period_v", type="number", min=24, step=24, value=168,
            persistence=True, persistence_type='local'
        ),
        dbc.InputGroupText("(h)"),

    ]
)

refresh = html.Div(
    [
        dbc.Button('Refresh', id="Button", color="primary", outline=True),
        html.Br(),
        html.Br(),
        dcc.Loading(html.Div(dbc.Badge(id='crypto')))
    ]
)
slider_vol = html.Div(
    [
        dbc.Label("Vol Level", html_for="VolLevel", align='start'),
        dcc.Slider(
            id='VolLevel',
            min=30,
            max=90,
            value=50,
            marks={f'{i}': f'{i}%' for i in range(30, 91, 10)},
            step=5,
            tooltip={'always_visible': True, 'placement': 'bottom'},
            persistence=True, persistence_type='local',
        ),
    ]
)
slider_hours = html.Div(
    [
        dbc.Label("Диапазон", html_for="Hours", align='start'),
        dcc.Slider(
            id='Hours',
            min=5,
            max=24 * 7 + 3,
            value=48,
            marks={**{f'{6 * i}': f'{6 * i} ч' for i in range(1, 4)}, **{f'{24 * i}': f'{i} Д' for i in range(1, 8)}},
            step=6,
            tooltip={'always_visible': True, 'placement': 'bottom'}, persistence=True, persistence_type='local',
        )
    ]
)
dump = dbc.Badge(' ', color="light")
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Col(
                [
                    dbc.Row(
                        [
                            dbc.Col(dbc.NavbarBrand("CFlash 18"), width={'size': 2, 'order': 'first'}),
                            dbc.Col(
                                [
                                    dbc.Row(all_period_input),
                                    dbc.Row(period_input_v),
                                    dbc.Row(period_wvwma),
                                ], width='auto'
                            ),
                            dbc.Col(
                                [
                                    dbc.Row(max_vol_options),
                                    dbc.Row(type_bars)
                                ], width=2
                            ),
                            dbc.Col(
                                [
                                    dbc.Row(dropdown, align='left'),
                                    dbc.Row(refresh),
                                ], width=2
                            )
                        ]
                    ),
                    dbc.Row(html.Div(id='title_out'))
                ], width=6
            ),
            dbc.Col(
                [
                    dbc.Row(slider_vol, justify="around"),
                    dbc.Row(slider_hours, justify="around"),
                ], width=6
            )
        ], fluid=True
    ), sticky="top",
)

interval_reload = dcc.Interval(
    id='interval-reload',
    interval=60000,  # in milliseconds
    n_intervals=0
)

# graph = dcc.Graph(id='graph_out')
# graph = dcc.Loading(html.Div(id='graph'),)
graph = html.Div(id='graph')
# dcc.Loading(html.Div(dbc.Badge(id='crypto')))
# store = dcc.Store(id='data', storage_type='local')
app = dash.Dash(external_stylesheets=[dbc.themes.FLATLY])
# app = dash.Dash(external_stylesheets=[dbc.themes.SKETCHY])
# app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])
# app = dash.Dash(external_stylesheets=[dbc.themes.SLATE])
app.layout = dbc.Container(
    [
        locations,
        # store,
        navbar,
        graph,
        interval_reload,
    ],
    fluid=True,
)


# TODO repair select crypto
def connect_base(pathname, all_p, repair=True):
    crypto = 'BTC/USD:USD'
    if pathname == "/ETH":
        crypto = 'ETH/USD'
    elif pathname == "/XRP":
        crypto = 'XRP/USD'
    # elif pathname == "/LTC":
    #     crypto = 'LTC/USD'
    # Порядок действий: open load repair
    cry_1h.open(crypto=crypto, period='1h', update=True)
    cry_1h.load(limit=all_p)
    if repair: cry_1h.repair_table()
    cry_1m.open(crypto=crypto, period='1m', update=True)
    cry_1m.load(limit=all_p * 60)
    if repair: cry_1m.repair_table()
    return crypto


@app.callback(
    Output("crypto", "children"),
    [Input("url", "pathname"),
     Input("all_period", "value"),
     Input("period_v", "value"),
     Input('Button', 'n_clicks'),
     Input('interval-reload', 'n_intervals')
     ]
)
def render_page_content(pathname, all_p, p, but, n):
    crypto = connect_base(pathname, all_p)
    print('Refresh ', pathname, n, crypto)
    return crypto


@app.callback(
    [Output('graph', 'children'), Output('title_out', 'children')],
    [Input('period_wvwma', 'value'),
     Input('Hours', 'value'),
     Input('VolLevel', 'value'),
     Input('Bar', 'value'),
     Input('Button', 'n_clicks'),
     Input('interval-reload', 'n_intervals'),
     Input("url", "pathname"),
     Input("all_period", "value"),
     Input("period_v", "value"),
     Input("max_vol_options", "checked")]
)
def update_graph(wvwma_0, hours, vol_level, act, but, n, pathname, all_p, p, mvo):
    print('Update', pathname, n)
    if cry_1h.df.empty or n == 0:
        print('Empty df ', pathname, n)
        connect_base(pathname, all_p, repair=False)
    df = cry_1h.df
    # Найти уровень Vol в % от максимального за весь выбраный диапазон
    lev = vol_level * df['Volume'].max() * 0.01
    # Последняя цена
    end_price = cry_1m.df['Close'][-1]
    end_vol = cry_1h.df['Volume'][-1]
    print(end_price, hd(end_vol))
    pre_end_vol = cry_1h.df['Volume'][-2]
    # Брать из массива минут, группировать по часам, находить в каждом часе индекс максимума и
    # Open максимума этого часа прописывать в Open_max массива часов
    df['Open_max'] = cry_1m.df['Open'][cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax()].resample(
        '1h'
    ).mean()
    df['Date_max'] = cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax().resample('1h').max()
    # TODO Выбор периодов линий на странице
    wvwma_0 = int(wvwma_0)
    wvwma_1 = 24
    wvwma_2 = 48
    wvwma_3 = 168
    # Графики взвешенных объемно-взвешенных
    df[f'wvwma_{wvwma_0}'] = wvwma(df['Open_max'], df['Volume'], length=wvwma_0)
    df[f'wvwma_{wvwma_1}'] = wvwma(df['Open_max'], df['Volume'], length=wvwma_1)
    df[f'wvwma_{wvwma_2}'] = wvwma(df['Open_max'], df['Volume'], length=wvwma_2)
    df[f'wvwma_{wvwma_3}'] = wvwma(df['Open_max'], df['Volume'], length=wvwma_3)

    # Создать массив разниц максимумов на каждом баре и текущей цены
    df['lsl'] = df['Open_max'] - end_price
    df['ls_color'] = df['lsl'].where(df['lsl'] >= 0, 'blue').where(df['lsl'] < 0, 'red')
    vol_l = df['Volume'][df['lsl'] < 0].sum()
    vol_s = df['Volume'][df['lsl'] >= 0].sum()

    # Синий если сумма предыдущих объемов p баров была выше, красный если ниже
    def v_compare(ser):
        d = df.loc[ser.index]
        d['l'] = d['Open_max'] - d['Open_max'][-1]
        # df['ls_color'] = df['lsl'].where(df['lsl'] >= 0, 'blue').where(df['lsl'] < 0, 'red')
        # print(df.loc[ser.index])
        return d['Volume'][d['l'] >= 0].sum() - d['Volume'][d['l'] < 0].sum()

    df['lslv'] = df['Open_max'].rolling(window=p).apply(v_compare, raw=False)
    df['ls_color_v'] = df['lslv'].where(df['lslv'] >= 0, 'blue').where(df['lslv'] < 0, 'red')

    df = df[-hours:]
    # Фильтровать по критерию Vol >= уровень
    maxv = df[df['Volume'] >= lev].index
    # Больше число - меньше точек
    maxv2 = df[df['Volume'] >= lev * 0.3].index
    # print(len(maxv2))
    df.loc[:, 'rank'] = df['Volume'][maxv].rank()
    df.loc[:, 'rank2'] = df['Volume'][maxv2].rank()
    df['rank2'].fillna(0, inplace=True)
    # print(df)
    grid = (df['Open_max'].max() - df['Open_max'].min()) / 100
    df.loc[:, 'Prof_Bar'] = df['Open_max'] // grid * grid
    dfg = df[df['Volume'] >= df['Volume'].max() * vol_lev_hor].groupby(['Prof_Bar']).sum()

    # Рисовать графики
    fig = make_subplots(
        rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": False}]], shared_xaxes=True,
        shared_yaxes=True, vertical_spacing=0.001, horizontal_spacing=0.03, column_widths=[1, 0.1]
    )
    # Heiken Ashi OR Candles
    if act == 'Candle':
        df_act = df
    else:
        df_act = HA(df)
    # print(maxv)
    # fig.add_trace()
    voldir = vol_l - vol_s
    dirs = '^' if voldir >= 0 else 'v'
    color_end = 'red' if voldir < 0 else 'blue'
    # maxVol
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Open_max'], mode='markers', name='max Volume',
            # hoverinfo='text',
            # hovertext=df['Date_max'][maxv],
            # text=df['Date_max'][maxv],
            # textposition="top right",
            marker=dict(
                # symbol='circle',
                size=df['rank2'],
                symbol='square',
                color=df['ls_color_v'],
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # VWMA(<1D)
    fig.add_trace(
        go.Scatter(
            x=df.index[:-wvwma_1], y=df[f'wvwma_{wvwma_1}'][:-wvwma_1], mode='markers', name='<WVWMA(1D)',
            # hoverinfo='none',
            marker=dict(
                size=4,
                color='cyan',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # VWMA(1D>)
    fig.add_trace(
        go.Scatter(
            x=df.index[-wvwma_1:], y=df[f'wvwma_{wvwma_1}'][-wvwma_1:], mode='markers', name='WVWMA(1D)>',
            # hoverinfo='none',
            marker=dict(
                size=4,
                color='blue',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # VWMA(<2D)
    fig.add_trace(
        go.Scatter(
            x=df.index[:-wvwma_2], y=df[f'wvwma_{wvwma_2}'][:-wvwma_2], mode='markers', name='<WVWMA(2D)',
            # hoverinfo='none',
            marker=dict(
                size=4,
                color='yellow',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # VWMA(2D>)
    fig.add_trace(
        go.Scatter(
            x=df.index[-wvwma_2:], y=df[f'wvwma_{wvwma_2}'][-wvwma_2:], mode='markers', name='WVWMA(2D)>',
            # hoverinfo='none',
            marker=dict(
                size=4,
                color='orange',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # VWMA(1W)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[f'wvwma_{wvwma_3}'], mode='markers', name='WVWMA(1W)',
            # hoverinfo='none',
            marker=dict(
                size=6,
                color='red',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # WVWMA_0
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[f'wvwma_{wvwma_0}'], mode='lines', name=f'WVWMA({wvwma_0}h)',
            # hoverinfo='none',
            line=dict(
                width=2,
                color='black',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # Обычные свечи
    fig.add_trace(
        go.Candlestick(
            x=df_act.index, open=df_act['Open'], close=df_act['Close'], high=df_act['High'], low=df_act['Low'],
            increasing=dict(line=dict(color='blue', width=1)),
            decreasing=dict(line=dict(color='red', width=1)),
            showlegend=False,
            opacity=0.4,
            # hoverinfo='none'
        ), 1, 1, secondary_y=False,
    )
    # Объемные свечи
    fig.add_trace(
        go.Candlestick(
            x=maxv, open=df_act['Open'][maxv], close=df_act['Close'][maxv], high=df_act['High'][maxv],
            low=df_act['Low'][maxv],
            increasing=dict(line=dict(color='green', width=3)),
            decreasing=dict(line=dict(color='purple', width=3)),
            showlegend=False,
            opacity=1,
            # hoverinfo='none'
        ), 1, 1, secondary_y=False,
    )
    # Vert Vol
    fig.add_trace(
        go.Bar(
            x=df.index, y=df['Volume'].where(df['Volume'] >= lev * 0.8, 0), name='Volume',
            marker=dict(color='grey'), showlegend=True, opacity=0.2,
            # hoverinfo='none'
        ),
        row=1, col=1, secondary_y=True
    )
    # Hor Vol
    if dfg.shape[0] > 1:
        fig.add_trace(
            go.Bar(
                x=dfg['Volume'],
                y=dfg.index,
                orientation='h',
                # marker=dict(color='blue'),
                name='VolH',
                showlegend=False,
                # hoverinfo='none',
                marker_color=dfg['Volume'],
                # texttemplate='%{x}', textposition='outside',
                # width=10
            ), 1, 2
        )
    # Indicator
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=end_vol,
            number={'prefix': "Vol:"},
            delta={'position': "top", 'reference': pre_end_vol},
            domain={'x': [0, 1], 'y': [0, 1]}
        )
    )
    # End price
    fig.add_trace(
        go.Scatter(
            x=[cry_1m.df.index[-1]],
            y=[end_price],
            text=f" {end_price}",
            name='EndPrice',
            textposition="middle right",
            mode="text+markers",
            marker=dict(color=color_end, size=12, symbol='star'),
            showlegend=True,
            hovertemplate=f"{end_price}"
        ), 1, 1, secondary_y=False
    )
    # Level price
    fig.add_trace(
        go.Scatter(
            x=[df.index[-1] for _ in range(len(maxv))],
            y=df['Open_max'][maxv],
            text=df['Open_max'][maxv],
            textposition="top right",
            mode="text",
            name='Max Vol Price',
            showlegend=True,
            # hoverinfo='none',
            legendgroup='Max Vol Lines',
        ), 1, 1, secondary_y=False
    )
    # Vol Flash
    fig.add_trace(
        go.Scatter(
            x=[maxv[i] for i in range(len(maxv))],
            y=df['Open_max'][maxv],
            hoverinfo="text",
            hovertext=df['Date_max'][maxv],
            # hovertemplate="Date:% {df['Date_max'][maxv]}",
            # hovertemplate=None,
            marker=dict(
                size=(df['Volume'][maxv] / df['Volume'][maxv].max() * 30).astype('int64'),
                color=df['ls_color'][maxv],
                line=dict(color=df.Volume, width=1),

            ),
            mode='markers',
            # text=df_1h['Open'][maxv],
            # textposition="top right",
            # mode="text",
            showlegend=False
        ), 1, 1, secondary_y=False
    )
    # # Line
    if True:
        [fig.add_shape(
            dict(
                type="line", xref='x', yref='y', x0=maxv[i], x1=df.index[-1],
                y0=df['Open_max'][maxv][i], y1=df['Open_max'][maxv][i],
                line=dict(color=df['ls_color'][maxv][i], width=df['rank'][maxv][i]),
            ),
            # hoverinfo='none',
            # showlegend=True,
            # legendgroup='Max Vol Lines',
        ) for i in range(len(maxv))]
    # Levels annotation
    [fig.add_annotation(
        dict(
            x=maxv[i],
            y=df['Open_max'][maxv][i],
            xref="x",
            yref="y",
            text=f"{hd(df['Volume'][maxv][i], 0)}<br>{df['Date_max'][maxv][i].strftime('%d,%H:%M')}",
            # hoverinfo='text',
            # hovertext=f"{df['Open_max'][maxv][i]}",
            name='Max Vol Annot',
            # showlegend=True,
            # legendgroup='Max Vol Annot',
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            ax=-40,
            ay=-40
        )
    ) for i in range(len(maxv))]
    title = f"{dirs} {hd(voldir, sign=True)} all_period:{all_p / 24}d end_price: {end_price} " + \
            f"VWMA({wvwma_1}h):{hd(end_price - df[f'wvwma_' + str(wvwma_1)][-1], 1, True)} " + \
            f"VWMA({wvwma_2}h):{hd(end_price - df[f'wvwma_' + str(wvwma_2)][-1], 1, True)} " + \
            f"VWMA({wvwma_3}h):{hd(end_price - df[f'wvwma_' + str(wvwma_3)][-1], 1, True)} "
    fig.update_layout(
        font=dict(
            family='Roboto',
            size=10
        ),
        xaxis_title="Date",
        yaxis_title=f"{cry_1h.crypto}",
        # height=650,
        height=700,
        # width=1400,
        xaxis_rangeslider_visible=False,
        # legend_orientation="h",
        legend=dict(x=0, y=1, orientation='h'),
        hovermode="x unified",
        # hoverlabel_align='right',
        # margin={"r": 0, "t": 1, "l": 0, "b": 0}
    )
    # pio.write_image(fig=fig, file=f'btc{intervals}.jpg', format='jpg')
    # pio.write_json(fig=fig, file=f'btc{intervals}.json', pretty=True)
    # print(but, intervals)
    figure = [dcc.Graph(figure=fig)]
    return figure, title


if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=8052, debug=False, use_reloader=True)
