from sqlalchemy import Column, Integer, String, TIMESTAMP, Float
# from sqlalchemy import ForeignKey
from sqlalchemy import create_engine, select
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import pandas as pd

Base = declarative_base()


class Exch(Base):
    __tablename__ = 'exch'

    id = Column(Integer, primary_key=True)
    name = Column(String(20))
    pair = Column(String(20))

    def __init__(self, name, pair):
        self.name = name
        self.pair = pair

    def __repr__(self):
        return f"Exch(id={self.id!r}, name={self.name!r}, pair={self.pair!r})"


class BTC(Base):
    __tablename__ = 'btc'

    time = Column(TIMESTAMP, nullable=False, primary_key=True)
    close = Column(Float)
    vol = Column(Float)
    dir = Column(Integer)
    liq = Column(Integer)

    # def __init__(self, time, close, vol, d, liq):
    #     # print(time)
    #     self.time = time
    #     self.close = close
    #     self.vol = vol
    #     self.dir = d
    #     self.liq = liq

    def __init__(self, df):
        self.time = df.time
        self.close = df.close
        self.vol = df.vol
        self.dir = int(df.dir)
        self.liq = int(df.liq)

    def get(self):
        time = self.time
        close = self.close
        vol = self.vol
        df = pd.DataFrame({'time': self.time, 'close': self.close, 'vol': self.vol})
        # print(df)
        return df

    def __repr__(self):
        return f"BTC(time={self.time!r}, close={self.close!r}, vol={self.vol!r}, dir={self.dir!r}, liq={self.liq!r})"


class Db():
    def __init__(self, sql_base='sqlite', name_base='btc.db'):
        if sql_base == 'sqlite':
            connect_base = f'sqlite+pysqlite:///{name_base}'
        elif sql_base == 'mysql':
            connect_base = f'mysql://bitok:bitok@10.10.10.200:3307/{name_base}'
        else:
            connect_base = f'sqlite+pysqlite:///{name_base}'

        self.engine = create_engine(connect_base, echo=False, future=True)
        Base.metadata.create_all(self.engine)

    def open(self):
        Session = sessionmaker(bind=self.engine)
        return Session()



if __name__ == '__main__':
    db = Db('sqlite', 'test.db')
    session = db.open()
    session.add(Exch("Binance", "btcusdt"))
    print(session.query(Exch).all())
    session.add(Exch("Bitmex", "xbtusd"))
    print(session.query(Exch).all())
    session.commit()
    print('Table name:', Exch.__table__)
    print(select(Exch))

    btc1 = BTC(datetime.utcfromtimestamp(1648735464660/1000), 46350, 134, 1, None)
    session.add(btc1)
    print(session.query(BTC).all())
    btc2 = BTC(datetime.utcfromtimestamp(1648736090835/1000), 46510, 324, 1, None)
    session.add(btc2)
    print(session.query(BTC).all())
    session.commit()
    print('Table name:', BTC.__table__)
    print(select(BTC))

"""
from sqlalchemy import select
from sqlalchemy.orm import Session

stmt = select(User).where(User.name == 'spongebob')
with Session(engine) as session:
    for row in session.execute(stmt):
        print(row)

print(select(User))
row = session.execute(select(User)).first()
print(row)
print(row[0])
print(select(User.name, User.fullname))
row = session.execute(select(User.name, User.fullname)).first()
print(row)
for row in session.execute(
        select(User.name, Address).
                where(User.id == Address.user_id).
                order_by(Address.id)
).all():
    print(row)

from sqlalchemy import and_, or_

print(
    select(Address.email_address).
        where(
        and_(
            or_(User.name == 'squidward', User.name == 'sandy'),
            Address.user_id == User.id
        )
    )
)

# Аналог WHERE
print(
    select(User).filter_by(name='spongebob', fullname='Spongebob Squarepants')
)

# ORDER BY
print(select(User).order_by(User.fullname.desc()))
print(select(User).order_by(User.fullname.asc()))

#   GROUP BY / HAVING
from sqlalchemy import func

with engine.connect() as conn:
    result = conn.execute(
        select(User.name, func.count(Address.id).label("count")).
            join(Address).
            group_by(User.name).
            having(func.count(Address.id) > 1)
    )
    print(result.all())

from sqlalchemy import func, desc, update, delete

stmt = select(
    Address.user_id,
    func.count(Address.id).label('num_addresses')
). \
    group_by("user_id").order_by("user_id", desc("num_addresses"))
print(stmt)

from sqlalchemy.orm import aliased

address_alias_1 = aliased(Address)
address_alias_2 = aliased(Address)
print(
    select(User).
        join_from(User, address_alias_1).
        where(address_alias_1.email_address == 'patrick@aol.com').
        join_from(User, address_alias_2).
        where(address_alias_2.email_address == 'patrick@gmail.com')
)

# INSER UPDATE DELETE
squidward = User(name="squidward", fullname="Squidward Tentacles")
krabs = User(name="ehkrabs", fullname="Eugene H. Krabs")
print(squidward)
session = Session(engine)
session.add(squidward)
session.add(krabs)
print(session.new)
session.flush()
some_squidward = session.get(User, 4)
print(some_squidward)
session.commit()
sandy = session.execute(select(User).filter_by(name="sandy")).scalar_one()
print(sandy)
sandy.fullname = "Sandy Squirrel"
print(sandy in session.dirty)
sandy_fullname = session.execute(
    select(User.fullname).where(User.id == 2)
).scalar_one()
print(sandy_fullname)
print(sandy in session.dirty)
#     Операторы UPDATE с поддержкой ORM
session.execute(
    update(User).
    where(User.name == "sandy").
    values(fullname="Sandy Squirrel Extraordinaire")
)
print(sandy.fullname)
#Удаление объектов ORM
patrick = session.get(User, 3)
session.delete(patrick)
session.execute(select(User).where(User.name == "patrick")).first()
print(patrick in session)
#Операторы DELETE с поддержкой ORM
squidward = session.get(User, 4)
session.execute(delete(User).where(User.name == "squidward"))
print(squidward in session)
# RollBACK
#...
session.close()

#     Работа со связанными объектами
u1 = User(name='pkrabs', fullname='Pearl Krabs')
print(u1.addresses)
a1 = Address(email_address="pearl.krabs@gmail.com")
u1.addresses.append(a1)
print(u1.addresses)
print(a1.user)
a2 = Address(email_address="pearl@aol.com", user=u1)
print(u1.addresses)
session.add(u1)
print(u1 in session)
print(a1 in session)
print(a2 in session)
print(u1.id)
print(a1.user_id)
session.commit()
print(u1.id)
print(
    select(Address.email_address).
    select_from(User).
    join(User.addresses)
)
#формы: has () / any ()
stmt = (
  select(User.fullname).
  where(User.addresses.any(Address.email_address == 'pearl.krabs@gmail.com'))
)
print(session.execute(stmt).all())
print(select(Address).where(Address.user == u1))
print(select(Address).where(Address.user != u1))
print(select(User).where(User.addresses.contains(a1)))
from sqlalchemy.orm import with_parent
print(select(Address).where(with_parent(u1, User.addresses)))
"""
