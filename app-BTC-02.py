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

""" READ DATA """
PERIOD = '1m'
LIMIT = 240
WVW = 24
cry = CryptoA(period=PERIOD, verbose=False)
cry.load(limit=LIMIT)
# df = cry.df

# create category
# bins = [0, 0.8, 1.2, 100]
# names = ['small', 'similar', 'bigger']
# df['StarSize'] = pd.cut(df['RSTAR'], bins, labels=names)


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
        )
    )
)
# COLOR_STATUS_VALUES1 = {'extreme': 'lightgray', 'challenging': '#1F85DE', 'promising': '#F90F04'}
vol_level_selector = dcc.Slider(
    id='vol-level-slider',
    min=0,
    max=max(cry.df['Volume']),
    # marks={5: '5', 10: '10', 20: '20'},
    # step=1,
    value=0,
    tooltip={'always_visible': True, 'placement': 'bottom'},
    persistence=True, persistence_type='local',
)
refresh = html.Div(
    [
        dbc.Row([
            dbc.Col(dbc.Button('Refresh', id="refresh", color="primary", outline=True), width=1),
            dbc.Col(dcc.Loading(html.Div(id='out-btc')), width=1),
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

""" LAYOUT """

app.layout = html.Div(
    [
        interval_reload,
        dbc.Row(
            html.H1('BTC Splash #02'),
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
def update_chart(n, vol_level, nn):
    if cry.df.empty:
        cry.load(limit=LIMIT)
    df = cry.df
    # Фильтровать по критерию Vol >= уровень
    df['max_vol_color'] = 'gray'
    df['max_vol'] = df['Volume'].where(df['Volume'] < vol_level, 13).where(df['Volume'] >= vol_level, 5)
    # df['max_vol_color'] = df['Volume'].where(df['Volume'] < vol_level, 'blue').where(df['Volume'] >= vol_level, 'red')
    df['max_vol_color'] = df['Open'].where(df['Open'] >= df['Close'], 'blue').where(df['Open'] < df['Close'], 'red')
    out_btc = f"{hd(vol_level)} {round((vol_level / df['Volume'].max()) * 100)} %"
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

    fig.update_layout(template=CHARTS_TEMPLATE)
    html1 = [html.Div('BTC/USD ' + PERIOD, className='header_plots'),
             dcc.Graph(figure=fig)]

    return html1, out_btc


if __name__ == '__main__':
    app.run_server(debug=True)
