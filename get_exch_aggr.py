import os

# import pandas as pd
# import numpy as np
from db.db_aggr import Db_sqlite, Exch

path = '/home/astroill/Data/aggr-server/data/'
db = Db_sqlite('aggr02.db')
session = db.open()
c = 0
for dirs, folder, files in os.walk(path):
    if len(files) > 0:
        dir1, folder2 = os.path.split(dirs)
        _, folder1 = os.path.split(dir1)
        c += 1
        # print(c)
        print(c, folder1, folder2)
        session.add(Exch(folder1, folder2))
session.commit()
