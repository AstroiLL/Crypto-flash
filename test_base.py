from DiLL.crypto import Crypto
# import pandas as pd

if __name__ == '__main__':
    period = '1h'
    if period == '1m':
        per = '1min'
    else:
        per = period
    crypto = 'DOGE/USD'
    cry = Crypto(verbose=True)
    cry.open(exchange='BITMEX', crypto=crypto, period=period)
    cry.update_crypto()
    df = cry.load_crypto()
    df = df.resample(per).first()
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

