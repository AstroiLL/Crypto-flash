from tradingview_ta import TA_Handler, Interval

btc = TA_Handler()
btc.set_symbol_as("BTC1!")
btc.set_exchange_as_crypto_or_stock("CME")
btc.set_screener_as_crypto()
btc.set_interval_as(Interval.INTERVAL_1_MONTH)
print(btc.get_analysis().summary)

