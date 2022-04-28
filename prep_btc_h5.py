import pandas as pd
from db.db_btc import Db, BTC
from MLDiLL.cryptoA import CryptoA
from sqlalchemy import select

"""
Программа формирования файла BTC.h5 с котировками 1м за последние 3 месяца
Из файлов собраных агрегатором https://github.com/Tucsky/aggr-server
Используется модуль db_btc
Для быстрого использования с jupyter-notebook 
"""

if __name__ == '__main__':
    cry_1m = CryptoA(period='1m', verbose=False)
    # 43200 - количество минут в месяце
    # 3 - количество месяцев для сбора
    cry_1m.load(limit=43200*3)
    # cry_1m.load(limit=1440)
    df = cry_1m.df.reset_index()[['Date', 'Open']]
    df.columns = ['ds', 'y']
    # Открытие базы всплесков объемов
    db = Db('sqlite', '/home/astroill/Data/CF/btc_all_max.db')
    session = db.open()
    stmt = select(BTC)
    btc0 = []
    for btc in session.scalars(stmt):
        btc0.append({'ds': btc.time, 'v': btc.vol})
    btc_df = pd.DataFrame(btc0)
    df = df.set_index('ds').join(btc_df.set_index('ds'))
    df.fillna(0, inplace=True)
    ddf = df[df['v'] != 0]
    print(ddf)
    df.to_hdf('/home/astroill/Data/CF/BTC.h5', 'm1_3M_v')
