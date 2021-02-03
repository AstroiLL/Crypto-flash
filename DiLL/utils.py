"""
iLLs functions
"""
import os
import os.path

# import ccxt
import joblib  # for persistence
import matplotlib.dates as mdates
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from datetime import datetime as dt
import pandas_ta as ta

# from sqlalchemy import create_engine

# Констатнты
D1 = 86400000  # ms
H1 = 3600000  # ms
M1 = 60000  # ms
M5 = M1 * 5


# H1s = 3600  # s

def ep(*args):
    """
    print and exit
    """
    print(args)
    exit()


def SMA(x: pd.Series, period: int = 20) -> pd.Series:
    """
    Вычеслить скользящую среднюю для серии
    :param x: Series
    :param period: Период sma
    :return: Series
    """
    return x.rolling(period).mean()


def begin_today():
    today = dt.utcnow()
    return today.combine(today.date(), today.min.time())


# def VWAP(df):
#     """
#     Вычеслить средневзвешенную среднюю по объему за день (устарело)
#     """
#     def __vwap(dff):
#         q = dff['Volume'].values
#
#     today = dtscalcnow()
#     return today.combine(today.date(), today.min.time())
#
#
# def VWAP(df):
#     """
#     Вычеслить средневзвешенную среднюю по объему за день (устарело)
#     """
#     def __vwap(dff):
#         q = dff
#         p = dff['Open'].values
#         return dff.assign(vwap=(p * q).cumsum() / q.cumsum())
#     return df.groupby(df.index.date, group_keys=False).apply(__vwap)


def vwap(df, period='1D', price='Open'):
    """
    Вычеслить средневзвешенную среднюю по объему за фиксированный период 1MN 1W 1D
    и записать в DataFrame в поле с именем vwap_{period}
    """

    def _vwap_ass(_df):
        q = _df['Volume'].values
        p = _df[price].values
        if len(price) == 2:
            p = (_df[price[0]].values + _df[price[1]].values) / 2
        elif len(price) == 3:
            p = (_df[price[0]].values + _df[price[1]].values + _df[price[2]].values) / 3
        return _df.assign(vwap=(p * q).cumsum() / q.cumsum())

    group_index = None
    if period == '1MN':
        group_index = df.index.month
    elif period == '1W':
        group_index = df.index.isocalendar().week
    elif period == '1D':
        group_index = df.index.date
    else:
        # TODO price list
        df['mul'] = df[price] * df['Volume']
        df['mul_sum'] = df['mul'].rolling(period).sum()
        df['div'] = df['Volume'].rolling(period).sum()
        df['vwap'] = df['mul_sum'] / df['div']
        df.rename(columns={'vwap': f'vwap_{period}'}, inplace=True)
        return df
    df = df.groupby(group_index, group_keys=False).apply(_vwap_ass)
    df.rename(columns={'vwap': f'vwap_{period}'}, inplace=True)
    return df


def wvwma(src, vol, length=48):
    """WVwma"""
    return ta.wma(src*vol, length=length)/ta.wma(vol, length=length)


def hd(x, precision=2, sign=False):
    """
    Округлить большие числа и преобразовать в строку, в удобном для восприятия человеком виде.
    Добавить после числа:
    G для миллиардов
    M для миллионов
    k для тысяч
    :param x: число для преобразования
    :param precision: число знаков после точки (пример для 2: 3 861 647 -> 3.86M, по умолчанию 2)
    :param sign: отображать или нет знак +
    :return: строку вида "3.86M"
    """
    if precision < 0: return str(x)
    suf = ''
    pref = ''
    if sign: pref = '+'
    x = float(x)
    y = x
    if x < 0:
        x = abs(x)
        y = x
        pref = '-'
    if x >= 1e9:
        y = x / 1e9
        y = round(y, precision)
        suf = 'G'
    elif x >= 1e6:
        y = x / 1e6
        y = round(y, precision)
        suf = 'M'
    elif x >= 1000:
        y = x / 1000
        y = round(y, precision)
        suf = 'k'
    return pref + f'{y:.{precision}f}' + suf


