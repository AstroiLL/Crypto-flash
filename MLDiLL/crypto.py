import time
# import os
# from dotenv import load_dotenv
from datetime import datetime, timedelta

import ccxt
import pandas as pd
from sqlalchemy import create_engine

# from MLDiLL.utils import VWAP, VWAP_d, VWAP_p

# from .env import mysql_url
mysql_url = "mysql://bitok:bitok@10.10.10.200:3307"
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
        # self.conn = None
        self.conn_str = None
        self.verbose = verbose
        self.connect = self.open
        self.update_crypto = self.updating
        self.load_crypto = self.load
        # self.connect(exchange=exchange, crypto=crypto, period=period, update=update)

    def _connect(self):
        return create_engine(self.conn_str, pool_pre_ping=True).connect()

    def _check_connect(self):
        try:
            conn = self._connect()
        except:
            print(f'No base {self.exchange}.{self.crypto}')
            if not self.update: exit(3)
            # conn.close()
            self._create_base()
        else:
            conn.close()
        count_records = self.get_count_records()
        if count_records == 0:
            print(f'Empty base {self.exchange}.{self.crypto}')
            if not self.update: exit(4)
            self._get_from_exchange()
            count_records = self.get_count_records()
            if count_records == 0:
                print(f'Error filling base {self.exchange}.{self.crypto}')
                if not self.update: exit(4)
                # self.delete({self.exchange}.{self.crypto})
                exit(5)
        if self.verbose: print(f"Table {self.period} has total {count_records} records")

    def _check_exchange(self):
        if self.exchange == 'BITMEX':
            exchange = ccxt.bitmex(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
        elif self.exchange == 'BINANCE':
            exchange = ccxt.binance(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
        else:
            print(f'Incorrect exchange "{self.exchange}", seting "BITMEX"')
            exchange = ccxt.bitmex(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
            self.exchange = 'BITMEX'
        try:
            if self.verbose: print(
                f"Test_get_from_exch {self.exchange}.{self.crypto} {self.period} limit 1"
            )
            exchange.fetch_ohlcv(self.crypto, self.period, limit=1)
        except:
            print(f'Error test fetch from {self.exchange}, update disabling')
            self.update = False

    def open(self, exchange=None, crypto=None, period=None, update=None):
        """Открываем базу"""
        self.limit = None
        if exchange is not None: self.exchange = exchange
        if self.exchange != 'BITMEX' and self.exchange != 'BINANCE':
            print(f'Incorrect exchange "{self.exchange}", setting "BITMEX"')
            self.exchange = 'BITMEX'
        if crypto is not None: self.crypto = crypto
        if period is not None: self.period = period
        # if indexes is not None: self.indexes = indexes
        if update is not None: self.update = update
        if self.period is None:
            return
        if self.verbose: print(f'==============\nInit {self.exchange}.{self.crypto} {self.period}')
        self.conn_str = f'{mysql_url}/{self.exchange}.{self.crypto}'
        if self.verbose: print(self.conn_str)
        self._check_connect()
        self._check_exchange()
        if self.update: self.updating()

    def get_count_records(self):
        """Количество котировок в базе"""
        try:
            conn = self._connect()
            co = conn.execute(f"SELECT COUNT(*) FROM {self.period}")
            conn.close()
            # print(co)
            count = co.fetchone()[0]
        except:
            print('error get_count')
            return 0
        # conn.close()
        # print('count=', count)
        return count

    def get_fist_date(self, local=False):
        """Первая дата котировок в базе"""
        conn = self._connect()
        df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date LIMIT 1", con=conn)
        conn.close()
        fist_date = df.at[0, 'Date']
        if local: fist_date += timedelta(hours=tz)
        if self.verbose: print(f"Fist date {fist_date}")
        return fist_date

    def get_last_date(self, local=False):
        """Последняя дата котировок в базе"""
        count_records = self.get_count_records()
        if self.verbose: print(f"Table {self.period} has total {count_records} records")
        # TODO если пустая база возвращать 0, а не загружать
        if count_records == 0:
            print("Empty base")
            if not self.update: exit(4)
            self._get_from_exchange(limit=1000)
        conn = self._connect()
        df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC LIMIT 1", con=conn)
        conn.close()
        last_date = df.at[0, 'Date']
        if local: last_date += timedelta(hours=tz)
        if self.verbose: print(f"Last date {last_date}")
        return last_date

    def load(self, limit=None):
        """Загрузить из базы limit котировок"""
        if self.verbose:
            count_records = self.get_count_records()
            print(f"Table {self.period} has total {count_records} records")
            print(f"Load {self.crypto} from SQL {self.period}")
        if limit is not None: self.limit = limit
        # df = pd.DataFrame()
        if self.limit is None:
            conn = self._connect()
            df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC", con=conn)
            conn.close()
            self.limit = df.shape[0]
        else:
            conn = self._connect()
            df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC LIMIT {self.limit}", con=conn)
            conn.close()
            self.limit = min(df.shape[0], self.limit)
        self.last_date = df.at[0, 'Date']
        if self.verbose: print("Last date from mySQL", self.last_date)
        df.sort_values('Date', ascending=True, inplace=True)
        df.set_index('Date', drop=True, inplace=True)
        df.index += timedelta(hours=tz)
        if self.verbose: print(f'Loaded {self.limit} bars {self.period}')
        self.df = df
        return df

    def updating(self):
        """Обновить базу котировок от последней даты до текущей"""
        if not self.update:
            print(f"Update in mode update=False. Ignoring Update.")
            return
        self.last_date = self.get_last_date()
        if self.last_date == 0:
            self._get_from_exchange()
            self.last_date = self.get_last_date()
        if self.verbose: print("Last date from mySQL", self.last_date)
        # TODO syncing with _get_from_exchange
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
            conn = self._connect()
            if self.verbose: print(f"Delete in {self.period} last record on {self.last_date}")
            conn.execute(f"DELETE FROM {self.period} ORDER BY Date DESC LIMIT 1")
            conn.close()
            if self.verbose: print(f"Update {self.exchange}.{self.crypto} {self.period} count {difs + 1}")
            self._get_from_exchange(limit=difs + 1)

    def update_from(self, from_date=None, count=None):
        """Обновить базу котировок от последней даты до текущей"""
        if not self.update:
            print(f"Update in mode update=False. Ignoring Update.")
            return
        if count >= 1:
            if self.verbose: print(f"Update_from {self.exchange}.{self.crypto} {self.period} count {count}")
            if self.verbose: print('From date:', from_date)
            self._get_from_exchange(since=from_date, limit=count)

    def repair_table(self, batch=1):
        """Проверка базы на отсутствие пропусков и дозагрузка пропущеных значений"""
        if self.verbose: print(f'Repair_table {self.period}')
        if self.period == '1m':
            per = '1min'
        else:
            per = self.period
        df = self.df.resample(per).first()
        holes = df[df['Open'].isna()].index
        holes = holes[::batch]
        c = 1
        l = len(holes)
        for i in holes.sort_values(ascending=True):
            if self.verbose: print(f'Repair {self.period} ({c}/{l}) {i}')
            c += 1
            self.update_from(from_date=i, count=batch)
        if self.verbose: print(f'End repair_table {self.period}')

    # TODO repair _to_sql
    def _to_sql(self, df_app: pd.DataFrame):
        """Записать df_app в базу котировок"""
        df_app.set_index('Date', drop=True, inplace=True)
        conn = self._connect()
        if self.verbose: print(f"Write_to_sql {self.exchange}.{self.crypto} {self.period} count {len(df_app)}")
        for i in range(len(df_app)):
            try:
                if self.verbose:
                    print('Insert', i, 'rows')
                df_app.iloc[i:i + 1].to_sql(self.period, con=conn, if_exists='append', index=True)
            except Exception as e:
                print(f'{e} Error write to MySQL {self.period}')
        conn.close()

    # Работа с биржей
    def _get_from_exchange(self, since=None, limit=500):
        """Получить котировки с биржи от даты since количеством limit"""
        # exchange = 'BITMEX'
        if self.exchange == 'BITMEX':
            exchange = ccxt.bitmex(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
        elif self.exchange == 'BINANCE':
            exchange = ccxt.binance(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
        else:
            print(f'Incorrect exchange {self.exchange} seting BITMEX')
            exchange = ccxt.bitmex(
                {
                    'enableRateLimit': True,  # or .enableRateLimit = True later
                }
            )
            self.exchange = 'BITMEX'
        # TODO syncing with updating
        if since is None:
            # Вычисляем время начала загрузки данных как разницу текущего времени и количества баров
            since_exch = exchange.milliseconds() - dict_period[self.period] * limit
        else:
            # Вычисляем время начала загрузки данных из входного времени
            since_exch = exchange.parse8601(since.strftime('%Y-%m-%d %H:%M:%S'))
        if self.verbose: print('Since', exchange.iso8601(since_exch))
        while limit > 0:
            time.sleep(exchange.rateLimit // 1000)
            if self.verbose: print('Load limit', limit, self.period)
            lmt = limit if limit <= 750 else 750
            try:
                if self.verbose: print(
                    f"Get_from_exch {self.exchange}.{self.crypto} {self.period} since {since_exch} limit {lmt}"
                )
                fetch = exchange.fetch_ohlcv(self.crypto, self.period, since=since_exch, limit=lmt)
            except:
                print(f'Error fetch from {self.exchange}')
                self.update = False
                exit(1)
            else:
                df = pd.DataFrame(fetch, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['Date'] = pd.to_datetime(df['Date'], unit='ms', infer_datetime_format=True)
                self._to_sql(df)
            since_exch += dict_period[self.period] * lmt
            limit -= lmt
            # if limit > 0: time.sleep(exchange.rateLimit // 100)

    def _create_base(self):
        """Создать базы котировок для 1d 1h 1m"""
        # TODO Проверить на наличии пары на бирже
        print(f"Create base {self.exchange}.{self.crypto}")
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
        conn.close()
        # self.conn = create_engine(f'{mysql_url}/{self.exchange}.{self.crypto}').connect()

    def get_list_exch(self):
        """Получить список существующих на сервере баз данных баз котировок"""
        conn = create_engine(f'{mysql_url}/EXCHANGE').connect()
        df = pd.read_sql(f"SELECT * FROM Exchange", con=conn)
        conn.close()
        if self.verbose: print(df)
        return df


class CryptoH:
    """
    cry = CryptoH(limit=24)
    df = cry.get_df()
    print(df)

    """
    def __init__(self, exchange='BITMEX', crypto='BTC/USD', limit=None, update=True, max_vol=True, verbose=False):
        self.cry_1h = Crypto(verbose=verbose)
        self.cry_1h.open(exchange=exchange, crypto=crypto, period='1h', update=update)
        self.cry_1m = Crypto(verbose=verbose)
        self.cry_1m.open(exchange=exchange, crypto=crypto, period='1m', update=update)
        if limit is not None:
            self.load(limit)
            self.max_vol()

    def load(self, limit):
        self.df_1h = self.cry_1h.load(limit=limit)
        self.df_1m = self.cry_1m.load(limit=limit * 168)

    def repair_table(self):
        self.cry_1h.repair_table()
        self.cry_1m.repair_table()

    def max_vol(self):
        # берем из массива минут, группируем по часам, находим в каждом часе индекс максимума и
        # Open максимума этого часа прописываем в Open_max массива часов
        self.df_1h['Open_max'] = self.cry_1m.df['Open'][self.cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax()
        ].resample('1h').mean()
        self.df_1h['Date_max'] = self.cry_1m.df['Volume'].groupby(pd.Grouper(freq='1h')).idxmax().resample('1h').max()

    def get_df(self):
        return self.df_1h


if __name__ == '__main__':
    import enquiries

    options = ['BTC/USD', 'ETH/USD', 'XRP/USD']
    choice = enquiries.choose('Что обновлять?: ', options)
    print(choice)
    cry = CryptoH(crypto=choice, limit=24)
    cry.repair_table()
    df = pd.DataFrame(cry.get_df()[['Volume', 'Open_max', 'Date_max']])
    print(df)
    # cry_1m = Crypto(update=False, verbose=False)
    # cry_1m.open(exchange='BITMEX', crypto='BTC/USD', period='1m')
    # df = cry_1m.load(limit=60)
    # print('SQL')
    # print(df)
