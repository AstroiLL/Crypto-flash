from sqlalchemy import ForeignKey
from sqlalchemy import Table, Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

engine = create_engine("sqlite+pysqlite:///sqla.dbiLL", echo=True, future=True)
Base = declarative_base()


class User(Base):
    __tablename__ = 'user_account'

    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    fullname = Column(String)

    addresses = relationship("Address", back_populates="user")

    def __repr__(self):
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"


class Address(Base):
    __tablename__ = 'address'

    id = Column(Integer, primary_key=True)
    email_address = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey('user_account.id'))

    user = relationship("User", back_populates="addresses")

    def __repr__(self):
        return f"Address(id={self.id!r}, email_address={self.email_address!r})"


print(User.__table__)
Base.metadata.create_all(engine)

sandy = User(name="sandy", fullname="Sandy Cheeks")
# sandy.email_address = "a@b.ru"
print(sandy)

from sqlalchemy import MetaData

metadata_obj = MetaData()
from sqlalchemy import text

# "commit as you go"
with engine.connect() as conn:
    # conn.execute(text("CREATE TABLE some_table (x int, y int)"))
    conn.execute(
        text("INSERT INTO some_table (x, y) VALUES (:x, :y)"),
        [{"x": 1, "y": 1}, {"x": 2, "y": 4}]
    )
    conn.commit()

# Из существующей БД в таблицу
some_table = Table("some_table", metadata_obj, autoload_with=engine)
print(some_table.c)

# for row in some_table.c:
#     print(f"x: {row.x}  y: {row.y}")

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