def lev2font(x, max_v, lev_m, max_f, min_f):
    # if not isinstance(x,type(float)):
    #     return min_f
    # ep(x, max_v, lev_m, max_f, min_f)
    x = float(x)
    # print(x)
    font = int((((max_f - min_f) * (x - max_v * lev_m)) / (max_v * (1 - lev_m))) + min_f)
    return font if font >= 0 else 0


def wa(group):
    group['Price'] = group['Price'] * group['Size'] / group['Size'].sum()
    # group['fairePrice'] = group['fairePrice'] * group['Size'] / group['Size'].sum()
    return group


def ohlc2(axes, prices: pd.DataFrame, colorup='blue', colordown='red'):
    width = 0.0001
    width2 = 0.0004
    pricesup = prices[prices['Close'] >= prices['Open']]
    pricesdown = prices[prices['Close'] < prices['Open']]

    axes.bar(pricesup.index, pricesup['Close'] - pricesup['Open'], width, bottom=pricesup['Open'], color=colorup)
    # axes.bar(pricesup.index, pricesup['High'] - pricesup['Close'], width2, bottom=pricesup['Close'], color=colorup)
    # axes.bar(pricesup.index, pricesup['Low'] - pricesup['Open'], width2, bottom=pricesup['Open'], color=colorup)

    axes.bar(pricesdown.index, pricesdown['Close'] - pricesdown['Open'], width, bottom=pricesdown['Open'],
             color=colordown)
    # axes.bar(pricesdown.index, pricesdown['High'] - pricesdown['Open'], width2, bottom=pricesdown['Open'], color=colordown)
    # axes.bar(pricesdown.index, pricesdown['Low'] - pricesdown['Close'], width2, bottom=pricesdown['Close'], color=colordown)


def ohlc_j(ax, quotes, width=0.2, colorup='blue', colordown='red',
           alpha=1.0):
    """
    Plot the time, open, high, low, close as a vertical line ranging
    from low to high.  Use a rectangular bar to represent the
    open-close span.  If close >= open, use colorup to color the bar,
    otherwise use colordown

    Parameters
    ----------
    ax : `Axes`
        an Axes instance to plot to
    quotes : sequence of quote sequences
        data to plot.  time must be in float date format - see date2num
        (time, open, high, low, close, ...)
    width : float
        fraction of a day for the rectangle width
    colorup : color
        the color of the rectangle where close >= open
    colordown : color
         the color of the rectangle where close <  open
    alpha : float
        the rectangle alpha level

    Returns
    -------
    ret : tuple
        returns (lines, patches) where lines is a list of lines
        added and patches is a list of the rectangle patches added

    """

    OFFSET = width / 2.0
    lines = []
    patches = []
    for q in quotes:
        t, open, high, low, close = q[:5]
        td = mdates.date2num(t.to_pydatetime())

        if close >= open:
            color = colorup
            lower = open
            height = close - open
        else:
            color = colordown
            lower = close
            height = open - close

        vline = Line2D(
            xdata=(t, t), ydata=(low, high),
            color=color,
            linewidth=0.5,
            antialiased=True,
        )

        rect = Rectangle(
            # xy=(t, lower),
            xy=(td - OFFSET, lower),
            width=width,
            height=height,
            facecolor=color,
            edgecolor=color,
        )
        rect.set_alpha(alpha)

        lines.append(vline)
        patches.append(rect)
        ax.add_line(vline)
        ax.add_patch(rect)
    ax.autoscale_view()

    return lines, patches


