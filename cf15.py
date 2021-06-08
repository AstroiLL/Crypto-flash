import pandas as pd
# from pandas import DataFrame
# import numpy as np
# from datetime import datetime as dt
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from plotly.subplots import make_subplots
# import plotly.io as pio
# import pandas_ta as ta    

from MLDiLL.crypto import Crypto
from MLDiLL.utils import hd, HA, wvwma

cry_1h = Crypto(verbose=False)
cry_1m = Crypto(verbose=False)
# df_exch = cry_1h.get_list_exch()

vol_lev_hor = 0.4
# nav_item = dbc.NavItem(dbc.NavLink("BitMEX", href="https://bitmex.com/"))

locations = dcc.Location(id="url")
dropdown = dbc.DropdownMenu(
    children=[
        dbc.DropdownMenuItem("BTC", href="/"),
        dbc.DropdownMenuItem("ETH", href="/ETH"),
        dbc.DropdownMenuItem("XRP", href="/XRP"),
        dbc.DropdownMenuItem("LTC", href="/LTC"),
    ],
    nav=True,
    in_navbar=True,
    label="Crypto",
)
max_vol_options = dbc.FormGroup(
    [
        dbc.Checkbox(
            id='max_vol_options',
            checked=True, persistence=True, persistence_type='local',
        ),
        dbc.Label(
            "Max Vol Lines",
            html_for="max_vol_options",
        ),
    ],
    check=True,
)
type_bars = dbc.RadioItems(
    id='Bar',
    options=[{'label': i, 'value': i} for i in ['Candle', 'Heiken']],
    value='Heiken', persistence=True, persistence_type='local',
)
period_wvwma = dbc.InputGroup(
            [
                dbc.InputGroupAddon("wvwma(h)", addon_type="prepend"),
                dbc.Input(id="period_wvwma", type="number", min=2, step=1, value=120,
                          persistence=True, persistence_type='local')
            ])
all_period_input = dbc.InputGroup(
            [
                dbc.InputGroupAddon("period(h)", addon_type="prepend"),
                dbc.Input(id="all_period", type="number", min=168, step=168, value=504,
                          persistence=True, persistence_type='local')
            ])
period_input_v = dbc.InputGroup(
            [
                dbc.InputGroupAddon("period V (h)", addon_type="prepend"),
                dbc.Input(id="period_v", type="number", min=24, step=6, value=24,
                          persistence=True, persistence_type='local')
            ])


crypto_label = dbc.Badge(id='crypto', color="light")
refresh = dbc.Button([crypto_label, "Refresh"], id="Button", color="primary", outline=True, block=False)
# reload = dbc.Badge(id='reload', color="light")
dump = dbc.Badge(' ', color="light")
navbar = dbc.NavbarSimple(
    children=[
        # reload,
        period_wvwma,
        all_period_input,
        period_input_v,
        max_vol_options,
        dump,

        type_bars,
        dropdown,
        dump,
        refresh,
    ],
    brand="Crypto Flash 15 BitMEX",
    brand_href="#",
    sticky="top",
)
slider_vol = dcc.Slider(
    id='VolLevel',
    min=20,
    max=60,
    value=50,
    marks={f'{i}': f'{i}%' for i in range(25, 60, 5)},
    step=1,
    tooltip={'always_visible': True, 'placement': 'bottom'},
    persistence=True, persistence_type='local',
)
slider_hours = dcc.Slider(
    id='Hours',
    min=5,
    max=24 * 7,
    value=48,
    marks={**{f'{6 * i}': f'{6 * i}h' for i in range(1, 4)}, **{f'{24 * i}': f'{i}D' for i in range(1, 8)}},
    step=1,
    tooltip={'always_visible': True, 'placement': 'bottom'}, persistence=True, persistence_type='local',
)
interval_reload = dcc.Interval(
    id='interval-reload',
    interval=60000,  # in milliseconds
    n_intervals=0
)

graph = dcc.Graph(id='graph_out')
# store = dcc.Store(id='data', storage_type='local')
app = dash.Dash(external_stylesheets=[dbc.themes.SKETCHY])
app.layout = html.Div([
    locations,
    # store,
    navbar,
    html.Br(),
    slider_vol,
    html.Br(),
    slider_hours,
    html.Br(),
    interval_reload,
    graph,
])


# TODO repair select crypto
def connect_base(pathname, all_p):
    crypto = 'BTC/USD'
    if pathname == "/ETH":
        crypto = 'ETH/USD'
    elif pathname == "/XRP":
        crypto = 'XRP/USD'
    elif pathname == "/LTC":
        crypto = 'LTC/USD'
    cry_1h.open(exchange='BITMEX', crypto=crypto, period='1h', update=True)
    cry_1h.load(limit=all_p)
    cry_1h.repair_table()
    # TODO Порядок действий?
    cry_1m.open(exchange='BITMEX', crypto=crypto, period='1m', update=True)
    cry_1m.load(limit=all_p * 60)
    cry_1m.repair_table()
    return crypto


@app.callback(Output("crypto", "children"),
              [Input("url", "pathname"),
               Input("all_period", "value"),
               Input("period_v", "value"),
               Input('Button', 'n_clicks'),
               Input('interval-reload', 'n_intervals')
               ])
def render_page_content(pathname, all_p, but, n):
    print('Refresh ', pathname, n)
    crypto = connect_base(pathname, all_p)
    return crypto


@app.callback(
    Output('graph_out', 'figure'),
    [Input('period_wvwma', 'value'),
     Input('Hours', 'value'),
     Input('VolLevel', 'value'),
     Input('Bar', 'value'),
     Input('Button', 'n_clicks'),
     Input('interval-reload', 'n_intervals'),
     Input("url", "pathname"),
     Input("all_period", "value"),
     Input("period_v", "value"),
     Input("max_vol_options", "checked")])
