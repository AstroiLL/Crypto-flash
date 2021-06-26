from datetime import datetime, timedelta
import dash
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import re

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
start = datetime.now()-timedelta(days=10)

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
app.layout = html.Div([
    dcc.RadioItems(
        id='Period',
        options=[{'label': i, 'value': i} for i in ['1d', '1h', '1m']],
        value='1h'
    ),
    dcc.DatePickerSingle(
        id='date',
        min_date_allowed=datetime(2019, 1, 1),
        max_date_allowed=datetime.now(),
        # initial_visible_month=start,
        number_of_months_shown=3,
        # persistence=False,
        date=start
    ),
    html.Div(id='output-date')
])


@app.callback(
    Output('output-date', 'children'),
    [Input('Period', 'value'),
     Input('date', 'date')])
def update_output(period, date):
    string_prefix = f'Для {period} начало графика '
    if date is not None:
        today = datetime.now()
        if period == '1d':
            start = today-timedelta(days=50)
        elif period == '1h':
            start = today-timedelta(days=10)
        elif period == '1m':
            start = today
        else:
            return None
        # date = start
        dates = str(start)
        # dates = dt.strptime(re.split('T| ', dates)[0], '%Y-%m-%d')
        # date_string = dates.strftime('%Y-%m-%d 00:00:00.0')
        return string_prefix + dates


if __name__ == '__main__':
    app.run_server(debug=True)
