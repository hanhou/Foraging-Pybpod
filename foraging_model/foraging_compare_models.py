import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import foraging_model
import ray



@ray.remote
def runmodel_paralel(runnum, tau_1, tau_2, filter_tau_slow_amplitude,filter_constant,softmax_temperature):
    rewardrate = list()
    trialnum = 0
    while len(rewardrate) < runnum:
        p_reward_L, p_reward_R, n_trials = foraging_model.generate_block_structure(n_trials_base=80,n_trials_sd=10,blocknum = 8, reward_ratio_pairs=np.array([[.4,.05],[.3857,.0643],[.3375,.1125]]))
        rewards = foraging_model.run_task(p_reward_L,
                                          p_reward_R,
                                          n_trials,
                                          unchosen_rewards_to_keep = 1,
                                          subject = 'clever mouse',
                                          min_rewardnum = 30, 
                                          filter_tau_fast = tau_1,
                                          filter_tau_slow = tau_2, 
                                          filter_tau_slow_amplitude = filter_tau_slow_amplitude, 
                                          filter_constant = filter_constant,
                                          softmax_temperature = softmax_temperature,
                                          differential = True,
                                          plot = False)

        rewardrate.append(np.mean(rewards))
        trialnum += sum(n_trials)
    #trialnums.append(trialnum)
    return np.mean(rewardrate),np.std(rewardrate),trialnum
# =============================================================================
# #%% 2 exponentials
# 
# taus = np.logspace(0, 8, 10,base = 2)#list(range(1,30))
# #amplitudes = np.arange(0.,1.1,.1)
# amplitudes = np.logspace(-2, 0, 10,base = 10)
# trialnums = list()
# runnum = 10
# rewardrates_mean = np.zeros((len(amplitudes),len(taus),len(taus)))
# rewardrates_sd = np.zeros((len(amplitudes),len(taus),len(taus)))
# trialnum = np.zeros((len(amplitudes),len(taus),len(taus)))
# for ampl_i,filter_tau_slow_amplitude in enumerate(amplitudes):
#     for tau_1_i,tau_1 in enumerate(taus):
#         result_ids = []
#         print('ampl:'+str(filter_tau_slow_amplitude)+' tau1:'+str(tau_1))
#         for tau_2_i,tau_2 in enumerate(taus):
#             #print('taus now:' + str(tau_1) + ' and '+ str(tau_2))
#              result_ids.append(runmodel_paralel.remote(runnum, tau_1, tau_2, filter_tau_slow_amplitude))        
#         results = ray.get(result_ids)
#         for tau_2_i, result in enumerate(results):
#             rewardrates_mean[ampl_i,tau_1_i,tau_2_i] = result[0]            
#             rewardrates_sd[ampl_i,tau_1_i,tau_2_i] = result[1]            
#             trialnum[ampl_i,tau_1_i,tau_2_i] = result[2]            
# ray.shutdown()
# 
# =============================================================================


#%%  softmax and single exponential
ray.init(num_cpus = 7)
taus = np.logspace(-2, 7, 50,base = 2)#list(range(1,30))

temperatures= np.logspace(-3, 2, 50,base = 10)
trialnums = list()
runnum = 100
rewardrates_mean = np.zeros((len(temperatures),len(taus)))
rewardrates_sd = np.zeros((len(temperatures),len(taus)))
trialnum = np.zeros((len(temperatures),len(taus)))
for ampl_i,softmax_temperature in enumerate(temperatures):
    result_ids = []
    for tau_1_i,tau_1 in enumerate(taus):
        print('temperature:'+str(softmax_temperature)+' tau:'+str(tau_1))
        result_ids.append(runmodel_paralel.remote(runnum, tau_1, 20, 0,0,softmax_temperature))        
    results = ray.get(result_ids)
    for tau_1_i, result in enumerate(results):
        rewardrates_mean[ampl_i,tau_1_i] = result[0]            
        rewardrates_sd[ampl_i,tau_1_i] = result[1]            
        trialnum[ampl_i,tau_1_i] = result[2]            

ray.shutdown()
datatosave = dict()
datatosave['taus'] = taus
datatosave['temperatures'] = temperatures
datatosave['rewardrate_mean'] = rewardrates_mean
datatosave['rewardrate_sd'] = rewardrates_sd
datatosave['trialnum'] = trialnum
np.save('/home/rozmar/Data/Behavior/Model/Leaky_integrator/30_trials_back_exp_and_softmax_differential.npy', datatosave)
#%% plot
from scipy.ndimage import gaussian_filter
reward_rate_filt = gaussian_filter(rewardrates_mean, sigma = 1)
fig=plt.figure()
ax= fig.add_axes([0,0,2,2])
im = ax.imshow(reward_rate_filt,cmap='jet')#, vmin=.225, vmax=.45
ax.set_xticks(np.arange(0,len(taus),3))
ax.set_xticklabels(np.round(taus[np.arange(0,len(taus),3)],2))
ax.set_yticks(np.arange(0,len(temperatures),3))
ax.set_yticklabels(np.round(temperatures[np.arange(0,len(temperatures),3)],5))
ax.set_xlabel('tau (trial)')
ax.set_ylabel('inverse temperature parameter')
fig.colorbar(im)

#%% single exponential and constant
ray.init(num_cpus = 7)
taus = np.logspace(-2, 7, 50,base = 2)#list(range(1,30))
amplitudes = np.logspace(-5, 2, 50,base = 10)
trialnums = list()
runnum = 150
rewardrates_mean = np.zeros((len(amplitudes),len(taus)))
rewardrates_sd = np.zeros((len(amplitudes),len(taus)))
trialnum = np.zeros((len(amplitudes),len(taus)))
for ampl_i,constant_amplitude in enumerate(amplitudes):
    result_ids = []
    for tau_1_i,tau_1 in enumerate(taus):
        print('ampl:'+str(constant_amplitude)+' tau:'+str(tau_1))
        result_ids.append(runmodel_paralel.remote(runnum, tau_1, 20, 0,constant_amplitude))        
    results = ray.get(result_ids)
    for tau_1_i, result in enumerate(results):
        rewardrates_mean[ampl_i,tau_1_i] = result[0]            
        rewardrates_sd[ampl_i,tau_1_i] = result[1]            
        trialnum[ampl_i,tau_1_i] = result[2]            

ray.shutdown()
datatosave = dict()
datatosave['taus'] = taus
datatosave['amplitudes'] = amplitudes
datatosave['rewardrate_mean'] = rewardrates_mean
datatosave['rewardrate_sd'] = rewardrates_sd
datatosave['trialnum'] = trialnum
np.save('/home/rozmar/Data/Behavior/Model/Leaky_integrator/30_trials_back_exp_and_constant.npy', datatosave)

#%% plot
from scipy.ndimage import gaussian_filter
reward_rate_filt = gaussian_filter(rewardrates_mean, sigma = .1)
fig=plt.figure()
ax= fig.add_axes([0,0,2,2])
im = ax.imshow(reward_rate_filt,cmap='jet')
ax.set_xticks(np.arange(0,len(taus),3))
ax.set_xticklabels(np.round(taus[np.arange(0,len(taus),3)],2))
ax.set_yticks(np.arange(0,len(amplitudes),3))
ax.set_yticklabels(np.round(amplitudes[np.arange(0,len(amplitudes),3)],5))
ax.set_xlabel('tau (trial)')
ax.set_ylabel('offset')
fig.colorbar(im)
