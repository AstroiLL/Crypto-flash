from DiLL.crypto import Crypto
# import pandas as pd

if __name__ == '__main__':
    per = '1m'
    cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period=per, update=True)
    cry.update_crypto()
    df = cry.load_crypto()
    df.to_hdf(f'../Data/BTC/btc-{per}.tf', mode='w', key=per, format='f')
