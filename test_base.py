from DiLL.crypto import Crypto
# import pandas as pd

if __name__ == '__main__':
    per = '1m'
    crypto = 'BTC/USD'
    cry = Crypto(verbose=False)
    cry.open(exchange='BITMEX', crypto=crypto, period=per)
    cry.update_crypto()
    df = cry.load_crypto()
    df = df.resample('1min').first()
    holes = df[df['Open'].isna()].index
    # print(holes)
    holes = holes[::1]
    # print(holes)
    c = 1
    l = len(holes)
    for i in holes.sort_values(ascending=True):
        print(f'({c}/{l}) {i}')
        c += 1
        cry.update_crypto_from(from_date=i, count=1)

