# Plotly Dash #13
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table
from dash import dcc, html
from dash.dependencies import Input, Output, State

from MLDiLL.cryptoA import CryptoA
from MLDiLL.utils import hd, wvwma

#TODO список линий и SMA WVWMA
#TODO сохранение параметров
#TODO лента объемов вокруг SMA шириной в зависимости от объема

# READ DATA

PERIOD = '1m'
LIMIT = 240
WVW = 24
VERSION = 'BTC Splash #04'
cry = CryptoA(period=PERIOD, verbose=False)
cry.load(limit=LIMIT)
# df = cry.df

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
        # margin={"r": 0, "t": 1, "l": 0, "b": 0}

    )
)
# COLOR_STATUS_VALUES1 = {'extreme': 'lightgray', 'challenging': '#1F85DE', 'promising': '#F90F04'}
vol_level_selector = dcc.RangeSlider(
    id='vol-level-slider',
    min=0,
    max=max(cry.df['Volume']),
    value=[0, 1000000],
    # allowCross=False,
    pushable=1000000,
    tooltip={'always_visible': True, 'placement': 'bottom'},
    persistence=True, persistence_type='local',
)
refresh = html.Div(
    [
        dbc.Row([
            dbc.Col(dbc.Button('Refresh', id="refresh", color="primary", outline=True), width=1),
            dbc.Col(dcc.Loading(html.Div(id='out-btc'))),
            dbc.Col(html.Div(id='out-dump'), width=0),
        ],
            justify="start",
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
        interval_reload,
        dbc.Row(
            html.H1(VESION),
            style={'margin-bottom': 40}
        ),
        dbc.Row(
            html.Div(refresh),
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
    Output(component_id='out-dump', component_property='children'),
    [Input(component_id='refresh', component_property='n_clicks'),
     # Input(component_id='vol-level-slider', component_property='value'),
     Input('interval-reload', 'n_intervals')]
)
def update_df(n, nn):
    cry.load(limit=LIMIT)
    # df = cry.df
    return ' '


@app.callback(
    [Output(component_id='btc-chart', component_property='children'),
     Output(component_id='out-btc', component_property='children')],
    [Input(component_id='refresh', component_property='n_clicks'),
     Input(component_id='vol-level-slider', component_property='value'),
     Input('interval-reload', 'n_intervals')]
)
def update_chart(n, range_vol_level, nn):
    if cry.df.empty:
        cry.load(limit=LIMIT)
    df = cry.df
    vol_level0 = range_vol_level[0]
    vol_level1 = range_vol_level[1]
    # Фильтровать по критерию Vol >= уровень
    df['max_vol'] = 5
    df['max_vol'] = df['max_vol'].where(df['Volume'] < vol_level0, 13).where(df['Volume'] < vol_level1, 21)
    df['max_vol_color'] = 'gray'
    df['max_vol_color'] = df['Open'].where(df['Open'] >= df['Close'], 'blue').where(df['Open'] < df['Close'], 'red')
    out_btc = f"Max Vol: {hd(df['Volume'].max())} Vol0: {hd(vol_level0)} {round((vol_level0 / df['Volume'].max()) * 100)} %" \
              f" Vol1: {hd(vol_level1)} {round((vol_level1 / df['Volume'].max()) * 100)} %"
    # print(df)
    df['wvwma'] = wvwma(df['Open'], df['Volume'], length=WVW)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['Open'],
            name='BTC',
            mode='lines+markers',
            marker=dict(
                size=df['max_vol'],
                color=df['max_vol_color'],
            ),
            line=dict(
                # size=1,
                color='grey',
            ),
        )
    )
    # VWMA()
    fig.add_trace(
        go.Scatter(
            x=df.index, y=df['wvwma'], mode='lines', name='WVWMA',
            # hoverinfo='none',
            line=dict(
                # size=4,
                color='black',
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
            domain={'x': [0, 0], 'y': [0, 0]}
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

    fig.update_layout(template=CHARTS_TEMPLATE)
    html1 = [html.Div('BTC/USD ' + PERIOD, className='header_plots'),
             dcc.Graph(figure=fig)]

    return html1, out_btc


if __name__ == '__main__':
    app.run_server(debug=True)
