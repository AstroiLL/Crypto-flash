import os
import pandas as pd
from db_aggr import Db, BTC
from datetime import datetime

path = '/home/astroill/Data/aggr-server/data-copy'
start_date = '2022-02-09'
now_date = datetime.now().strftime("%Y-%m-%d")
print("Сегодня:", now_date)
db = Db('sqlite', '/home/astroill/Data/CF/btc_all_max.db')
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
            # 10 объем выше которого берется всплеск
            dfv = df[df['vol'] >= 10]
            if not dfv.empty:
                dfv.set_index('time', drop=True, inplace=True)
                r = dfv.resample('1min')
                df1m = r.agg({'close': "mean", 'vol': "sum", 'dir': 'max', 'liq': 'min'})
                df1m = df1m.reset_index().dropna()
                # print(df1m)
                session.flush()
                for i in range(len(df1m)):
                    btc0 = BTC(df1m.iloc[i, :])
                    if not session.query(BTC).filter(BTC.time == btc0.time).all():
                        print('btc0', btc0)
                        session.add(btc0)
session.commit()
# print(session.query(BTC).all())
