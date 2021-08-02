import plotly.graph_objects as go
# import numpy as np
import pandas as pd
from MLDiLL.crypto import CryptoH

# np.random.seed(1)

# N = 70
cry = CryptoH(limit=24)
df = pd.DataFrame(cry.get_df()[['Volume', 'Open_max', 'Date_max']])
df['V'] = 0

fig = go.Figure(data=[
    go.Scatter3d(
        x=df.index,
        z=df['V'],
        y=df['Open_max'],
        marker=dict(
            size=6,
            color=df['Volume'],
            colorscale='Viridis',
        ),
    ),
    go.Scatter3d(
        x=df.index,
        z=df['Volume'],
        y=df['Open_max'],
        marker=dict(
            size=2,
            color=df['Volume'],
            colorscale='Viridis',
        ),
    )
])
fig.update_layout(
    # scene=dict(
    #     xaxis=dict(nticks=4, range=[-100, 100], ),
    #     yaxis=dict(nticks=4, range=[-50, 100], ),
    #     zaxis=dict(nticks=4, range=[-100, 100], ), ),
    width=700,
    margin=dict(r=20, l=10, b=10, t=10)
)

fig.show()
