"""
Binance functions
"""
import time
import os
# from dotenv import load_dotenv
from datetime import datetime, timedelta

import ccxt
import pandas as pd
from sqlalchemy import create_engine

# Константы
D1 = 86400000  # ms
H1 = 3600000  # ms
M1 = 60000  # ms
M5 = M1 * 5
# H1s = 3600  # s
verbose = False
# mysql_url = 'mysql://user:pass@127.0.0.1:3307'
mysql_url = os.environ['MYSQL_URL']

class Crypto:
    """
    Получаем котировки с криптовалютных бирж и записываем в базу mySQL

    BITMEX BINANCE
    1d 1h 1m
    """
    def __init__(self, exchange='BITMEX', crypto='BTC/USD', period='1d', indexes=True, tz=3, update=True):
        if verbose: print(f'==============\nInit {exchange}.{crypto}')
        try:
            conn = create_engine(f'{mysql_url}').connect()
        except:
            print('Error open MySQL')
            exit(1)
        self.exchange = exchange
        if self.exchange != 'BITMEX' and self.exchange != 'BINANCE':
            print(f'Incorrect exchange {self.exchange}')
            exit(2)
        self.crypto = crypto
        self.dict_period = {'1m': M1, '1h': H1, '1d': D1}
        self.period = period
        self.limit = None
        self.last_date = 0
        self.indexes = indexes
        self.tz = tz
        self.df = pd.DataFrame()
        self.update = update
        try:
            self.conn = create_engine(f'{mysql_url}/{self.exchange}.{self.crypto}').connect()
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
        self.get_list_exch()

    def get_count_records(self):
        return self.conn.execute(f"SELECT COUNT(*) FROM {self.period}").fetchone()[0]

    def get_fist_date(self):
        df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date LIMIT 1", con=self.conn)
        if verbose: print(f"Fist date {df.at[0, 'Date']}")
        return df.at[0, 'Date']

    def get_last_date(self):
        count_records = self.get_count_records()
        print(f"Table {self.period} has total {count_records} records")
        if count_records == 0:
            print("Empty base")
            if not self.update: exit(4)
            self._get_crypto_from_exchange()
        df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC LIMIT 1", con=self.conn)
        return df.at[0, 'Date']

    def load_crypto(self, limit=None):
        if verbose:
            count_records = self.get_count_records()
            print(f"Table {self.period} has total {count_records} records")
            print(f"Load {self.crypto} from SQL {self.period}")
        if limit is not None: self.limit = limit
        if self.limit is None:
            self.df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC", con=self.conn)
            self.limit = self.df.shape[0]
        else:
            self.df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC LIMIT {self.limit}", con=self.conn)
            self.limit = min(self.df.shape[0], self.limit)
        self.last_date = self.df.at[0, 'Date']
        if verbose: print("Last date from mySQL", self.last_date)
        self.df.sort_values('Date', ascending=True, inplace=True)
        self.df['Date'] += timedelta(hours=self.tz)
        if self.indexes:
            self.df.set_index('Date', drop=True, inplace=True)
        print(f'Loaded {self.limit} bars {self.period}')
        return self.df

    def update_crypto(self):
        if not self.update:
            print(f"Update in mode update=False")
            return
        if verbose: print(f"Update {self.crypto} from {self.exchange} {self.period}")
        self.last_date = self.get_last_date()
        if self.last_date == 0:
            self._get_crypto_from_exchange()
            self.last_date = self.get_last_date()
        if verbose: print("Last date from mySQL", self.last_date)
        today = datetime.utcnow()
        if verbose: print('Today:', today)
        difs_td = today - self.last_date
        if verbose: print('Today - last_date =', difs_td)
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
        df_app.set_index('Date', drop=True, inplace=True)
        try:
            df_app.to_sql(self.period, con=self.conn, if_exists='append', index=True)
        except:
            print('Error write to MySQL')
            pass

    def _get_crypto_from_exchange(self, since=None, limit=500):
        print(f"Get {self.crypto} from {self.exchange} {self.period}")
        if self.exchange == 'BITMEX':
            exchange = ccxt.bitmex()
        elif self.exchange == 'BINANCE':
            exchange = ccxt.binance()
        else:
            print(f'Incorrect exchange {self.exchange}')
            exit(3)
        if since is None:
            since = exchange.milliseconds() - self.dict_period[self.period] * limit
        else:
            since = exchange.parse8601(since + 'T00:00:00Z')
        # print(exchange.iso8601(since))
        while limit > 0:
            if verbose: print('Load limit', limit, self.period)
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
            since += self.dict_period[self.period] * lmt
            limit -= lmt
            if limit > 0: time.sleep(exchange.rateLimit // 100)

    def _create_base(self):
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
        if verbose: print(f'Created base {self.exchange}.{self.crypto}')
        conn = create_engine(f'{mysql_url}/').connect()
        conn.execute(base1 + base2, con=conn)
        conn = create_engine(f'{mysql_url}/EXCHANGE').connect()
        ins = f"INSERT INTO `Exchange`(`Exchange`, `Crypto`) VALUES ('{self.exchange}','{self.crypto}')"
        conn.execute(ins, con=conn)
        self.conn = create_engine(f'{mysql_url}/{self.exchange}.{self.crypto}').connect()

    def get_list_exch(self):
        conn = create_engine(f'{mysql_url}/EXCHANGE').connect()
        df = pd.read_sql(f"SELECT * FROM Exchange", con=conn)
        if verbose: print(df)
        return df
