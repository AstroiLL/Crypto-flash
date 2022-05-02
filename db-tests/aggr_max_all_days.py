import os
import pandas as pd
# from datetime import datetime

"""
Находятся все максимумы >= maxBTC
И дописываются в excel
"""
maxBTC = 10
path = '/home/astroill/Data/aggr-server/data-copy'
start_date = '2022-04-28'
now_date = '2022-04-28'
# now_date = datetime.now().strftime("%Y-%m-%d")
print("Сегодня:", now_date)
columns = ['exch', 'pairs', 'date', 'time_max', 'close', 'vol']
df_maxs = pd.DataFrame([], columns=columns)
for dirs, folder, files in os.walk(path):
    for file in files:
        fname, ext = os.path.splitext(file)
        date = fname[:10]
        if ext == '.gz' and date >= start_date:
            # print(date)
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
            # print(df)
            if vmax >= maxBTC:
                imax = df['vol'].argmax()
                tmax = df.time[imax]
                cmax = df.close[imax]
                df_add = pd.DataFrame({'exch': folder1, 'pairs': folder2, 'date': fname, 'time_max': tmax, 'close': cmax, 'vol': vmax}, index=[0])
                print(df_add)
                df_maxs = pd.concat([df_maxs, df_add], ignore_index=True)
print(df_maxs)
df_maxs.to_excel(f"aggr_add_{start_date}_{now_date}.xlsx", sheet_name=f"add from {start_date} to {now_date}")