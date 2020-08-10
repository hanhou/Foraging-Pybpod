# -*- coding: utf-8 -*-
"""
Created on Wed Jul 29 14:26:18 2020

Compare two methods in generating truncated exponential distributions.
1. stats.truncexpon --> more like exponential, but increasing hazard function
2. Marton's method --> peak at the maximum value, but quite flat hazard function

Marton's methods makes more sense if the point to keep hazard function as flat as possible.

@author: Han
"""

import scipy.stats as stats
import matplotlib.pyplot as plt
import numpy as np

# lower, upper, scale = 1.5, 10, 3   # ITI
lower, upper, scale = 50, 150, 30  # block
n = 10000

# Real truncated exponential
X = stats.truncexpon(b=(upper-lower)/scale, loc=lower, scale=scale)
truncexp = X.rvs(n)

# Old method
truncexp_old = np.random.exponential(scale, n) + lower
truncexp_old[truncexp_old > upper] = upper

# Plotting
fig = plt.figure(1)
fig.clf()

# Trunc exp
ax = fig.subplots(2,2)
truncexp_hist, xx, _ = ax[0,0].hist(truncexp, 100, density=True)    
truncexp_hazard = truncexp_hist / np.flip(np.flip(truncexp_hist).cumsum())
ax[0,0].set(title='TruncExp (scipy)', ylim=(0, max(truncexp_hist) * 1.5))
ax[0,0].axvline(truncexp.mean(), c='r', label='mean')
ax[0,0].axvline(np.median(truncexp), c='k', label='median')
ax[0,0].legend()

ax[1,0].plot(xx[:-1], truncexp_hazard)# Hazard func
ax[1,0].set(ylim=(0, 0.4))

# Trunc exp old
truncexp_old_hist, xx, _ = ax[0,1].hist(truncexp_old, 100, density=True)  
truncexp_old_hazard = truncexp_old_hist / np.flip(np.flip(truncexp_old_hist).cumsum())
ax[0,1].set(title='TruncExp (Marton)', ylim=(0, max(truncexp_hist) * 1.5))
ax[0,1].axvline(truncexp_old.mean(), c='r', label='mean')
ax[0,1].axvline(np.median(truncexp_old), c='k', label='median')

ax[1,1].plot(xx[:-1], truncexp_old_hazard)# Hazard func
ax[1,1].set(ylim=(0, 0.4))

plt.show()
