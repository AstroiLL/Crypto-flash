from DiLL.crypto import Crypto
# import pandas as pd

if __name__ == '__main__':
    per1 = '1h'
    crypto1 = 'BTC/USD'
    per2 = '1m'
    crypto2 = 'BTC/USD'
    # pref = '1'
    cry = Crypto()
    # cry.open(exchange='BITMEX', crypto=crypto1, period=per1, update=True)
    # cry.update_crypto()
    # df = cry.load_crypto()
    # # df.to_hdf(f'../Data/BTC/{pref}-{crypto.replace("/","-")}-{per}.tf', mode='w', key=per, format='f')
    # print(df)
    cry.open(exchange='BITMEX', crypto=crypto2, period=per2, update=True)
    cry.update_crypto()
    df = cry.load_crypto()
    # df.to_hdf(f'../Data/BTC/{pref}-{crypto.replace("/","-")}-{per}.tf', mode='w', key=per, format='f')
    print(df)
    diff = df.index - df.index.shift(-1)
    print(diff.unique())

