# -*- coding: utf-8 -*-
"""
Created on Wed Jul 29 14:26:18 2020

@author: Han
"""

import scipy.stats as stats
import matplotlib.pyplot as plt
import numpy as np

lower, upper, scale = 80, 200, 30
n = 10000

# Real truncated expon
X = stats.truncexpon(b=(upper-lower)/scale, loc=lower, scale=scale)
data = X.rvs(n)

# Old method
data_old = np.random.exponential(scale, n) + lower
data_old[data_old > upper] = upper

# Plotting
fig = plt.figure(1)
fig.clf()
ax = fig.subplots(2,2)
ax[0,0].hist(data, 100, density=True)

ax[0,1].hist(data_old, 100, density=True)
plt.show()
