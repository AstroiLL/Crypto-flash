from DiLL.crypto import Crypto
# import pandas as pd

if __name__ == '__main__':
    per = '1h'
    crypto = 'BTC/USD'
    cry = Crypto(verbose=False)
    cry.open(exchange='BITMEX', crypto=crypto, period=per)
    # cry.update_crypto()
    df = cry.load_crypto()
    df = df.resample('1h').first()
    holes = df[df['Open'].isna()].index
    print(holes)
    c = 1
    l = len(holes)
    for i in holes.sort_values(ascending=False):
        print(f'({c}/{l}) {i}')
        cry.update_crypto_from(from_date=i, count=1)

