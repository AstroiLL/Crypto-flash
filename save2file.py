from DiLL.crypto import Crypto
import pandas as pd

if __name__ == '__main__':
    cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1d', indexes=True, update=True)
    cry.update_crypto()
    df = cry.load_crypto()
    # df.to_hdf('../Data/BTC/btc-1d.tf', key='1d', format='f')
    # df.to_hdf('../Data/BTC/btc-1d.tf', key='1d')
    # cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1h', indexes=True, update=True)
    # cry.update_crypto()
    # df = cry.load_crypto()
    # df.to_hdf('../Data/BTC/btc.tf', key='1h', format='f')
    # cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1m', indexes=True, update=True)
    # cry.update_crypto()
    # df = cry.load_crypto()
    # df.to_hdf('../Data/BTC/btc.tf', key='1m', format='f')

    # df = pd.read_hdf('../Data/BTC/btc-1m.h5')
    print(df)
