import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import foraging_model
import ray

ray.init()

@ray.remote
def runmodel_paralel(runnum, tau_1, tau_2, filter_tau_slow_amplitude):
    rewardrate = list()
    trialnum = 0
    while len(rewardrate) < runnum:
        p_reward_L, p_reward_R, n_trials = foraging_model.generate_block_structure(n_trials_base=200,n_trials_sd=0,blocknum = 10, reward_ratio_pairs=np.array([[.4,.05],[.3857,.0643],[.3375,.1125]]))
        rewards = foraging_model.run_task(p_reward_L,
                                          p_reward_R,
                                          n_trials,
                                          unchosen_rewards_to_keep = 1,
                                          subject = 'clever mouse',
                                          min_rewardnum = 10, 
                                          filter_tau_fast = tau_1,
                                          filter_tau_slow = tau_2, 
                                          filter_tau_slow_amplitude = filter_tau_slow_amplitude, 
                                          plot = False)

        rewardrate.append(np.mean(rewards))
        trialnum += sum(n_trials)
    #trialnums.append(trialnum)
    return np.mean(rewardrate),np.std(rewardrate),trialnum
#%%

taus = np.logspace(0, 8, 10,base = 2)#list(range(1,30))
#amplitudes = np.arange(0.,1.1,.1)
amplitudes = np.logspace(-2, 0, 10,base = 10)
trialnums = list()
runnum = 10
rewardrates_mean = np.zeros((len(amplitudes),len(taus),len(taus)))
rewardrates_sd = np.zeros((len(amplitudes),len(taus),len(taus)))
trialnum = np.zeros((len(amplitudes),len(taus),len(taus)))
for ampl_i,filter_tau_slow_amplitude in enumerate(amplitudes):
    for tau_1_i,tau_1 in enumerate(taus):
        result_ids = []
        print('ampl:'+str(filter_tau_slow_amplitude)+' tau1:'+str(tau_1))
        for tau_2_i,tau_2 in enumerate(taus):
            #print('taus now:' + str(tau_1) + ' and '+ str(tau_2))
             result_ids.append(runmodel_paralel.remote(runnum, tau_1, tau_2, filter_tau_slow_amplitude))        
        results = ray.get(result_ids)
        for tau_2_i, result in enumerate(results):
            rewardrates_mean[ampl_i,tau_1_i,tau_2_i] = result[0]            
            rewardrates_sd[ampl_i,tau_1_i,tau_2_i] = result[1]            
            trialnum[ampl_i,tau_1_i,tau_2_i] = result[2]            
ray.shutdown()

#%% save data
# =============================================================================
# datatosave['taus'] = taus
# datatosave['amplitudes'] = amplitudes
# datatosave['rewardrate_mean'] = rewardrates_mean
# datatosave['rewardrate_sd'] = rewardrates_sd
# datatosave['trialnum'] = trialnum
# np.save('/home/rozmar/Data/Behavior/Model/Leaky_integrator/test_parameters.npy', datatosave)
# =============================================================================


#%%
#%%
p_reward_L, p_reward_R, n_trials = foraging_model.generate_block_structure(n_trials_base=80,n_trials_sd=10,blocknum = 50, reward_ratio_pairs=np.array([[.4,.05],[.3857,.0643],[.3375,.1125]]))
rewards_random = foraging_model.run_task(p_reward_L,
                                          p_reward_R,
                                          n_trials,
                                          unchosen_rewards_to_keep = 1,
                                          subject = 'random',
                                          min_rewardnum = 10, 
                                          filter_tau_fast = 0,
                                          filter_tau_slow = 60, 
                                          filter_tau_slow_amplitude = 00.0, 
                                          plot = False)
#%
rewards_perfect = foraging_model.run_task(p_reward_L,
                                          p_reward_R,
                                          n_trials,
                                          unchosen_rewards_to_keep = 1,
                                          subject = 'perfect',
                                          min_rewardnum = 10, 
                                          filter_tau_fast = 0,
                                          filter_tau_slow = 60, 
                                          filter_tau_slow_amplitude = 00.0, 
                                          plot = False)
#%%
# =============================================================================
# p_reward_L, p_reward_R, n_trials = foraging_model.generate_block_structure(n_trials_base=150,n_trials_sd=10,blocknum = 10, reward_ratio_pairs=np.array([[.4,.05],[.3857,.0643],[.3375,.1125]]))
# rewards_perfect = foraging_model.run_task(p_reward_L,
#                                           p_reward_R,
#                                           n_trials,
#                                           unchosen_rewards_to_keep = 1,
#                                           subject = 'clever mouse',
#                                           min_rewardnum = 10, 
#                                           filter_tau_fast = 7,
#                                           filter_tau_slow = 100, 
#                                           filter_tau_slow_amplitude = .01, 
#                                           plot = True)
# np.mean(rewards_perfect)
# =============================================================================
#%%
bestvals = np.unravel_index(np.argmax(rewardrates_mean),(len(amplitudes),len(taus),len(taus)))
fig=plt.figure()
ax1=fig.add_axes([0,0,.8,.8])
ax1.plot(taus,rewardrates_mean[bestvals[0],bestvals[1],:])
ax1.plot(taus,np.ones(len(taus))*np.mean(rewards_random))
ax1.plot(taus,np.ones(len(taus))*np.mean(rewards_perfect))
ax1.set_xscale('log')
