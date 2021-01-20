from DiLL.crypto import Crypto
# import pandas as pd

if __name__ == '__main__':
    per = '1d'
    crypto = 'LTC/USD'
    pref = '1'
    cry = Crypto()
    cry.connect(exchange='BITMEX', crypto=crypto, period=per, update=True)
    cry.update_crypto()
    df = cry.load_crypto()
    # df.to_hdf(f'../Data/BTC/{pref}-{crypto.replace("/","-")}-{per}.tf', mode='w', key=per, format='f')
    print(df)
    cry.connect(exchange='BITMEX', crypto='BTC/USD', period='1m', update=True)
    cry.update_crypto()
    df = cry.load_crypto()
    # df.to_hdf(f'../Data/BTC/{pref}-{crypto.replace("/","-")}-{per}.tf', mode='w', key=per, format='f')
    print(df)

