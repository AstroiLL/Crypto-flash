from DiLL.crypto import Crypto
# import pandas as pd

if __name__ == '__main__':
    per = '1m'
    crypto = 'ETH/USD'
    cry = Crypto(exchange='BITMEX', crypto=crypto, period=per, update=True)
    cry.update_crypto()
    df = cry.load_crypto()
    df.to_hdf(f'../Data/BTC/{crypto.replace("/","-")}-{per}.tf', mode='w', key=per, format='f')
    