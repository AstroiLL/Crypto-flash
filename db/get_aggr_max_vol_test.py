import os

import pandas as pd

from db_aggr import Db, BTC

path = '/home/astroill/Data/aggr-server/test'
db = Db('sqlite', 'bin_f_usdt.db')
session = db.open()

for dirs, folder, files in os.walk(path):
    for file in files:
        _, ext = os.path.splitext(file)
        if ext == '.gz':
            dir1, folder2 = os.path.split(dirs)
            _, folder1 = os.path.split(dir1)
            fullname = os.path.join(dirs, file)
            print()
            print(fullname)
            # print(folder1, folder2)

            df = pd.read_csv(
                fullname, sep=' ', names=['time', 'close', 'vol', 'dir', 'liq'],
                parse_dates=['time'], infer_datetime_format=False, dtype={'dir': 'Int32', 'liq': 'Int32'}
                )
            df.fillna(0, inplace=True)
            df = df[['time', 'close', 'vol', 'dir', 'liq']]
            df['time'] = pd.to_datetime(df['time'], unit='ms', infer_datetime_format=True)
            # df.set_index('time', drop=True, inplace=True)
            # print(df)
            df0 = df.sort_values(by=['vol'], ascending=False).iloc[0:5, :]
            print(df0)
            for i in range(0, 5):
                # btc0 = BTC(df0.time, df0.close, df0.vol, df0.dir, df0.liq)
                btc0 = BTC(df0.iloc[i, :])
                print(btc0)
                session.add(btc0)
session.commit()
print(session.query(BTC).all())
