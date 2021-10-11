from sqlalchemy import create_engine

engine = create_engine("sqlite+pysqlite:///sqla.db", echo=True, future=True)

from sqlalchemy import MetaData

metadata_obj = MetaData()
from sqlalchemy import Table, Column, Integer, String

user_table = Table(
    "user_account",
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('name', String(30)),
    Column('fullname', String)
)
print(user_table.c.name)
print(user_table.c.keys())
print(user_table.primary_key)

from sqlalchemy import ForeignKey

address_table = Table(
    "address",
    metadata_obj,
    Column('id', Integer, primary_key=True),
    Column('user_id', ForeignKey('user_account.id'), nullable=False),
    Column('email_address', String, nullable=False)
)
metadata_obj.create_all(engine)
from sqlalchemy import insert

stmt = insert(user_table).values(name='spongebob', fullname="Spongebob Squarepants")
print(stmt)
compiled = stmt.compile()
print(compiled.params)
with engine.connect() as conn:
    result = conn.execute(stmt)
    conn.commit()
with engine.connect() as conn:
    result = conn.execute(
        insert(user_table),
        [
            {"name": "sandy", "fullname": "Sandy Cheeks"},
            {"name": "patrick", "fullname": "Patrick Star"}
        ]
    )
    conn.commit()

# Deep Alchemy
from sqlalchemy import select, bindparam

scalar_subq = (
    select(user_table.c.id).
        where(user_table.c.name == bindparam('username')).
        scalar_subquery()
)

with engine.connect() as conn:
    result = conn.execute(
        insert(address_table).values(user_id=scalar_subq),
        [
            {"username": 'spongebob', "email_address": "spongebob@sqlalchemy.org"},
            {"username": 'sandy', "email_address": "sandy@sqlalchemy.org"},
            {"username": 'sandy', "email_address": "sandy@squirrelpower.org"},
        ]
    )
    conn.commit()

select_stmt = select(user_table.c.id, user_table.c.name + "@aol.com")
insert_stmt = insert(address_table).from_select(
    ["user_id", "email_address"], select_stmt
)
print(insert_stmt)

insert_stmt = insert(address_table).returning(address_table.c.id, address_table.c.email_address)
print(insert_stmt)

select_stmt = select(user_table.c.id, user_table.c.name + "@aol.com")
insert_stmt = insert(address_table).from_select(
    ["user_id", "email_address"], select_stmt
)
print(insert_stmt.returning(address_table.c.id, address_table.c.email_address))

# Core & orm

from sqlalchemy import select

stmt = select(user_table).where(user_table.c.name == 'spongebob')
print(stmt)
with engine.connect() as conn:
    for row in conn.execute(stmt):
        print(row)

print(select(user_table))
print(select(user_table.c.name, user_table.c.fullname))

stmt = (
    select(
        ("Username: " + user_table.c.name).label("username"),
    ).order_by(user_table.c.name)
)
with engine.connect() as conn:
    for row in conn.execute(stmt):
        print(f"{row.username}")

from sqlalchemy import text

stmt = (
    select(
        text("'some phrase'"), user_table.c.name
    ).order_by(user_table.c.name)
)
with engine.connect() as conn:
    print(conn.execute(stmt).all())

from sqlalchemy import literal_column

stmt = (
    select(
        literal_column("'some phrase'").label("p"), user_table.c.name
    ).order_by(user_table.c.name)
)
with engine.connect() as conn:
    for row in conn.execute(stmt):
        print(f"{row.p}, {row.name}")

print(user_table.c.name == 'squidward')
print(address_table.c.user_id > 10)
print(select(user_table).where(user_table.c.name == 'squidward'))
print(
    select(address_table.c.email_address).
        where(user_table.c.name == 'squidward').
        where(address_table.c.user_id == user_table.c.id)
)
print(
    select(address_table.c.email_address).
        where(
        user_table.c.name == 'squidward',
        address_table.c.user_id == user_table.c.id
    )
)
# FROM
print(select(user_table.c.name))
print(select(user_table.c.name, address_table.c.email_address))
print(
    select(user_table.c.name, address_table.c.email_address).
        join_from(user_table, address_table)
)
print(
    select(user_table.c.name, address_table.c.email_address).
        join(address_table)
)
print(
    select(address_table.c.email_address).
        select_from(user_table).join(address_table)
)

# SELECT count()
from sqlalchemy import func

print(
    select(func.count('*')).select_from(user_table)
)
# ON
print(
    select(address_table.c.email_address).
        select_from(user_table).
        join(address_table, user_table.c.id == address_table.c.user_id)
)
# ORDER BY
print(select(user_table).order_by(user_table.c.name))

#   GROUP BY / HAVING

count_fn = func.count(user_table.c.id)
print(count_fn)

# alias
user_alias_1 = user_table.alias()
user_alias_2 = user_table.alias()
print(
    select(user_alias_1.c.name, user_alias_2.c.name).
        join_from(user_alias_1, user_alias_2, user_alias_1.c.id > user_alias_2.c.id)
)
# ...
# INSERT UPDATE DELETE

from sqlalchemy import update

stmt = (
    update(user_table).where(user_table.c.name == 'patrick').
        values(fullname='Patrick the Star')
)
print(stmt)

stmt = (
    update(user_table).
        values(fullname="Username: " + user_table.c.name)
)
print(stmt)

from sqlalchemy import bindparam

stmt = (
    update(user_table).
        where(user_table.c.name == bindparam('oldname')).
        values(name=bindparam('newname'))
)
with engine.begin() as conn:
    conn.execute(
        stmt,
        [
            {'oldname': 'jack', 'newname': 'ed'},
            {'oldname': 'wendy', 'newname': 'mary'},
            {'oldname': 'jim', 'newname': 'jake'},
        ]
    )

# получение количества затронутых строк
with engine.begin() as conn:
    result = conn.execute(
        update(user_table).
            values(fullname="Patrick McStar").
            where(user_table.c.name == 'patrick')
    )
    print(result.rowcount)
