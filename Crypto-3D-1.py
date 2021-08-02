import plotly.graph_objects as go
# import numpy as np
import pandas as pd
from MLDiLL.crypto import CryptoH

# np.random.seed(1)

# N = 70
# cry = CryptoH(limit=24)
# df = pd.DataFrame(cry.get_df()[['Volume', 'Open_max', 'Date_max']])
# df['V'] = 0
x = [1, 1, 2, 2]
y = [1, 1, 2, 2]
z = [0, 1, 0, 1]
# x = [0, 1, 2, 3, 4, 5, 6, 7, 8, 8, 7, 6, 5, 4, 3, 2, 1, 0]
# y = [0.5, 1.5, 2.2, 2.5, 2.7, 2.5, 2.2, 1.5, 0.5, 0.5, 1.5, 2.2, 2.5, 2.7, 2.5, 2.2, 1.5, 0.5]
# z = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1]

fig = go.Figure(
    data=go.Mesh3d(
        x=x,
        y=y,
        z=z
    )
)
fig.show()
