import os

import pandas as pd
import numpy as np

path = '/home/astroill/Data/aggr-server/data1'

for dirs, folder, files in os.walk(path):
    for file in files:
        _, ext = os.path.splitext(file)
        if ext == '.gz':
            dir1, folder2 = os.path.split(dirs)
            _, folder1 = os.path.split(dir1)
            fullname = os.path.join(dirs, file)
            print()
            print(fullname)
            print(folder1, folder2)

            df = pd.read_csv(fullname, sep=' ', names=['time', 'close', 'vol', 'dir', 'liq'],
                             parse_dates=['time'], infer_datetime_format=False, dtype={'dir': 'Int32', 'liq': 'Int32'}
                             )
            df['exch'] = folder1
            df['coin'] = folder2
            df.fillna(0, inplace=True)
            df = df[['time', 'exch', 'coin', 'close', 'vol', 'dir', 'liq']]
            # print(df.head(10))
            df['time'] = pd.to_datetime(df['time'], unit='ms', infer_datetime_format=True)
            df.set_index('time', drop=True, inplace=True)
            # print(df.head(10))
            r = df.resample('1min')
            dfr = r.agg({'close': "mean", 'vol': "sum", 'dir': 'mean'})
            dfr['exch'] = folder1
            dfr['coin'] = folder2
            print('Vol')
            print(dfr[['close', 'vol', 'dir']])

            dfl = df[df['liq'] == 1]
            r = dfl.resample('1min')
            dflr = r.agg({'close': "mean", 'vol': "sum", 'dir': 'mean'})
            dflr.dropna(inplace=True)
            dflr['exch'] = folder1
            dflr['coin'] = folder2
            print('Vol LIQ')
            print(dflr[['close', 'vol', 'dir']])
