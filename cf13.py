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

from DiLL.crypto import Crypto
from DiLL.utils import hd, HA, vwap

# TODO выбор all_period
# TODO выбор crypto vol_scale
all_period = 336
# ETH
# crypto = 'ETH/USD'
# vol_scale = 5*1e3
# BTC
# crypto = 'BTC/USD'
# vol_scale = 1e6

cry_1h = Crypto(verbose=False)
df_exch = cry_1h.get_list_exch()
cry_1m = Crypto(verbose=False)
cry_1h.connect(exchange='BITMEX', crypto='BTC/USD', period='1h')
cry_1h.update_crypto()
cry_1h.load_crypto(limit=all_period)
cry_1m.connect(exchange='BITMEX', crypto='BTC/USD', period='1m')
cry_1m.update_crypto()
cry_1m.load_crypto(limit=all_period * 60)

vol_lev = 0.4
# nav_item = dbc.NavItem(dbc.NavLink("BitMEX", href="https://bitmex.com/"))

locations = dcc.Location(id="url")
dropdown = dbc.DropdownMenu(
    children=[
        dbc.DropdownMenuItem("BTC", href="/"),
        dbc.DropdownMenuItem("ETH", href="/ETH"),
        # dbc.DropdownMenuItem(divider=True),
        dbc.DropdownMenuItem("DOGE", href="/DOGE"),
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
crypto_label = dbc.Badge(id='crypto', color="light")
refresh = dbc.Button([crypto_label, "Refresh"], id="Button", color="primary", outline=True, size="sm", block=False)
reload = dbc.Badge(id='reload', color="light")
dump = dbc.Badge(' ', color="light")
navbar = dbc.NavbarSimple(
    children=[
        reload,
        max_vol_options,
        dump,
        type_bars,
        dropdown,
        dump,
        refresh,
    ],
    brand="Crypto Flash 13 BitMEX",
    brand_href="#",
    sticky="top",
)
slider_vol = dcc.Slider(
    id='VolLevel',
    min=300,
    max=800,
    value=500,
    marks={f'{i}': f'{i}M' for i in range(300, 800, 50)},
    step=50,
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
store = dcc.Store(id='data', storage_type='local')
app = dash.Dash(external_stylesheets=[dbc.themes.SKETCHY])
app.layout = html.Div([
    locations,
    store,
    navbar,
    html.Br(),
    slider_vol,
    html.Br(),
    slider_hours,
    html.Br(),
    interval_reload,
    graph,
])


@app.callback(Output("crypto", "children"), [Input("url", "pathname")], State('data', 'data'))
def render_page_content(pathname, data):
    data = data or {'crypto': 'BTC/USD', 'vol_scale': 1e6}
    data['crypto'] = 'BTC/USD'
    data['vol_scale'] = 1e6
    if pathname == "/ETH":
        data['crypto'] = 'ETH/USD'
        data['vol_scale'] = 5e3
    elif pathname == "/DOGE":
        data['crypto'] = 'DOGE/USD'
        data['vol_scale'] = .0001
    crypto = data['crypto']
    cry_1h.connect(exchange='BITMEX', crypto=crypto, period='1h')
    cry_1h.update_crypto()
    cry_1h.load_crypto(limit=all_period)
    cry_1m.connect(exchange='BITMEX', crypto=crypto, period='1m')
    cry_1m.update_crypto()
    cry_1m.load_crypto(limit=all_period * 60)
    return f"{crypto}"


@app.callback(
    Output('reload', "children"),
    [Input('Button', 'n_clicks'),
     Input('interval-reload', 'n_intervals')])
def update_df(but, intervals):
    cry_1h.update_crypto()
    cry_1h.load_crypto(limit=all_period)
    cry_1m.update_crypto()
    cry_1m.load_crypto(limit=all_period*60)
    return f"{intervals}"


@app.callback(
    Output('graph_out', 'figure'),
    [Input('Hours', 'value'),
     Input('VolLevel', 'value'),
     Input('Bar', 'value'),
     Input('Button', 'n_clicks'),
     Input('interval-reload', 'n_intervals'),
     Input("url", "pathname"),
     Input("max_vol_options", "checked")],
    State('data', 'data'))
def update_graph(hours, vol_level, act, but, intervals, pathname, mvo, data):
    data = data or {'crypto': 'BTC/USD', 'vol_scale': 1e6}
    crypto = data['crypto']
    vol_scale = data['vol_scale']
    df = cry_1h.df
    lev = vol_level * vol_scale
    vwap_info_w = '1W'
    vwap_info_d = '1D'
    vwap_info_i = 48
    df = vwap(df, period=vwap_info_w, price=['Open', 'High', 'Low'])
    df = vwap(df, period=vwap_info_d, price=['Open', 'High', 'Low'])
    df = vwap(df, period=vwap_info_i)
    # print(df)
    end_price = cry_1m.df['Close'][-1]
    # берем из массива минут, группируем по часам, находим в каждом часе индекс максимума и
    # Open максимума этого часа прописываем в Open_max массива часов
    df['Open_max'] = cry_1m.df['Open'][cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax()].resample('1h').mean()
    df['Date_max'] = cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax().resample('1h').max()
    # print(df['Date_max'][-5:])
    df['lsl'] = df['Open_max'] - end_price
    df['ls_color'] = df['lsl'].where(df['lsl'] >= 0, 'blue').where(df['lsl'] < 0, 'red')
    vol_l = df['Volume'][df['lsl'] < 0].sum()
    vol_s = df['Volume'][df['lsl'] >= 0].sum()

    df = df[-hours:]

    maxv = df[df['Volume'] >= lev].index
    # print(len(maxv))
    df['rank'] = df['Volume'][maxv].rank()
    grid = (df['Open_max'].max() - df['Open_max'].min()) / 100
    df['Prof_Bar'] = df['Open_max'] // grid * grid
    dfg = df[df['Volume'] >= df['Volume'].max() * vol_lev].groupby(['Prof_Bar']).sum()
    fig = make_subplots(rows=1, cols=2, specs=[[{"secondary_y": True}, {"secondary_y": False}]], shared_xaxes=True,
                        shared_yaxes=True, vertical_spacing=0.001, horizontal_spacing=0.03, column_widths=[1, 0.1])
    # Heiken Ashi OR Candles
    if act == 'Candle':
        df_act = df
    else:
        df_act = HA(df)
    # print(maxv)
    # fig.add_trace()
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
                color='blue',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # VWMA(i)
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df[f'vwap_{vwap_info_i}'], mode='markers', name=f'VWMA({vwap_info_i}h)',
            marker=dict(
                # width=1,
                color='red',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # maxVol
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Open_max'], mode='lines+markers', name='max Volume',
            marker=dict(
                symbol='x',
                color='grey',
            ),
            showlegend=True
        ), 1, 1, secondary_y=False,
    )
    # Vert Vol
    # fig.add_trace(
    #     go.Volume(x=df.index, y=df['Volume'], name='Volume',
    #            showlegend=True, opacity=0.2,
    #            hoverinfo='none'
    #            ),
    #     row=1, col=1, secondary_y=True)
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
            marker=dict(color='red', size=10, symbol='star'),
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
    voldir = vol_l - vol_s
    dirs = '^' if voldir >= 0 else 'v'
    # fig.update_xaxes(
    #     rangeslider_visible=False,
    #     tickformatstops=[
    #         dict(dtickrange=[None, 1000], value="%H:%M:%S.%L ms"),
    #         dict(dtickrange=[1000, 60000], value="%H:%M:%S s"),
    #         dict(dtickrange=[60000, 3600000], value="%H:%M m"),
    #         dict(dtickrange=[3600000, 86400000], value="%H:%M h"),
    #         dict(dtickrange=[86400000, 604800000], value="%e. %b d"),
    #         dict(dtickrange=[604800000, "M1"], value="%e. %b w"),
    #         dict(dtickrange=["M1", "M12"], value="%b '%y M"),
    #         dict(dtickrange=["M12", None], value="%Y Y")
    #     ]
    # )
    fig.update_layout(
        title=f"{dirs} {hd(voldir,sign=True)} all_period:{all_period/24}d end_price: {end_price} " +
        f"VWAP({vwap_info_w}):{hd(end_price-df['vwap_1W'][-1],1,True)} " +
        f"VWAP({vwap_info_d}):{hd(end_price-df['vwap_1D'][-1],1,True)} " +
        f"VWMA({vwap_info_i}h):{hd(end_price-df['vwap_'+str(vwap_info_i)][-1],1,True)} ",
        xaxis_title="Date",
        yaxis_title=f"{crypto}",
        height=640,
        xaxis_rangeslider_visible=False,
        # legend_orientation="h",
        legend=dict(x=0, y=1, orientation='h'),
        hovermode="x",
    )
    # pio.write_image(fig=fig, file=f'btc{intervals}.jpg', format='jpg')
    # pio.write_json(fig=fig, file=f'btc{intervals}.json', pretty=True)
    # print(but, intervals)
    return fig


if __name__ == '__main__':
    app.run_server(port=8052, debug=False, use_reloader=True)
