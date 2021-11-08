# Plotly Dash #11
import dash
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import plotly.express as px
import requests
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash import dash_table

""" READ DATA """

response = requests.get('http://asterank.com/api/kepler?query={}&limit=2000')
df = pd.json_normalize(response.json())
df = df[df['PER'] > 0]
df['KOI'] = df['KOI'].astype(int, errors='ignore')

# create star size category
bins = [0, 0.8, 1.2, 100]
names = ['small', 'similar', 'bigger']
df['StarSize'] = pd.cut(df['RSTAR'], bins, labels=names)

# Temp bins
tp_bins = [0, 200, 400, 500, 5000]
tp_labels = ['low', 'optimal', 'high', 'extreme']
df['temp'] = pd.cut(df['TPLANET'], tp_bins, labels=tp_labels)

# Size bins
rp_bins = [0, 0.5, 2, 4, 100]
rp_labels = ['low', 'optimal', 'high', 'extreme']
df['gravity'] = pd.cut(df['RPLANET'], rp_bins, labels=rp_labels)

# Estimate obj status
df.loc[:, 'status'] = np.where(
    (df['temp'] == 'optimal') &
    (df['gravity'] == 'optimal'),
    'promising', ''
)
df.loc[:, 'status'] = np.where(
    (df['temp'] == 'optimal') &
    (df['gravity'].isin(['low', 'high'])),
    'challenging', df['status']
)
df.loc[:, 'status'] = np.where(
    (df['gravity'] == 'optimal') &
    (df['temp'].isin(['low', 'high'])),
    'challenging', df['status']
)
df['status'] = df.status.fillna('extreme')

# Relativ dist
df.loc[:, 'relative_dist'] = df['A'] / df['RSTAR']

# Filters
options = []
for k in names:
    options.append({'label': k, 'value': k})

star_size_selector = dcc.Dropdown(
    id='star-selector',
    options=options,
    value=['small', 'similar', 'bigger'],
    multi=True
)

rplanet_selector = dcc.RangeSlider(
    id='range-slider',
    min=min(df['RPLANET']),
    max=max(df['RPLANET']),
    marks={5: '5', 10: '10', 20: '20'},
    step=1,
    value=[min(df['RPLANET']), max(df['RPLANET'])]
)

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY]
)

# tabs content
tab1_content = [
    # charts
    dbc.Row(
        [
            dbc.Col(html.Div(id='dist-temp-chart'), md=6),
            dbc.Col(html.Div(id='celestial-chart'), md=6)
        ], style={'margin-top': 20}
    ),
    dbc.Row(
        [
            dbc.Col(html.Div(id='relative-dist-chart'), md=6),
            dbc.Col(html.Div(id='mstar-tstar-chart'), md=6),
        ]
    )

]
tab2_content = [dbc.Row(html.Div(id='data-table'), style={'margin-top': 20})]

""" LAYOUT """

app.layout = html.Div(
    [
        dbc.Row(
            html.H1('Plotly Dash #11'),
            style={'margin-bottom': 40}
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div('Select range RPLANET'),
                        html.Div(rplanet_selector)
                    ],
                    width={'size': 2}
                ),
                dbc.Col(
                    [
                        html.Div('Star size'),
                        html.Div(star_size_selector)
                    ],
                    width={'size': 3, 'offset': 1}
                ),
                dbc.Col(dbc.Button('Apply', id='submit-val', n_clicks=0))
            ],
            style={'margin-bottom': 40}
        ),
        dbc.Tabs(
            [
                dbc.Tab(tab1_content, label='Charts'),
                dbc.Tab(tab2_content, label='Data'),
                dbc.Tab(html.Div('About Page'), label='About'),
            ]
        )
    ],
    style={'margin-left': '80px', 'margin-right': '80px'}
)

""" CALLBACK """


@app.callback(
    [Output(component_id='dist-temp-chart', component_property='children'),
     Output(component_id='celestial-chart', component_property='children'),
     Output(component_id='relative-dist-chart', component_property='children'),
     Output(component_id='mstar-tstar-chart', component_property='children'),
     Output(component_id='data-table', component_property='children')],
    [Input(component_id='submit-val', component_property='n_clicks')],
    [State(component_id='range-slider', component_property='value'),
     State(component_id='star-selector', component_property='value')]
)
def update_dist_temp_chart(n, radius_range, star_size):
    chart_data = df[(df['RPLANET'] > radius_range[0]) &
                    (df['RPLANET'] < radius_range[1]) &
                    (df['StarSize'].isin(star_size))]
    if len(chart_data) == 0:
        return [html.Div('No data selected') for _ in range(5)]
    fig1 = px.scatter(chart_data, x='TPLANET', y='A', color='StarSize')
    html1 = [html.Div('Planet temp ~ dist from the star'),
             dcc.Graph(figure=fig1)]
    fig2 = px.scatter(chart_data, x='RA', y='DEC', size='RPLANET', color='status')
    html2 = [html.Div('Pos on Celestia Sphere'),
             dcc.Graph(figure=fig2)]
    # relative dist chart
    fig3 = px.histogram(
        chart_data, x='relative_dist',
        color='status', barmode='overlay', marginal='violin'
    )
    fig3.add_vline(x=1, y0=0, annotation_text='Earth', line_dash='dot')
    html3 = [html.Div('Relative Dist'),
             dcc.Graph(figure=fig3)]
    fig4 = px.scatter(chart_data, x='MSTAR', y='TSTAR', size='RPLANET', color='status')
    html4 = [html.Div('Star mass ~ Star Temp'),
             dcc.Graph(figure=fig4)]

    # RAW data table
    raw_data = chart_data.drop(['relative_dist',
                                'StarSize',
                                'ROW',
                                'temp',
                                'gravity'], axis=1)
    tbl = dash_table.DataTable(data=raw_data.to_dict('records'),
                               columns=[{'name': i, 'id': i} for i in raw_data.columns],
                               style_data={'width': '100px', 'maxwidth': '100px', 'minwidth': '100px'},
                               style_header={'text-align': 'center'},
                               page_size=40)
    html5 = [html.P('Raw Data'), tbl]

    return html1, html2, html3, html4, html5


if __name__ == '__main__':
    app.run_server(debug=True)
