from sqlalchemy import create_engine, text, select, func
from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Session


class Base(DeclarativeBase):
    pass


class T1m(Base):
    __tablename__ = "T1m"
    Date: Mapped[str] = mapped_column(primary_key=True)
    Open: Mapped[float]
    High: Mapped[float]
    Low: Mapped[float]
    Close: Mapped[float]
    Volume: Mapped[float]

    def __repr__(self) -> str:
        return f"T1m(Date={self.Date!r}, Open={self.Open!r}, Close={self.Close!r})"


SQL_URL = "mysql+mysqldb://bitok:bitok@10.10.10.200:3307/BTC"

engine = create_engine(f'{SQL_URL}', pool_pre_ping=True, echo=True).connect()
# text("SELECT COUNT(*) FROM 1m ;")
# .where(T1m.Close > 23476)

print('===')
stmt = select(T1m)
with Session(engine) as session:
    for row in session.execute(stmt):
        print(row)

print('===')
stmt = select(T1m)
with Session(engine) as session:
    print(len(session.execute(stmt).all()))

print('===')
stmt = select(func.count("*")).select_from(T1m)
with Session(engine) as session:
    print(session.execute(stmt).scalar())

print('===')
with Session(engine) as session:
    q = session.query(T1m).where(T1m.Close > 23476)
    # print(q.count())
    print(q.all())
    for row in q.all():
        print(row.Date, row.Open, row.Volume)
