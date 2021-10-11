import time
# import os
# from dotenv import load_dotenv
from datetime import datetime, timedelta

import ccxt
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import Session, sessionmaker
# from MLDiLL.utils import VWAP, VWAP_d, VWAP_p

# from .env import mysql_url
sql_url = "mysql://bitok:bitok@10.10.10.200:3307"
# mysql_url = 'mysql://user:pass@127.0.0.1:3307'
# mysql_url = os.environ['MYSQL_URL']

# Константы
D1 = 86400000  # ms
H1 = 3600000  # ms
M1 = 60000  # ms
# M5 = M1 * 5
# H1s = 3600  # s

dict_period = {'1m': M1, '1h': H1, '1d': D1}
tz = 0


class Exchange:
    # Работа с биржей

    def __init__(self, exchange='BITMEX', crypto='BTC/USD', period='1m', verbose=True):
        self.exchange = exchange
        self.exchange_conn = None
        self.crypto = crypto
        self.period = period
        self.verbose = verbose
        self.availability = True
        if self.exchange == 'BITMEX':
            self.exchange_conn = ccxt.bitmex(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
        elif self.exchange == 'BINANCE':
            self.exchange_conn = ccxt.binance(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
        else:
            print(f'Incorrect exchange "{self.exchange}", seting "BITMEX"')
            self.exchange_conn = ccxt.bitmex(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
            self.exchange = 'BITMEX'
        # markets = self.exchange_conn.load_markets()
        # if self.verbose:
        # print(self.exchange_conn.id, self.exchange_conn.markets, self.exchange_conn.markets.keys())
        try:
            if self.verbose: print(
                f"Test_get_from_exch {self.exchange}.{self.crypto}.{self.period} limit 1"
            )
            self.exchange_conn.fetch_ohlcv(self.crypto, self.period, limit=1)
        except:
            print(f'#1 Error connect exchange {self.exchange}')
            self.availability = False

    # Получение данных с биржи
    def get(self, since=None, limit=500):
        """Получить котировки с биржи от даты since количеством limit.
            Если не указано since то берется limit до конца.
            since в формате %Y-%m-%d %H:%M:%S
            На выходе получаем DataFrame OHLCV
        """
        limit = limit
        if since is None:
            # Вычисляем время начала загрузки данных как разницу текущего времени и количества баров
            since_exch = self.exchange_conn.milliseconds() - dict_period[self.period] * limit
        else:
            # Вычисляем время начала загрузки данных из входного времени
            since_exch = self.exchange_conn.parse8601(since.strftime('%Y-%m-%d %H:%M:%S'))
        if self.verbose: print('Since', self.exchange_conn.iso8601(since_exch))
        df_app = None
        while limit > 0:
            time.sleep(self.exchange_conn.rateLimit // 1000)
            if self.verbose: print('Load limit ', limit, self.period)
            lmt = limit if limit <= 750 else 750
            try:
                if self.verbose: print(
                    f"Get_from_exch {self.exchange}.{self.crypto}.{self.period} since {self.exchange_conn.iso8601(since_exch)} limit {lmt}"
                )
                fetch = self.exchange_conn.fetch_ohlcv(self.crypto, self.period, since=since_exch, limit=lmt)
            except:
                print(f'#2 Error fetch from {self.exchange}')
                self.availability = False
            else:
                df_fetch = pd.DataFrame(fetch, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df_fetch['Date'] = pd.to_datetime(df_fetch['Date'], unit='ms', infer_datetime_format=True)
                if df_app is None:
                    df_app = df_fetch
                else:
                    df_app = df_app.append(df_fetch)
                # print(df_app)
            since_exch += dict_period[self.period] * lmt
            limit -= lmt
            # if limit > 0: time.sleep(exchange.rateLimit // 100)
        return df_app




class CryptoA:
    """
    Получаем котировки с криптовалютных бирж и записываем в базу SQL, чтобы легко их получать

    Биржи BITMEX BINANCE
    Периоды 1d 1h 1m
    """

    def __init__(self, exchange='BITMEX', crypto='BTC/USD', period='1m', update=False, verbose=True):
        self.df = pd.DataFrame()
        self.exchange = exchange
        self.crypto = crypto
        self.period = period
        self.update = update
        self.verbose = verbose
        self.availability_exch = True
        self.limit = None
        self.last_date = None
        self.conn_str = None
        self.conn = None
        self.session = None
        self.new = True
        self.metadata_obj = MetaData()

    def load(self, exchange=None, crypto=None, period=None, update=None, limit=None):
        """Открываем базу и загружаем новые данные если не изменились
            параметры exchange crypto period
        """
        self.limit = None
        if exchange is not None:
            if self.exchange != exchange:
                self.new = True
                self.exchange = exchange
        if crypto is not None:
            if self.crypto != crypto:
                self.new = True
                self.crypto = crypto
        if period is not None:
            if self.period != period:
                self.new = True
                self.period = period
        if update is not None: self.update = update
        if self.exchange != 'BITMEX' and self.exchange != 'BINANCE':
            print(f'Incorrect exchange "{self.exchange}", setting "BITMEX"')
            self.exchange = 'BITMEX'
        if self.verbose: print(f'==============\nInit {self.exchange}.{self.crypto} {self.period}')
        self.conn_str = f'{sql_url}/{self.exchange}.{self.crypto}'
        if self.verbose: print(self.conn_str)
        try:
            self.conn = self._connect_()
            self.table = Table(self.period, self.metadata_obj, autoload_with=self.conn)
            self.session = Session(self.conn)
        except:
            print(f'No base {self.exchange}.{self.crypto}')
            if not self.update:
                print('#2 Updates disabled. Exiting.')
                exit(2)
            self._create_base_()
        # else:
        #     self.conn.close()
        #     self.conn = None
        count_records = self._get_count_records_()
        if count_records == 0:
            print(f'#3 Empty base {self.exchange}.{self.crypto}.{self.period}')
            if not self.update: exit(3)
            self._update_base_()
            count_records = self._get_count_records_()
            if count_records == 0:
                print(f'#4 Error filling empty base {self.exchange}.{self.crypto}.{self.period}')
                exit(4)
        if self.verbose: print(f"Table {self.period} has total {count_records} records")
        self._load_data_()

    def _connect_(self):
        return create_engine(self.conn_str, pool_pre_ping=True, echo=self.verbose).connect()

    def _get_count_records_(self):
        """Количество котировок в базе"""
        if self.verbose:
            count_records = self._get_count_records_()
            print(f"Table {self.period} has total {count_records} records")
            print(f"Load {self.crypto} from SQL {self.period}")
        count = self.session.query(self.table).count()
        if self.verbose: print(f"Записей: {count}")
        return count

    def _load_data_(self):
        """Загрузить из базы limit котировок"""
        if self.new:
            pass
        else:
            pass
        if self.limit is None:
            record = self.session.query(self.table).all()
            df = pd.DataFrame(record, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            s = df.select_dtypes(include='object').columns
            df[s] = df[s].astype("float")
            if self.verbose: print(df.dtypes)
            self.limit = df.shape[0]
        else:
            record = self.session.query(self.table).limit(self.limit).all()
            # print(record)
            df = pd.DataFrame(record, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            s = df.select_dtypes(include='object').columns
            df[s] = df[s].astype("float")
            if self.verbose: print(df.dtypes)
            self.limit = min(df.shape[0], self.limit)
        self.last_date = df.at[0, 'Date']
        if self.verbose: print("Last date from mySQL", self.last_date)
        df.sort_values('Date', ascending=True, inplace=True)
        df.set_index('Date', drop=True, inplace=True)
        df.index += timedelta(hours=tz)
        if self.verbose: print(f'Loaded {self.limit} bars {self.period}')
        self.df = df
        return df


if __name__ == '__main__':
    # cry = Exchange()
    # df = cry.get(limit=60)
    # print('Exchange')
    # print(df)
    cry_1m = CryptoA(period='1m', verbose=True)
    df = cry_1m.load(limit=6)
    # print('SQL')
    print(df)
