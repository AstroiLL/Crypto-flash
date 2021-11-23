# Plotly Dash #13
import dash
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table
from dash import dcc, html
from dash.dependencies import Input, Output, State

from MLDiLL.cryptoA import CryptoA
from MLDiLL.utils import hd, HA, wvwma

""" READ DATA """
cry = CryptoA(period='1h', verbose=False)
cry.load(limit=60)
df = cry.df

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
    max=max(df['Volume']),
    # marks={5: '5', 10: '10', 20: '20'},
    # step=1,
    value=0,
    persistence=True, persistence_type='local',
)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY]
)

""" LAYOUT """

app.layout = html.Div(
    [
        dbc.Row(
            html.H1('BTC Dash #01'),
            style={'margin-bottom': 40}
        ),
        dbc.Row(
            dbc.Button('Apply', id='submit-val', n_clicks=0),
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
    Output(component_id='btc-chart', component_property='children'),
    [Input(component_id='submit-val', component_property='n_clicks')],
    [State(component_id='vol-level-slider', component_property='value')]
)
def update_chart(n, vol_level):
    # cry.load(limit=60)
    # df = cry.df
    # Фильтровать по критерию Vol >= уровень
    df['max_vol_color'] = 'gray'
    df['max_vol'] = df['Volume'].where(df['Volume'] < vol_level, 13).where(df['Volume'] >= vol_level, 5)
    # df['max_vol_color'] = df['Volume'].where(df['Volume'] < vol_level, 'blue').where(df['Volume'] >= vol_level, 'red')
    df['max_vol_color'] = df['Open'].where(df['Open'] >= df['Close'], 'blue').where(df['Open'] < df['Close'], 'red')
    print(hd(vol_level), round((vol_level/df['Volume'].max())*100), '%')

    # print(n)
    fig1 = go.Figure()
    fig1.add_trace(
        go.Scatter(
            x=df.index, y=df['Open'], mode='lines+markers',
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
    fig1.update_layout(template=CHARTS_TEMPLATE)
    html1 = [html.Div('BTC/USD', className='header_plots'),
             dcc.Graph(figure=fig1)]

    return html1


if __name__ == '__main__':
    app.run_server(debug=True)
