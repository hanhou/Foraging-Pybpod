#%%
from pathlib import Path
import numpy as np
import pandas as pd
from datetime import datetime
import time
import os
#%%
paths = ['/home/rozmar/Data/Behavior/Behavior_room/Tower-3','C:\\Users\\labadmin\\Documents\\Pybpod\\Projects']
for defpath in paths:
    if os.path.exists(defpath):
        break
#defpath = 'C:\\Users\\labadmin\\Documents\\Pybpod\\Projects'#'/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects'

def loaddirstucture(projectdir = Path(defpath),projectnames_needed = None, experimentnames_needed = None,  setupnames_needed=None):
    dirstructure = dict()
    projectnames = list()
    experimentnames = list()
    setupnames = list()
    sessionnames = list()
    subjectnames = list()
    if type(projectdir) != type(Path()):
        projectdir = Path(projectdir)
        
    for projectname in projectdir.iterdir():
        if projectname.is_dir() and (not projectnames_needed or projectname.name in projectnames_needed):
            dirstructure[projectname.name] = dict()
            projectnames.append(projectname.name)
            
            for subjectname in (projectname / 'subjects').iterdir():
                if subjectname.is_dir() : 
                    subjectnames.append(subjectname.name)            
            
            for experimentname in (projectname / 'experiments').iterdir():
                if experimentname.is_dir() and (not experimentnames_needed or experimentname.name in experimentnames_needed ): 
                    dirstructure[projectname.name][experimentname.name] = dict()
                    experimentnames.append(experimentname.name)
                    
                    for setupname in (experimentname / 'setups').iterdir():
                        if setupname.is_dir() and (not setupnames_needed or setupname.name in setupnames_needed ): 
                            setupnames.append(setupname.name)
                            dirstructure[projectname.name][experimentname.name][setupname.name] = list()
                            
                            for sessionname in (setupname / 'sessions').iterdir():
                                if sessionname.is_dir(): 
                                    sessionnames.append(sessionname.name)
                                    dirstructure[projectname.name][experimentname.name][setupname.name].append(sessionname.name)
    return dirstructure, projectnames, experimentnames, setupnames, sessionnames, subjectnames              

def load_and_parse_a_csv_file(csvfilename):
    df = pd.read_csv(csvfilename,delimiter=';',skiprows = 6)
    df = df[df['TYPE']!='|'] # delete empty rows
    df = df[df['TYPE']!= 'During handling of the above exception, another exception occurred:'] # delete empty rows
    df = df[df['MSG']!= ' '] # delete empty rows
    df = df[df['MSG']!= '|'] # delete empty rows
    df = df.reset_index(drop=True) # resetting indexes after deletion
    try:
        df['PC-TIME']=df['PC-TIME'].apply(lambda x : datetime.strptime(x,'%Y-%m-%d %H:%M:%S.%f')) # converting string time to datetime
    except ValueError: # sometimes pybpod don't write out the whole number...
        badidx = df['PC-TIME'].str.find('.')==-1
        if len(df['PC-TIME'][badidx]) == 1:
            df['PC-TIME'][badidx] = df['PC-TIME'][badidx]+'.000000'
        else:
            df['PC-TIME'][badidx] = [df['PC-TIME'][badidx]+'.000000']
        df['PC-TIME']=df['PC-TIME'].apply(lambda x : datetime.strptime(x,'%Y-%m-%d %H:%M:%S.%f')) # converting string time to datetime
    tempstr = df['+INFO'][df['MSG']=='CREATOR-NAME'].values[0]
    experimenter = tempstr[2:tempstr[2:].find('"')+2] #+2
    tempstr = df['+INFO'][df['MSG']=='SUBJECT-NAME'].values[0]
    subject = tempstr[2:tempstr[2:].find("'")+2] #+2
    df['experimenter'] = experimenter
    df['subject'] = subject
    # adding trial numbers in session
    idx = (df[df['TYPE'] == 'TRIAL']).index.to_numpy()
    idx = np.concatenate(([0],idx,[len(df)]),0)
    idxdiff = np.diff(idx)
    Trialnum = np.array([])
    for i,idxnumnow in enumerate(idxdiff): #zip(np.arange(0:len(idxdiff)),idxdiff):#
        Trialnum  = np.concatenate((Trialnum,np.zeros(idxnumnow)+i),0)
    df['Trial_number_in_session'] = Trialnum
