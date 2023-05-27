import os
import pandas as pd
from dbiLL.db_btc import Db, BTC
from datetime import datetime
"""
Из файлов собраных агрегатором https://github.com/Tucsky/aggr-server
(Агрегатор должен работать непрерывно столько времени, сколько данных вам надо собрать)
Вытаскиваются все максимумы объемов >= moreBTC за каждый час
И складываются в базу SQL (например sqlite или mySQL)
Начало сбора максимумов start_date до текущего момента now_date
В последствии эту базу можно использовать для визуализации на графиках и для использования в ML
Для работы с SQL через SQLAlchemy используется модуль dbiLL.db_btc
Запускать программу можно много раз, она добавляет только отсутствующие значения
"""

moreBTC = 10
# Указать полный путь к папке где aggr-server собирает файлы
# Обычно это aggr-server/data
path = '/home/astroill/Python/Crypto-flash/aggr-server/data'
# Начальная дата сбора данных
# Для ускорения указывайте последнюю или предпоследнюю дату предыдущего сбора
start_date = '2023-05-16'
now_date = datetime.now().strftime("%Y-%m-%d")
print("Сегодня:", now_date)
# База данных для занесения всплесков
db = Db('sqlite', '/home/astroill/Python/Crypto-flash/Data/btc_max_more_10.db')
session = db.open()
columns = ['exch', 'pairs', 'date', 'time_max', 'close', 'vol']
df_maxs = pd.DataFrame([], columns=columns)

for dirs, folder, files in os.walk(path):
    print(dirs)
    for file in files:
        fname, ext = os.path.splitext(file)
        date = fname[:10]
        if ext == '.gz' and date >= start_date:
            dir1, folder2 = os.path.split(dirs)
            _, folder1 = os.path.split(dir1)
            fullname = os.path.join(dirs, file)
            df = pd.read_csv(
                fullname, sep=' ', names=['time', 'close', 'vol', 'dir', 'liq'],
                # parse_dates=['time'],
                dtype={'time': 'Int64', 'dir': 'Int32', 'liq': 'Int32'}
                )
            df.fillna(0, inplace=True)
            df = df[['time', 'close', 'vol', 'dir', 'liq']]
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            # print(df['time'])
            # exit()
            # Всплеск берется если объем >= moreBTC
            dfv = df[df['vol'] >= moreBTC]
            if not dfv.empty:
                dfv.set_index('time', drop=True, inplace=True)
                r = dfv.resample('1min')
                df1m = r.agg({'close': "last", 'vol': "sum", 'dir': 'max', 'liq': 'min'})
                df1m = df1m.reset_index().dropna()
                # df1m = df1m.dropna()
                # print(df1m)
                session.flush()
                for i in range(len(df1m)):
                    btc0 = BTC(df1m.iloc[i, :])
                    if not session.query(BTC).filter(BTC.time == btc0.time).all():
                        print('btc0:', btc0.time, 'Vol:', btc0.vol)
                        session.add(btc0)
session.commit()
# print(session.query(BTC).all())
print('Last record:', session.query(BTC).order_by(BTC.time.desc()).first().time)

"""
ohlc_dict = {'Open':'first','High':'max','Low':'min','Close': 'last','Volume': 'sum','Adj Close': 'last'}
data_dy.resample('M', how=ohlc_dict, closed='right', label='right')
"""