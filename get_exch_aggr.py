import os

# import pandas as pd
# import numpy as np
from db.db_aggr import Db_sqlite, Exch

path = '/home/astroill/Data/aggr-server/data/'
db = Db_sqlite('aggr02.db')
ses = db.open()
c = 0
for dirs, folder, files in os.walk(path):
    if len(files) > 0:
        dir1, folder2 = os.path.split(dirs)
        _, folder1 = os.path.split(dir1)
        c += 1
        # print(c)
        # print(c, folder1, folder2)
        if ses.query(Exch.id).filter_by(name=folder1).filter_by(pair=folder2).scalar() is None:
            print(c)
            ses.add(Exch(folder1, folder2))
ses.commit()
for row in ses.query(Exch).filter_by(id=21).all():
    print(row)
okex21 = ses.query(Exch).filter_by(id=21).first()
okex21.pair = 'ZZZ'
print(ses.dirty)
ses.commit()
for row in ses.query(Exch).filter_by(id=21).all():
    print(row)
print(ses.query(Exch).filter(Exch.name.in_(['OKEX'])).all())