def ohlc_ha(ax, quotes, width=0.2, colorup='blue', colordown='red',
            alpha=1.0):
    """
    Plot the time, open, high, low, close as a vertical line ranging
    from low to high.  Use a rectangular bar to represent the
    open-close span.  If close >= open, use colorup to color the bar,
    otherwise use colordown

    Parameters
    ----------
    ax : `Axes`
        an Axes instance to plot to
    quotes : sequence of quote sequences
        data to plot.  time must be in float date format - see date2num
        (time, open, high, low, close, ...)
    width : float
        fraction of a day for the rectangle width
    colorup : color
        the color of the rectangle where close >= open
    colordown : color
         the color of the rectangle where close <  open
    alpha : float
        the rectangle alpha level

    Returns
    -------
    ret : tuple
        returns (lines, patches) where lines is a list of lines
        added and patches is a list of the rectangle patches added

    """

    OFFSET = width / 2.0
    lines = []
    patches = []
    open_p = quotes[0][1]
    close_p = quotes[0][4]
    # ep(open_p)
    for q in quotes:
        t, open, high, low, close = q[:5]
        td = mdates.date2num(t.to_pydatetime())

        closeh = (open + close + high + low) / 4
        openh = (open_p + close_p) / 2
        open_p = openh
        close_p = closeh
        highh = max(high, openh, closeh)
        lowh = min(low, openh, closeh)
        open = openh
        close = closeh
        high = highh
        low = lowh

        if close >= open:
            color = colorup
            lower = open
            height = close - open
        else:
            color = colordown
            lower = close
            height = open - close

        vline = Line2D(
            xdata=(t, t), ydata=(low, high),
            color=color,
            linewidth=0.5,
            antialiased=True,
        )

        rect = Rectangle(
            # xy=(t, lower),
            xy=(td - OFFSET, lower),
            width=width,
            height=height,
            facecolor=color,
            edgecolor=color,
        )
        rect.set_alpha(alpha)

        lines.append(vline)
        patches.append(rect)
        ax.add_line(vline)
        ax.add_patch(rect)
    ax.autoscale_view()

    return lines, patches


# #############################################################################
# Persist a model and create predictions after re-loading it
def check_pkl(name="arima.pkl"):
    return os.path.isfile(name)


def del_pkl(name="arima.pkl"):
    os.unlink(name)


def save_pkl(arima, name="arima.pkl"):
    # Pickle it
    joblib.dump(arima, name, compress=3)
    print(f'Saved {name}')


def load_pkl(name="arima.pkl"):
    # Load the model up, create predictions
    arima = joblib.load(name)
    print(f'Loaded {name}')
    return arima


"""
class Disk():
    def check_(self):
        return os.path.isfile(self.name)

    def load(self):
        if check_():
            arima = joblib.load(self.name)
            self.loaded = True
            print(f'Loaded {self.name}')
        return arima

    def __init__(self, name="arima.pkl", new=True):
        self.name = name
        self.var = None
        self.loaded = False
        if not new:
            if check_():
                self.var = load()
                self.loaded = True

    def delete(self):
        if check_():
            os.unlink(self.name)
            print(f'Deleted {self.name}')

    def save(self, var):
        if self.loaded:
            joblib.dump(var, self.name, compress=3)
            print(f'Saved {self.name}')
"""


def HA(dataframe):
    df = dataframe.copy()

    df['HA_Close'] = (df.Open + df.High + df.Low + df.Close) / 4

    # df.reset_index(inplace=True)

    ha_open = [(df.Open[0] + df.Close[0]) / 2]
    [ha_open.append((ha_open[i] + df.HA_Close.values[i]) / 2) for i in range(0, len(df) - 1)]
    df['HA_Open'] = ha_open

    # df.set_index('index', inplace=True)

    df['HA_High'] = df[['HA_Open', 'HA_Close', 'High']].max(axis=1)
    df['HA_Low'] = df[['HA_Open', 'HA_Close', 'Low']].min(axis=1)
    df.drop(columns=['Open', 'High', 'Low', 'Close'], inplace=True)
    df.rename(columns={'HA_Open': 'Open', 'HA_High': 'High', 'HA_Low': 'Low', 'HA_Close': 'Close'}, inplace=True)
    return df
