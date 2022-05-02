import pandas as pd
from dbiLL.db_btc import Db, BTC
from MLDiLL.cryptoA import CryptoA
from sqlalchemy import select

"""
Программа формирования файла BTC.h5 с котировками 1м за последние 3 месяца
Из базы данных котировок (модуль MLDiLL.cryptoA) и
Из файлов собраных агрегатором https://github.com/Tucsky/aggr-server
Используется модуль dbiLL.db_btc
Для быстрого использования в jupyter-notebook 
"""

if __name__ == '__main__':
    cry_1m = CryptoA(period='1m', verbose=False)
    # 43200 - количество минут в месяце
    # 3 - количество месяцев для сбора
    cry_1m.load(limit=43200*3)
    df = cry_1m.df.reset_index()[['Date', 'Close']]
    # Открытие базы всплесков объемов для чтения
    db = Db('sqlite', '/home/astroill/Data/CF/btc_max_more_10.db')
    session = db.open()
    stmt = select(BTC)
    btc0 = []
    for btc in session.scalars(stmt):
        btc0.append({'Date': btc.time, 'CloseA': btc.close, 'Volume': btc.vol})
    btc_df = pd.DataFrame(btc0)
    df = df.set_index('Date').join(btc_df.set_index('Date'))
    df.fillna(0, inplace=True)
    print(df[df['Volume'] != 0])
    df.to_hdf('/home/astroill/Data/CF/BTC.h5', 'm1_3M_v_a')