# =============================================================================
#     # adding trial types
#     tic = time.time()
#     indexes = df[df['MSG'] == 'Trialtype:'].index + 1 #+2
#     if len(indexes)>0:
#         if 'Trialtype' not in df.columns:
#             df['Trialtype']=np.NaN
#         trialtypes = df['MSG'][indexes]
#         trialnumbers = df['Trial_number_in_session'][indexes].values
#         for trialtype,trialnum in zip(trialtypes,trialnumbers):
#             #df['Trialtype'][df['Trial_number_in_session'] == trialnum] = trialtype
#             df.loc[df['Trial_number_in_session'] == trialnum, 'Trialtype'] = trialtype
#     toc = time.time()
#     print(['trial types:',toc-tic])
# =============================================================================
    # adding block numbers
    indexes = df[df['MSG'] == 'Blocknumber:'].index + 1 #+2
    if len(indexes)>0:
        if 'Block_number' not in df.columns:
            df['Block_number']=np.NaN
        blocknumbers = df['MSG'][indexes]
        trialnumbers = df['Trial_number_in_session'][indexes].values
        for blocknumber,trialnum in zip(blocknumbers,trialnumbers):
            #df['Block_number'][df['Trial_number_in_session'] == trialnum] = int(blocknumber)
            df.loc[df['Trial_number_in_session'] == trialnum, 'Block_number'] = int(blocknumber)
    # adding trial numbers -  the variable names are crappy.. sorry
    indexes = df[df['MSG'] == 'Trialnumber:'].index + 1 #+2
    if len(indexes)>0:
        if 'Trial_number' not in df.columns:
            df['Trial_number']=np.NaN
        blocknumbers = df['MSG'][indexes]
        trialnumbers = df['Trial_number_in_session'][indexes].values
        for blocknumber,trialnum in zip(blocknumbers,trialnumbers):
            #df['Trial_number'][df['Trial_number_in_session'] == trialnum] = int(blocknumber)
            df.loc[df['Trial_number_in_session'] == trialnum, 'Trial_number'] = int(blocknumber)
    # saving variables (if any)
    variableidx = (df[df['MSG'] == 'Variables:']).index.to_numpy()
    if len(variableidx)>0:
        d={}
        exec('variables = ' + df['MSG'][variableidx+1].values[0], d)
        for varname in d['variables'].keys():
            if isinstance(d['variables'][varname], (list,tuple)):
                templist = list()
                for idx in range(0,len(df)):
                    templist.append(d['variables'][varname])
                df['var:'+varname]=templist
            else:
                df['var:'+varname] = d['variables'][varname]
    # saving motor variables (if any)
    variableidx = (df[df['MSG'] == 'LickportMotors:']).index.to_numpy()
    if len(variableidx)>0:
        d={}
        exec('variables = ' + df['MSG'][variableidx+1].values[0], d)
        for varname in d['variables'].keys():
            df['var_motor:'+varname] = d['variables'][varname]
    # extracting reward probabilities from variables
    if ('var:reward_probabilities_L' in df.columns) and ('Block_number' in df.columns):
        probs_l = df['var:reward_probabilities_L'][0]
        probs_r = df['var:reward_probabilities_R'][0]
        df['reward_p_L'] = np.nan
        df['reward_p_R'] = np.nan
        for blocknum in df['Block_number'].unique():
            if not np.isnan(blocknum):
                df.loc[df['Block_number'] == blocknum, 'reward_p_L'] = probs_l[int(blocknum-1)]
                df.loc[df['Block_number'] == blocknum, 'reward_p_R'] = probs_r[int(blocknum-1)]
    return df

