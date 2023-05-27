import time
# import asyncio
from datetime import datetime, timedelta

import ccxt
import pandas as pd
import re
from sqlalchemy import create_engine, text

# from MLDiLL.utils import VWAP, VWAP_d, VWAP_p

# from .env import mysql_url
MYSQL_URL = "mysql+mysqldb://bitok:bitok@10.10.10.200:3307"
# mysql_url = 'mysql://user:pass@127.0.0.1:3307'
# mysql_url = os.environ['MYSQL_URL']
SQL_URL = MYSQL_URL
# Константы
D1 = 86400000  # ms
H1 = 3600000  # ms
M1 = 60000  # ms
M5 = M1 * 5
# H1s = 3600  # s

dict_period = {'1m': M1, '1h': H1, '1d': D1}
TZ = 0


# Версия 2

class Crypto:
    """
    Получаем котировки с криптовалютных бирж и записываем в базу SQL, чтобы легко их получать

    Биржи bitmex binance etc
    Периоды 1d 1h 1m
    """

    def __init__(self, exchange=None, crypto=None, period=None, update=True,
                 verbose=False):
        if verbose: print(f'def __init__ {period=}')
        try:
            create_engine(f'{SQL_URL}').connect()
        except:
            print('Error open Base')
            exit(1)
        self.exchange = exchange
        self.exch = getattr(ccxt, self.exchange)({'enableRateLimit': True}) if self.exchange is not None else None
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
        self.maxV = 0
        # self.connect(exchange=exchange, crypto=crypto, period=period, update=update)

    def info(self):
        if self.verbose: print(f'def info')
        self.exch.load_markets()
        if self.verbose: print('Exchange:', self.exchange)
        symbols = self.exch.symbols
        pat = 'BTC.*USD*'
        # print('Symbols:', symbols)
        for s in symbols:
            if re.match(pat, s):
                print(s)

    def _connect(self):
        if self.verbose: print(f'def _connect "{self.conn_str}"')
        con = create_engine(self.conn_str, pool_pre_ping=True).connect()
        if self.verbose: print(f'_connected to "{con.info}"')
        return con

    def _check_connect(self):
        if self.verbose: print('def _check_connect')
        try:
            conn = self._connect()
        except:
            print(f'No base BTC')
            if not self.update: exit(3)
            self._create_base()
        else:
            conn.close()
        count_records = self.get_count_records()
        if count_records == 0:
            print(f'Empty base BTC')
            if not self.update: exit(4)
            self._get_from_exchange()
            count_records = self.get_count_records()
            if count_records == 0:
                print(f'Error filling base BTC')
                if not self.update: exit(4)
                # self.delete({self.exchange}.{self.crypto})
                exit(5)
        if self.verbose: print(f"Table {self.period} has total {count_records} records")

    def _check_exchange(self):
        if self.verbose: print('def _check_exchange')
        try:
            if self.verbose: print(
                f"Test_get_from_exch BTC {self.period} limit 1"
            )
            if self.exchange == 'bitmex' and self.crypto == 'BTC/USD':
                self.exch.fetch_ohlcv(self.crypto + ':BTC', self.period, limit=1)
            else:
                self.exch.fetch_ohlcv(self.crypto, self.period, limit=1)
        except:
            print(f'Error test fetch from {self.exchange}, update disabling')
            self.update = False

    def open(self, exchange=None, crypto=None, period=None, update=None):
        """Открываем базу"""
        if self.verbose: print('def open')
        self.limit = None
        if exchange is not None: self.exchange = exchange
        if self.exchange is not None: self.exch = getattr(ccxt, self.exchange)({'enableRateLimit': True})
        if crypto is not None: self.crypto = crypto
        if period is not None: self.period = period
        # if indexes is not None: self.indexes = indexes
        if update is not None: self.update = update
        if self.period is None: return
        if self.verbose: print(f'==============\nInit BTC {self.period}')
        self.conn_str = f'{SQL_URL}/BTC'
        if self.verbose: print(self.conn_str)
        self._check_connect()
        self._check_exchange()
        if self.update: self.updating()
        self.load(limit=1)

    def get_count_records(self):
        """Количество котировок в базе"""
        if self.verbose: print(f'def get_count_records {self.period}')
        try:
            conn = self._connect()
            co = conn.execute(text(f'SELECT COUNT(*) FROM {self.period};'))
            conn.close()
            count = co.fetchone()[0]
        except:
            print('error get_count')
            return 0
        return count

    def get_fist_date(self, local=False):
        """Первая дата котировок в базе"""
        if self.verbose: print('def get_fist_date')
        conn = self._connect()
        df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date LIMIT 1", con=conn)
        conn.close()
        fist_date = df.at[0, 'Date']
        if local and TZ != 0: fist_date += timedelta(hours=TZ)
        if self.verbose: print(f"Fist date {fist_date}")
        return fist_date

    def get_last_date(self, local=False):
        """Последняя дата котировок в базе"""
        if self.verbose: print("def get_last_date")
        count_records = self.get_count_records()
        if self.verbose: print(f"Table {self.period} has total {count_records} records")
        # TODO если пустая база возвращать 0, а не загружать
        if count_records == 0:
            print("Empty base")
            if not self.update: exit(4)
            self._get_from_exchange()
        conn = self._connect()
        df = pd.read_sql(f"SELECT * FROM {self.period} ORDER BY Date DESC LIMIT 1", con=conn)
        conn.close()
        last_date = df.at[0, 'Date']
        if local and TZ != 0: last_date += timedelta(hours=TZ)
        if self.verbose: print(f"Last date {last_date}")
        return last_date

    def load(self, limit=None):
        """Загрузить из базы в DataFrame последние limit котировок"""
        if self.verbose: print(f"def load {limit}")
        if self.verbose:
            count_records = self.get_count_records()
            print(f"Table {self.period} has total {count_records} records")
            print(f"Load {self.crypto} from SQL {self.period}")
        if limit is not None: self.limit = limit
        # Если не установлен limit котировок, грузить все
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
        if self.verbose: print("Last date from Base", self.last_date)
        df.sort_values('Date', ascending=True, inplace=True)
        df.set_index('Date', drop=True, inplace=True)
        if TZ != 0: df.index += timedelta(hours=TZ)
        if self.verbose: print(f'Loaded {self.limit} bars {self.period}')
        self.df = df
        self.maxV = df['Volume'].max()
        return df

    def updating(self):
        """Обновить базу котировок от последней даты до текущей"""
        if self.verbose: print("def updating")
        if not self.update:
            print(f"Update in mode update=False. Ignoring Update.")
            return
        self.last_date = self.get_last_date()
        if self.last_date == 0:
            self._get_from_exchange()
            self.last_date = self.get_last_date()
        if self.verbose: print("Last date from Base", self.last_date)
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
        # TODO перенести и исправить это в функцию _to_sql
        # Удаляем последнюю запись, поскольку она скорее всего имеет неверные данные
        if difs >= 1:
            conn = self._connect()
            if self.verbose: print(f"Delete in {self.period} last record on {self.last_date}")
            conn.execute(text(f"DELETE FROM {self.period} ORDER BY Date DESC LIMIT 1;"))
            conn.close()
            if self.verbose: print(f"Update BTC {self.period} count {difs + 1}")
            self._get_from_exchange(limit=difs + 1)

    def update_from(self, from_date=None, count=None):
        """Обновить базу котировок от указанной даты по количеству"""
        if self.verbose: print(f"def update_from {from_date} {count}")
        if not self.update:
            print(f"Update in mode update=False. Ignoring Update.")
            return
        if count >= 1:
            if self.verbose: print(f"Update_from BTC {self.period} count {count}")
            if self.verbose: print('From date:', from_date)
            self._get_from_exchange(since=from_date, limit=count)

    def repair_table(self, df=None):
        """Проверка DataFrame на отсутствие пропусков и дозагрузка пропущеных значений"""
        # TODO что мы вообще репарим? self.df или базу
        # Если не указан DataFrame, то репарим DataFrame из класса
        if df is None:
            df_rep = self.df
        else:
            df_rep = df
        if df_rep is None: print(f"Repair only after load()"); return
        if self.verbose: print(f"def repair_table {df_rep.shape=}")
        if self.verbose: print(f'Repair_table {self.period}')
        if self.period == '1m':
            per = '1min'
        else:
            per = self.period
        # Находим пропущеные индексы
        df_rep = df_rep.resample(per).first()
        holes = df_rep[df_rep['Open'].isna()].index.sort_values(ascending=True)
        if self.verbose: print('holes:', holes)
        c = 1
        l = len(holes)
        for i in holes:
            if self.verbose: print(f'Repair {self.period} ({c}/{l}) {i}'); c += 1
            self.update_from(from_date=i, count=1)
        if self.verbose: print(f'End repair_table {self.period}')

    # TODO repair _to_sql
    def _to_sql(self, df_app: pd.DataFrame):
        """Записать df_app в базу котировок"""
        if self.verbose: print(f'def _to_sql {df_app.shape=}')
        df_app.set_index('Date', drop=True, inplace=True)
        conn = self._connect()
        if self.verbose: print(f"Write_to_sql BTC {self.period} count {len(df_app)}")
        if self.verbose: print(f"{df_app}")
        for i in range(len(df_app)):
            try:
                if self.verbose: print('_to_sql', self.period, i, df_app.index[i])
                df_app.iloc[i:i + 1].to_sql(self.period, con=conn, if_exists='append', index=True)
            except Exception as e:
                # TODO исправить ошибку записи. Удалять запись и добавлять с новыми данными или делать UPDATE
                print(f'\n{e} Error write to Base {self.period}\n{df_app.iloc[i: i + 1]}')
        conn.close()

    # Работа с биржей
    def _get_from_exchange(self, since=None, limit=1500):
        """Получить котировки с биржи от даты since количеством limit
        И записать в базу котировок"""
        if self.verbose: print(f"def _get_from_exchange {since=} {limit=}")
        # TODO syncing with updating
        if since is None:
            # Вычисляем время начала загрузки данных как разницу текущего времени и количества баров
            since_exch = self.exch.milliseconds() - dict_period[self.period] * limit
        else:
            # Вычисляем время начала загрузки данных из входного времени
            since_exch = self.exch.parse8601(since.strftime('%Y-%m-%d %H:%M:%S'))
        if self.verbose: print('Since', self.exch.iso8601(since_exch))
        while limit > 0:
            time.sleep(self.exch.rateLimit // 1000)
            if self.verbose: print('Load limit', limit, self.period)
            lmt = limit if limit <= 750 else 750
            try:
                if self.verbose: print(
                    f"Get_from_exch {self.exchange}.{self.crypto} {self.period} since {since_exch} limit {lmt}"
                )
                fetch = self.exch.fetch_ohlcv(self.crypto, self.period, since=since_exch, limit=lmt)
            except:
                print(f'Error fetch from {self.exchange}')
                self.update = False
                exit(1)
            else:
                df = pd.DataFrame(fetch, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['Date'] = pd.to_datetime(df['Date'], unit='ms')
                # Пишем кусок загруженных данных в базу
                self._to_sql(df)
                # print(df)
            since_exch += dict_period[self.period] * lmt
            limit -= lmt

    def _create_base(self):
        """Создать базы котировок для 1d 1h 1m"""
        # TODO Проверить на наличии пары на бирже
        print(f"Create base BTC")
        base1 = f"CREATE DATABASE IF NOT EXISTS `BTC`; USE `BTC`;"
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
        conn = create_engine(f'{SQL_URL}/').connect()
        conn.execute(text(base1 + base2))
        conn.close()


if __name__ == '__main__':
    print('work! Dont break!')
    exch = 'binance'
    crypto = 'BTC/USDT'
    cry = Crypto(exchange=exch, verbose=False, update=True)
    # cry.info()
    # cry.open(crypto=crypto, period='1h')
    # # df = cry.load(limit=1)
    # cry.repair_table()
    # print(f'First date 1h:', cry.get_fist_date())
    # print(f'Last date 1h:', cry.get_last_date())
    cry.open(crypto=crypto, period='1m')
    # df = cry.load(limit=1)
    cry.repair_table()
    print(f'Last date 1m:', cry.get_last_date())
    while True:
        print('work! Dont break!')
        cry.open(crypto=crypto, period='1m')
        print(f'First date 1m:', cry.get_fist_date())
        print('sleep')
        time.sleep(600)
