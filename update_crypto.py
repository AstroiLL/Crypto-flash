from DiLL.crypto import Crypto
import pandas as pd


def find_max_vol(df, day):
    # if df.index[day]:
    #     return None
    # try:
    print(day)
    day_m = df['Volume'].loc[day: day + pd.DateOffset(days=1)].idxmax()
    # except:
    #     return None
    return day_m


if __name__ == '__main__':
    cry_d = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1d', indexes=True, update=True)
    # cry_d.update_crypto()
    df_d = cry_d.load_crypto()

    cry_m = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1h', indexes=True, update=True)
    # cry_m.update_crypto()
    df_m = cry_m.load_crypto()
    # print(df_m)

    start_d = df_m.index[0]
    index = df_d.index > start_d
    for day in df_d.index[index][:-1]:
        # print(day, find_max_vol(df_m, day))
        df_d.loc[df_d.index == day, 'Vol_date'] = find_max_vol(df_m, day)
    # df_d.loc['Vol_date'] = df_d.applymap(find_max(df_d, df_d.index))
    # print(df_d.index[-1], '<>', find_max_vol(df_m, df_d.index[0]))
    print(df_d)
