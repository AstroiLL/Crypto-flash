import pandas as pd
from db.db_aggr import Db, BTC
from MLDiLL.cryptoA import CryptoA
from sqlalchemy import select

if __name__ == '__main__':
    cry_1m = CryptoA(period='1m', verbose=False)
    cry_1m.load(limit=43200*6)
    # cry_1m.load(limit=1440)
    df = cry_1m.df.reset_index()[['Date', 'Open']]
    df.columns = ['ds', 'y']
    # Открытие базы всплесков объемов
    db = Db('sqlite', '/home/astroill/Data/CF/btc_all.db')
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
    df.to_hdf('/home/astroill/Data/CF/BTC.h5', 'm1_6M_v')
