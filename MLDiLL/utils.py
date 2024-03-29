"""
iLLs functions
"""
import pandas as pd
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
    Вычислить скользящую среднюю для серии
    :param x: Series
    :param period: Период sma
    :return: Series
    """
    return x.rolling(period).mean()


def begin_today():
    today = dt.utcnow()
    return today.combine(today.date(), today.min.time())


def vwap(df, period='1D', price='Open'):
    """
    Вычислить средневзвешенную среднюю по объему за фиксированный период 1MN 1W 1D
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


def sma(src, length=48):
    """
    sma - простая скользящая средняя за период
    """
    return ta.sma(src, length=length)


def wma(src, length=48):
    """
    wma - взвешенная скользящая средняя за период
    """
    return ta.wma(src, length=length)


def wvsma(src, vol, length=48):
    """
    WVsma - объемно-взвешенная скользящая средняя за период
    """
    return ta.sma(src*vol, length=length)/ta.sma(vol, length=length)


def wvwma(src, vol, length=48):
    """
    WVwma - взвешенная объемно-взвешенная скользящая средняя за период
    """
    # print(src,vol,length)
    return ta.wma(src*vol, length=length)/ta.wma(vol, length=length)

def pvt(src, vol, length=48):
    """
    PVT - Price Volume Trend
    """
    # print(src,vol,length)
    pass
    # return ta.wma(src*vol, length=length)/ta.wma(vol, length=length)


def hd(x, precision=2, sign=False):
    """
    Преобразовать большие числа в короткую строку в удобном виде для восприятия.
    Добавить после числа:
    G для миллиардов
    M для миллионов
    k для тысяч
    :param x: число для преобразования
    :param precision: число знаков после точки (пример для precision=2: 3 861 647 -> 3.86M), по умолчанию 2
    :param sign: отображать или нет знак +, по умолчанию не отображать
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
    """
    Преобразовать уровень в размер фонта
    :param x:
    :param max_v:
    :param lev_m:
    :param max_f:
    :param min_f:
    :return:
    """
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

def HA(dataframe):
    """
    Преобразовать dataframe Candlestic в HeikenAshi
    :param dataframe:
    :return:
    """
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
