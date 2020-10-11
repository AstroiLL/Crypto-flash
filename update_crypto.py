from DiLL.crypto import Crypto
import pandas as pd

if __name__ == '__main__':
    # cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1d', indexes=True, update=True)
    # cry.update_crypto()
    # cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1h', indexes=True, update=True)
    # cry.update_crypto()
    # cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1m', indexes=True, update=True)
    # cry.update_crypto()
    # df = cry.load_crypto()
    # print(df)
    # df.to_hdf('../Data/BTC/btc-1m.h5', key='df', format='f')

    df = pd.read_hdf('../Data/BTC/btc-1m.h5')
    print(df)