def update_graph(wvwma_0, hours, vol_level, act, but, n, pathname, all_p, p, mvo):
    print('Update', pathname, n)
    if cry_1h.df.empty or n == 0:
        print('Empty df ', pathname, n)
        connect_base(pathname, all_p)
    df = cry_1h.df
    # Найти уровень Vol в % от максимального за весь выбраный диапазон
    lev = vol_level * df['Volume'].max() * 0.01
    # Последняя цена
    end_price = cry_1m.df['Close'][-1]
    # Брать из массива минут, группировать по часам, находить в каждом часе индекс максимума и
    # Open максимума этого часа прописывать в Open_max массива часов
    df['Open_max'] = cry_1m.df['Open'][cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax()].resample('1h').mean()
    df['Date_max'] = cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax().resample('1h').max()
    # TODO Выбор периодов линий на странице
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
    # print(len(maxv))
    df.loc[:, 'rank'] = df['Volume'][maxv].rank()
    grid = (df['Open_max'].max() - df['Open_max'].min()) / 100
    df.loc[:, 'Prof_Bar'] = df['Open_max'] // grid * grid
    dfg = df[df['Volume'] >= df['Volume'].max() * vol_lev_hor].groupby(['Prof_Bar']).sum()

    # Рисовать графики
    fig = make_subplots(rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": False}]], shared_xaxes=True,
                        shared_yaxes=True, vertical_spacing=0.001, horizontal_spacing=0.03, column_widths=[1, 0.1])
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
            x=df.index, y=df['Open_max'], mode='lines+markers', name='max Volume',
            marker=dict(
                symbol='cross',
                color=df['ls_color_v'],
            ),
            line=dict(
                color='grey',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # VWMA(<1D)
    fig.add_trace(
        go.Scatter(
            x=df.index[:-wvwma_1], y=df[f'wvwma_{wvwma_1}'][:-wvwma_1], mode='markers', name='<WVWMA(1D)',
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
            line=dict(
                width=2,
                color='black',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    fig.add_trace(
        go.Candlestick(
            x=df_act.index, open=df_act['Open'], close=df_act['Close'], high=df_act['High'], low=df_act['Low'],
            increasing=dict(line=dict(color='blue', width=1)),
            decreasing=dict(line=dict(color='red', width=1)),
            showlegend=False,
            opacity=0.4,
            hoverinfo='none'
        ), 1, 1, secondary_y=False,
    )
    fig.add_trace(
        go.Candlestick(
            x=maxv, open=df_act['Open'][maxv], close=df_act['Close'][maxv], high=df_act['High'][maxv], low=df_act['Low'][maxv],
            increasing=dict(line=dict(color='green', width=3)),
            decreasing=dict(line=dict(color='purple', width=3)),
            showlegend=False,
            opacity=1,
            hoverinfo='none'
        ), 1, 1, secondary_y=False,
    )
    # Vert Vol
    fig.add_trace(
        go.Bar(x=df.index, y=df['Volume'].where(df['Volume'] >= lev*0.8, 0), name='Volume',
               marker=dict(color='grey'), showlegend=True, opacity=0.2,
               hoverinfo='none'
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
            y=[end_price],
            text=f"{end_price}",
            textposition="middle right",
            mode="text+markers",
            marker=dict(color=color_end, size=12, symbol='star'),
            showlegend=False,
            hoverinfo='none'
        ), 1, 1, secondary_y=False)
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
            legendgroup='Max Vol Lines',
        ), 1, 1, secondary_y=False)
    # Vol Flash
    fig.add_trace(
        go.Scatter(
            x=[maxv[i] for i in range(len(maxv))],
            y=df['Open_max'][maxv],
            hoverinfo="text",
            hovertext=df['Date_max'][maxv],
            # hovertext=df['Date_max'][maxv].dt.time,
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
        ), 1, 1, secondary_y=False)
    # # Line
    if mvo:
        [fig.add_shape(
            dict(
                type="line", xref='x', yref='y', x0=maxv[i], x1=df.index[-1],
                y0=df['Open_max'][maxv][i], y1=df['Open_max'][maxv][i],
                line=dict(color=df['ls_color'][maxv][i], width=df['rank'][maxv][i]),
            ),
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
            text=f"V:{df['Volume'][maxv][i]:,.0f}",
            hovertext=f"{df['Open_max'][maxv][i]}",
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
    fig.update_layout(
        title=f"{dirs} {hd(voldir,sign=True)} all_period:{all_p/24}d end_price: {end_price} " +
        f"VWMA({wvwma_1}h):{hd(end_price-df[f'wvwma_'+str(wvwma_1)][-1],1,True)} "+
        f"VWMA({wvwma_2}h):{hd(end_price-df[f'wvwma_'+str(wvwma_2)][-1],1,True)} "+
        f"VWMA({wvwma_3}h):{hd(end_price-df[f'wvwma_'+str(wvwma_3)][-1],1,True)} ",
        xaxis_title="Date",
        yaxis_title=f"{cry_1h.crypto}",
        height=650,
        # width=1024,
        xaxis_rangeslider_visible=False,
        # legend_orientation="h",
        legend=dict(x=0, y=1, orientation='h'),
        hovermode="x unified",
        # margin={"r": 0, "t": 1, "l": 0, "b": 0}
    )
    # pio.write_image(fig=fig, file=f'btc{intervals}.jpg', format='jpg')
    # pio.write_json(fig=fig, file=f'btc{intervals}.json', pretty=True)
    # print(but, intervals)
    return fig


if __name__ == '__main__':
    app.run_server(port=8051, debug=False, use_reloader=True)
