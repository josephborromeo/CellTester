import numpy as np
import matplotlib.pyplot as plt

x = [0,1,2,3,4]
y = [0,1,2,3,4]

fig1, ax1 = plt.subplots(figsize=(12.8,7.2), tight_layout=True)
ax1.margins(x=0)
ax1.plot(x,y)

ax1.set_yticks(np.arange(0, 5, 0.2))

ax1.grid(True)



plt.show()