def loadcsvdata(bigtable=pd.DataFrame(),
                projectdir = Path(defpath),
                projectnames_needed = None,
                experimentnames_needed = None,
                setupnames_needed = None,
                sessionnames_needed = None,
                load_only_last_day = False):
    bigtable_orig = bigtable
#bigtable=pd.DataFrame()
#projectdir = Path('/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects')
#projectdir = Path('/home/rozmar/Data/Behavior/Projects')
    if type(projectdir) != type(Path()):
        projectdir = Path(projectdir)
    if type(bigtable_orig) == pd.DataFrame and len(bigtable) > 0:
        sessionnamessofar = bigtable['session'].unique()
        sessionnamessofar = np.sort(sessionnamessofar)
        sessionnametodel = sessionnamessofar[-1]
        bigtable = bigtable[bigtable['session'] != sessionnametodel]
        sessionnamessofar = sessionnamessofar[:-1] # we keep reloading the last one
    else:
        sessionnamessofar = []
    projectnames = list()
    for projectname in projectdir.iterdir():
        if projectname.is_dir() and (not projectnames_needed or projectname.name in projectnames_needed): 
            projectnames.append(projectname)
            experimentnames = list()
            for experimentname in (projectname / 'experiments').iterdir():
                if experimentname.is_dir() and (not experimentnames_needed or experimentname.name in experimentnames_needed): 
                    experimentnames.append(experimentname)
                    setupnames = list()
                    for setupname in (experimentname / 'setups').iterdir():
                        if setupname.is_dir() and (not setupnames_needed or setupname.name in setupnames_needed): 
                            #if setupname.name == 'Foraging-0':
                            setupnames.append(setupname)
                            # a json file can be opened here
                            sessionnames = list()
                            
                            if load_only_last_day:
                                for sessionname in (setupname / 'sessions').iterdir():
                                    if sessionname.is_dir() and (not sessionnames_needed or sessionname.name in sessionnames_needed): 
                                        sessionnames.append(sessionname.name[:8])#only the date
                                sessionnames = np.sort(sessionnames)
                                sessiondatetoload = sessionnames[-1]
                                sessionnames = list()
                                
                            for sessionname in (setupname / 'sessions').iterdir():
                                if sessionname.is_dir() and (not sessionnames_needed or sessionname.name in sessionnames_needed) and (not load_only_last_day or sessiondatetoload in sessionname.name):
                                    sessionnames.append(sessionname)
                                    csvfilename = (sessionname / (sessionname.name + '.csv'))
                                    if csvfilename.is_file() and sessionname.name not in sessionnamessofar: #there is a .csv file
                                        df = load_and_parse_a_csv_file(csvfilename)
                                        df['project'] = projectname.name
                                        df['experiment'] = experimentname.name
                                        df['setup'] = setupname.name
                                        df['session'] = sessionname.name
                                        if type(bigtable) != pd.DataFrame or len(bigtable) == 0:
                                            bigtable = df
                                        else:
                                            for colname in df.columns:
                                                if colname not in bigtable.columns:
                                                    bigtable[colname]=np.NaN
                                            for colname in bigtable.columns:
                                                if colname not in df.columns:
                                                    df[colname]=np.NaN
                                            bigtable = bigtable.append(df)
                                    

    bigtable = bigtable.drop_duplicates(subset=['TYPE', 'PC-TIME', 'MSG', '+INFO'])
    if type(bigtable_orig) == pd.DataFrame and len(bigtable) != len(bigtable_orig):
        bigtable = bigtable.reset_index(drop=True)                                
    return bigtable
#%%
#bigtable = loadcsvdata(projectdir = '/home/rozmar/Data/Behavior/Projects')

#%%
#df = bigtable

    
