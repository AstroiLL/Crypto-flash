from datetime import datetime
ts = int('1648735464660')

# if you encounter a "year is out of range" error the timestamp
# may be in milliseconds, try `ts /= 1000` in that case
print(datetime.utcfromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S'))
