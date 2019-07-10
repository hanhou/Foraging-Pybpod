#%% importing modules
import behavior_rozmar as behavior_rozmar
import pandas as pd
import numpy as np

#%% load data
bigtable = behavior_rozmar.loadcsvdata(projectdir = '/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects')

#%% 
data = bigtable

subjects = data['subject'].unique()
subject = 'St61'
data = data[data['subject']==subject ]

experiments = data['experiment'].unique()
experiment = 'Foraging_phase_0'
data = data[data['experiment']==experiment ]

setups = data['setup'].unique()
setup = '2 - Zaber'
data = data[data['setup']==setup ]

#%%
idxes = dict()
times = dict()
values = dict()

sessions = bigtable['session'].unique()
sessions = np.sort(sessions)





idxes['GoCue'] = (data['MSG'] == 'GoCue') & (data['TYPE'] == 'TRANSITION')
times['GoCue'] = data['PC-TIME'][idxes['GoCue']]
