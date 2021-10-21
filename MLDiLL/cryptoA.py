import time
# import os
# from dotenv import load_dotenv
from datetime import timedelta

import ccxt
import pandas as pd
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import Session

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
                f"#64 Test_get_from_exch {self.exchange}.{self.crypto}.{self.period} limit 1"
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
        if self.verbose: print('#85 Since', self.exchange_conn.iso8601(since_exch))
        df_app = None
        while limit > 0:
            time.sleep(self.exchange_conn.rateLimit // 1000)
            if self.verbose: print('#89 Load limit ', limit, self.period)
            lmt = limit if limit <= 750 else 750
            try:
                if self.verbose: print(
                    f"#93 Get_from_exch {self.exchange}.{self.crypto}.{self.period} since {self.exchange_conn.iso8601(since_exch)} limit {lmt}"
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
        self.count = 0
        self.table = None
        self.metadata_obj = MetaData()

    # TODO default parameters попробовать убрать None
    def load(self, exchange=None, crypto=None, period=None, update=None, limit=1):
        """Открываем базу и загружаем новые данные если не изменились
            параметры exchange crypto period
        """
        if limit == 'ALL' or limit is None:
            self.limit = None
        else:
            self.limit = limit
        if exchange is not None and self.exchange != exchange:
            self.new = True
            self.exchange = exchange
            if self.exchange != 'BITMEX' and self.exchange != 'BINANCE':
                print(f'Incorrect exchange "{self.exchange}", setting "BITMEX"')
                self.exchange = 'BITMEX'
        if crypto is not None and self.crypto != crypto:
            self.new = True
            self.crypto = crypto
        if period is not None and self.period != period:
            self.new = True
            self.period = period
        if update is not None: self.update = update
        if self.new: self.session = None
        self._get_count_records_()
        if not self._load_data_():
            if not self._load_data_():
                self._load_data_()

    def _connect_(self):
        if self.verbose: print(f'==============\nInit {self.exchange}.{self.crypto} {self.period}')
        self.conn_str = f'{sql_url}/{self.exchange}.{self.crypto}'
        if self.verbose: print("#170", self.conn_str)
        c = 0
        while c < 3:
            try:
                self.conn = create_engine(self.conn_str, pool_pre_ping=True, echo=self.verbose).connect()
                self.table = Table(self.period, self.metadata_obj, autoload_with=self.conn)
                self.session = Session(self.conn)
                if self.verbose: print(f"#177 Connected to {self.exchange}.{self.crypto} {self.period}")
                return
            except:
                self.session = None
                print(f'No base {self.exchange}.{self.crypto}')
                if not self.update:
                    print('#2 Updates disabled. Exiting.')
                    exit(2)
                # self._create_base_()
                print(f'#5 Error {c=}: Read base {self.exchange}.{self.crypto}.{self.period}')
            c += 1
        exit(5)
        # self._get_count_records_()
        # if self.count == 0:
        #     print(f'#3 Empty base {self.exchange}.{self.crypto}.{self.period}')
        #     if not self.update: exit(3)
        #     self._update_base_()
        #     self._get_count_records_()
        #     if self.count == 0:
        #         print(f'#4 Error filling empty base {self.exchange}.{self.crypto}.{self.period}')
        #         exit(4)

    def _get_count_records_(self):
        """Количество котировок в базе"""
        if self.session is None: self._connect_()
        c = 0
        while c < 3:
            try:
                self.count = int(self.session.query(self.table).count())
                if self.verbose: print(f"#206 Table {self.period} has total {self.count} records")
                return
            except:
                if self.verbose: print('except: session.query.count')
                self.count = 0
                self.session = None
                self._connect_()
            c += 1
        print(f'#5 Error: Read base {self.exchange}.{self.crypto}.{self.period}')
        exit(5)

    def _load_data_(self):
        """Загрузить из базы limit котировок"""
        if self.session is None: self._connect_()
        # if self.new:
        #     lmt = self.limit
        # else:
        # last_date = self.session.query(self.table).first()
        try:
            if self.limit is None:
                record = self.session.query(self.table).all()
            else:
                record = self.session.query(self.table).offset(self.count - self.limit).limit(self.limit).all()
            df = pd.DataFrame.from_records(record, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
            s = df.select_dtypes(include='object').columns
            df[s] = df[s].astype("float")
            # if self.verbose: print(df.dtypes)
            if self.limit is None:
                self.limit = df.shape[0]
            else:
                self.limit = min(df.shape[0], self.limit)
        except:
            self.session = None
            if self.verbose: print('except: session.query.all')
            return False
        # last_date = self.session.query(self.table).offset(self.count - 1).first()[0]
        df.sort_values('Date', ascending=True, inplace=True)
        df.set_index('Date', drop=True, inplace=True)
        df.index += timedelta(hours=tz)
        self.last_date = df.index[-1]
        if self.verbose:
            print(f"#247 Last date from {self.period} from mySQL", self.last_date)
            # print(f"Last date2 from {self.period} from mySQL", last_date)
        if self.verbose: print(f'#249 Loaded {self.limit} bars {self.period}')
        self.df = df.copy()
        return True


if __name__ == '__main__':
    cry_1h = CryptoA(period='1h', verbose=True)
    cry_1h.load(limit=6)
    cry_1h.df.to_hdf('./BTC-USD-h1.h5', 'h1')
