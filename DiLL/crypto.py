import time
# import os
# from dotenv import load_dotenv
from datetime import datetime, timedelta

import ccxt
import pandas as pd
from sqlalchemy import create_engine
# from DiLL.utils import VWAP, VWAP_d, VWAP_p

from .env import mysql_url

# mysql_url = 'mysql://user:pass@127.0.0.1:3307'
# mysql_url = os.environ['MYSQL_URL']

# Константы
D1 = 86400000  # ms
H1 = 3600000  # ms
M1 = 60000  # ms
M5 = M1 * 5
# H1s = 3600  # s

dict_period = {'1m': M1, '1h': H1, '1d': D1}
tz = 0


class Crypto:
    """
    Получаем котировки с криптовалютных бирж и записываем в базу mySQL, чтобы легко их получать

    Биржи BITMEX BINANCE
    Периоды 1d 1h 1m
    """

    def __init__(self, exchange=None, crypto=None, period=None, update=True,
                 verbose=False):
        try:
            create_engine(f'{mysql_url}').connect()
        except:
            print('Error open MySQL')
            exit(1)
        self.exchange = exchange
        self.limit = None
        self.last_date = 0
        self.df = pd.DataFrame()
        self.crypto = crypto
        self.period = period
        # self.indexes = indexes
        self.update = update
        self.conn = None
        self.verbose = verbose
        # self.connect(exchange=exchange, crypto=crypto, period=period, update=update)


    def connect(self, exchange=None, crypto=None, period=None, update=None):
        if exchange is not None: self.exchange = exchange
        if crypto is not None: self.crypto = crypto
        if period is not None: self.period = period
        # if indexes is not None: self.indexes = indexes
        if update is not None: self.update = update
        if self.period is None:
            return
        if self.verbose: print(f'==============\nInit {self.exchange}.{self.crypto} {self.period}')
        if self.exchange != 'BITMEX' and self.exchange != 'BINANCE':
            print(f'Incorrect exchange {self.exchange}')
            exit(2)
        try:
            self.conn = create_engine(f'{mysql_url}/{self.exchange}.{self.crypto}', pool_pre_ping=True).connect()
        except:
            print(f'No base {self.exchange}.{self.crypto}')
            if not self.update: exit(3)
            self._create_base()
        count_records = self.get_count_records()
        if count_records == 0:
            print(f'Empty base {self.exchange}.{self.crypto}')
            if not self.update: exit(4)
            self._get_crypto_from_exchange()
            count_records = self.get_count_records()
            if count_records == 0:
                print(f'Error filling base {self.exchange}.{self.crypto}')
                if not self.update: exit(4)
                # self.delete({self.exchange}.{self.crypto})
                exit(5)
        print(f"Table {self.period} has total {count_records} records")
        # self.get_list_exch()

    def get_count_records(self):
        """Количество котировок в базе"""
        count = self.conn.execute(f"SELECT COUNT(*) FROM {self.period}").fetchone()[0]
        print(count)
        return count

    def get_fist_date(self, local=False):
        """Первая дата котировок в базе"""
        df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date LIMIT 1", con=self.conn)
        fist_date = df.at[0, 'Date']
        if local: fist_date += timedelta(hours=tz)
        if self.verbose: print(f"Fist date {fist_date}")
        return fist_date

    def get_last_date(self, local=False):
        """Последняя дата котировок в базе"""
        count_records = self.get_count_records()
        print(f"Table {self.period} has total {count_records} records")
        if count_records == 0:
            print("Empty base")
            if not self.update: exit(4)
            self._get_crypto_from_exchange()
        df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC LIMIT 1", con=self.conn)
        last_date = df.at[0, 'Date']
        if local: last_date += timedelta(hours=tz)
        return last_date

    def load_crypto(self, limit=None):
        """Загрузить из базы limit котировок"""
        if self.verbose:
            count_records = self.get_count_records()
            print(f"Table {self.period} has total {count_records} records")
            print(f"Load {self.crypto} from SQL {self.period}")
        if limit is not None: self.limit = limit
        df = pd.DataFrame()
        if self.limit is None:
            df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC", con=self.conn)
            self.limit = df.shape[0]
        else:
            df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC LIMIT {self.limit}", con=self.conn)
            self.limit = min(df.shape[0], self.limit)
        self.last_date = df.at[0, 'Date']
        if self.verbose: print("Last date from mySQL", self.last_date)
        df.sort_values('Date', ascending=True, inplace=True)
        df.set_index('Date', drop=True, inplace=True)
        df.index += timedelta(hours=tz)
        print(f'Loaded {self.limit} bars {self.period}')
        self.df = df
        return df

    def load_crypto_date(self, limit=None, from_date=None):
        """Загрузить из базы котировки с from_date длиной limit"""
        if self.verbose:
            count_records = self.get_count_records()
            print(f"Table {self.period} has total {count_records} records")
            print(f"Load {self.crypto} from SQL {self.period}")
        # if limit is not None: self.limit = limit
        df = pd.DataFrame()
        if self.limit is None:
            df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC", con=self.conn)
            self.limit = df.shape[0]
        else:
            df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC LIMIT {self.limit}", con=self.conn)
            self.limit = min(df.shape[0], self.limit)
        self.last_date = df.at[0, 'Date']
        if self.verbose: print("Last date from mySQL", self.last_date)
        df.sort_values('Date', ascending=True, inplace=True)
        df.set_index('Date', drop=True, inplace=True)
        df.index += timedelta(hours=tz)
        print(f'Loaded {self.limit} bars {self.period}')
        self.df = df
        return df

    def update_crypto(self):
        """Обновить базу котировок от последней даты до текущей"""
        if not self.update:
            print(f"Update in mode update=False")
            return
        if self.verbose: print(f"Update {self.crypto} from {self.exchange} {self.period}")
        self.last_date = self.get_last_date()
        if self.last_date == 0:
            self._get_crypto_from_exchange()
            self.last_date = self.get_last_date()
        if self.verbose: print("Last date from mySQL", self.last_date)
        today = datetime.utcnow()
        if self.verbose: print('Today:', today)
        difs_td = today - self.last_date
        if self.verbose: print('Today - last_date =', difs_td)
        # difs = 0
        if self.period == '1d':
            difs = difs_td.days
        elif self.period == '1h':
            difs = int(difs_td.total_seconds() // 3600)
        elif self.period == '1m':
            difs = int(difs_td.total_seconds() // 60)
        else:
            return None
        # if verbose: print(difs)
        if difs >= 1:
            self.conn.execute(f"DELETE FROM {self.period} ORDER BY Date DESC LIMIT 1", con=self.conn)
            self._get_crypto_from_exchange(limit=difs + 1)

    def _crypto_to_sql(self, df_app: pd.DataFrame):
        """Записать df_app в базу котировок"""
        df_app.set_index('Date', drop=True, inplace=True)
        try:
            df_app.to_sql(self.period, con=self.conn, if_exists='append', index=True)
        except:
            print('Error write to MySQL')
            pass

    # Работа с биржей
    def _get_crypto_from_exchange(self, since=None, limit=500):
        """Получить котировки с биржи от даты since количеством limit"""
        print(f"Get {self.crypto} from {self.exchange} {self.period}")
        exchange = None
        if self.exchange == 'BITMEX':
            exchange = ccxt.bitmex()
        elif self.exchange == 'BINANCE':
            exchange = ccxt.binance()
        else:
            print(f'Incorrect exchange {self.exchange} seting BITMEX')
            exchange = ccxt.bitmex()
            self.exchange = 'BITMEX'
        if since is None:
            since = exchange.milliseconds() - dict_period[self.period] * limit
        else:
            since = exchange.parse8601(since + 'T00:00:00Z')
        # print(exchange.iso8601(since))
        while limit > 0:
            if self.verbose: print('Load limit', limit, self.period)
            lmt = limit if limit <= 750 else 750
            try:
                fetch = exchange.fetch_ohlcv(self.crypto, self.period, since=since, limit=lmt)
            except:
                print(f'Error fetch from {self.exchange}')
                exit(1)
            else:
                df = pd.DataFrame(fetch, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['Date'] = pd.to_datetime(df['Date'], unit='ms', infer_datetime_format=True)
                self._crypto_to_sql(df)
            since += dict_period[self.period] * lmt
            limit -= lmt
            if limit > 0: time.sleep(exchange.rateLimit // 100)

    def _create_base(self):
        """Создать базы котировок для 1d 1h 1m"""
        base1 = f"CREATE DATABASE IF NOT EXISTS `{self.exchange}.{self.crypto}`; USE `{self.exchange}.{self.crypto}`;"
        base2 = """
CREATE TABLE `1d` (
  `Date` datetime NOT NULL,
  `Open` double DEFAULT NULL,
  `High` double DEFAULT NULL,
  `Low` double DEFAULT NULL,
  `Close` double DEFAULT NULL,
  `Volume` double DEFAULT NULL
);
CREATE TABLE `1h` (
  `Date` datetime NOT NULL,
  `Open` double DEFAULT NULL,
  `High` double DEFAULT NULL,
  `Low` double DEFAULT NULL,
  `Close` double DEFAULT NULL,
  `Volume` double DEFAULT NULL
);
CREATE TABLE `1m` (
  `Date` datetime NOT NULL,
  `Open` double DEFAULT NULL,
  `High` double DEFAULT NULL,
  `Low` double DEFAULT NULL,
  `Close` double DEFAULT NULL,
  `Volume` double DEFAULT NULL
);
ALTER TABLE `1d`
  ADD PRIMARY KEY (`Date`) USING BTREE;
ALTER TABLE `1h`
  ADD PRIMARY KEY (`Date`) USING BTREE;
ALTER TABLE `1m`
  ADD PRIMARY KEY (`Date`) USING BTREE;
COMMIT;
        """
        if self.verbose: print(f'Created base {self.exchange}.{self.crypto}')
        conn = create_engine(f'{mysql_url}/').connect()
        conn.execute(base1 + base2, con=conn)
        conn = create_engine(f'{mysql_url}/EXCHANGE').connect()
        ins = f"INSERT INTO `Exchange`(`Exchange`, `Crypto`) VALUES ('{self.exchange}','{self.crypto}')"
        conn.execute(ins, con=conn)
        self.conn = create_engine(f'{mysql_url}/{self.exchange}.{self.crypto}').connect()

    def get_list_exch(self):
        """Получить список существующих на сервере баз данных баз котировок"""
        conn = create_engine(f'{mysql_url}/EXCHANGE').connect()
        df = pd.read_sql(f"SELECT * FROM Exchange", con=conn)
        if self.verbose: print(df)
        return df
