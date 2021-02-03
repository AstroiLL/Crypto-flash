from DiLL.crypto import Crypto
# import pandas as pd

if __name__ == '__main__':
    per1 = '1h'
    crypto1 = 'BTC/USD'
    per2 = '1m'
    crypto2 = 'BTC/USD'
    pref = '1'
    cry1 = Crypto()
    cry1.open(exchange='BITMEX', crypto=crypto1, period=per1, update=True)
    # cry1.update()
    df1 = cry1.load()
    df1.to_hdf(f'../Data/BTC/{pref}-{crypto1.replace("/","-")}-{per1}.tf', mode='w', key=per1, format='f')
    print(df1)

    cry2 = Crypto()
    cry2.open(exchange='BITMEX', crypto=crypto2, period=per2, update=True)
    # cry2.update()
    df2 = cry2.load()
    df2.to_hdf(f'../Data/BTC/{pref}-{crypto2.replace("/","-")}-{per2}.tf', mode='w', key=per2, format='f')
    print(df2)

