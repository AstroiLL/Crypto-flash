from DiLL.crypto import Crypto

if __name__ == '__main__':
    cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1d', indexes=True, update=True)
    cry.update_crypto()
    cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1h', indexes=True, update=True)
    cry.update_crypto()
    cry = Crypto(exchange='BITMEX', crypto='BTC/USD', period='1m', indexes=True, update=True)
    cry.update_crypto()
