import os
import pandas as pd
from db_btc import Db, BTC
from datetime import datetime

"""
Из файлов собраных агрегатором https://github.com/Tucsky/aggr-server
(Агрегатор должен работать непрерывно столько времени, сколько данных вам надо собрать)
Вытаскиваются count_maxs максимумов за каждый час
И складываются в базу SQL (например sqlite или mySQL)
Начало сбора максимумов start_date до текущего момента now_date
В последствии эту базу можно использовать для визуализации на графиках
Для работы с SQL через SQLAlchemy используется модуль db.db_btc
Запускать программу можно много раз, она добавляет только отсутствующие значения
"""

count_maxs = 5
# Указать полный путь к папке где aggr-server собирает файлы
# Обычно это aggr-server/data
path = '/home/astroill/Data/aggr-server/data-copy'
# Начальная дата сбора данных
# Для ускорения указывайте дату последнюю или предпоследнюю предыдущего сбора
start_date = '2022-04-27'
now_date = datetime.now().strftime("%Y-%m-%d")
print("Сегодня:", now_date)
db = Db('sqlite', '/home/astroill/Data/CF/btc_all.db')
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
                parse_dates=['time'], infer_datetime_format=False, dtype={'dir': 'Int32', 'liq': 'Int32'}
                )
            df.fillna(0, inplace=True)
            df = df[['time', 'close', 'vol', 'dir', 'liq']]
            df['time'] = pd.to_datetime(df['time'], unit='ms', infer_datetime_format=True)
            # df.set_index('time', drop=True, inplace=True)
            vmax = df['vol'].max()
            imax = df['vol'].argmax()
            tmax = df.time[imax]
            cmax = df.close[imax]
            # print(folder1, folder2, tmax, cmax, vmax)
            df0 = df.sort_values(by=['vol'], ascending=False).iloc[0:count_maxs, :]
            # print('df0', df0)
            session.flush()
            for i in range(0, count_maxs):
                # btc0 = BTC(df0.time, df0.close, df0.vol, df0.dir, df0.liq)
                btc0 = BTC(df0.iloc[i, :])
                # if session.query(BTC.time).filter_by(time=btc0.time).scalar() is None:
                if not session.query(BTC).filter(BTC.time == btc0.time).all():
                    print('btc0', btc0)
                    session.add(btc0)
session.commit()
# print(session.query(BTC).all())
