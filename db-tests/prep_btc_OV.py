# import pandas as pd
# from dbiLL.db_btc import Db, BTC
from MLDiLL.cryptoA import CryptoA
# from sqlalchemy import select


"""
Программа формирования файла BTC_OV.h5 с котировками 1м за последние 4 месяца
Из базы данных котировок (модуль MLDiLL.cryptoA)
Формируются WVWMA с разными периодами
Для быстрого использования в jupyter-notebook 
"""

if __name__ == '__main__':
    cry_1m = CryptoA(period='1m', verbose=False)
    # 60*24*30 - количество минут в месяце
    # 5 - количество месяцев для сбора
    cry_1m.load(limit=60*24*30*1)
    df = cry_1m.df[['Open', 'Volume']]
    df.to_hdf('~/Data/CF/BTC_OV.h5', 'm1')

