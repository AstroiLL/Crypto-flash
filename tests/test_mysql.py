from sqlalchemy import create_engine, text

SQL_URL = "mysql+mysqldb://bitok:bitok@10.10.10.200:3307/BTC"

con = create_engine(f'{SQL_URL}', pool_pre_ping=True).connect()
co = con.execute(text("SELECT COUNT(*) FROM 1m ;"))
count = co.fetchone()[0]
con.close()
print(count)
