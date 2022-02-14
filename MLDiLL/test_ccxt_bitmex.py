import ccxt

exchange = ccxt.bitmex(
    {
        'enableRateLimit': True,  # or .enableRateLimit = True later
    }
)

# symbol = 'BTC/USD:BTC'
symbol = '.XBT'

# fetch = exchange.fetch_ohlcv('BITMEX', symbol, limit=1)
markets = exchange.load_markets()
print(exchange.symbols)

btc = exchange.markets[symbol]['info']
# ['markPrice']

print(btc)
