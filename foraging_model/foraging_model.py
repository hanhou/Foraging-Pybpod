import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def moving_average(a, n=3) :
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n


#%%
    
def generate_block_structure(n_trials_base=80,n_trials_sd=10,blocknum = 10, reward_ratio_pairs=[[.4,.05],[.3857,.0643],[.3375,.1125],[.225,.225]]):
    # from Bari-Cohen 2019
    p_reward_L=[sum(reward_ratio_pairs[0])/2] # the first block is set to 50% reward rate
    p_reward_R=[sum(reward_ratio_pairs[0])/2] # the first block is set to 50% reward rate
    for i in range(blocknum): # reward rate pairs are chosen randomly
        ratiopairidx=np.random.choice(range(len(reward_ratio_pairs)))
        reward_ratio_pair=reward_ratio_pairs[ratiopairidx]
        #np.random.shuffle(reward_ratio_pair)
        if i%2 == 0 :
            p_reward_L.append(reward_ratio_pair[0])
            p_reward_R.append(reward_ratio_pair[1])
        else:
            p_reward_L.append(reward_ratio_pair[1])
            p_reward_R.append(reward_ratio_pair[0])
    n_trials = np.round(np.random.normal(0,n_trials_sd,len(p_reward_L)) + n_trials_base).astype(int)# number of trials in each block
    
    return p_reward_L, p_reward_R, n_trials


def run_task(p_reward_L,p_reward_R,n_trials,unchosen_rewards_to_keep = 1,subject = 'clever mouse',min_rewardnum = 20, filter_tau_fast = 7,filter_tau_slow = 20, filter_tau_slow_amplitude = 0,filter_constant = 0,softmax_temperature = np.nan, differential = False,plot = True):
    '''
    p_reward_L, p_reward_R : list of reward probabilities in each block for left and right
    n_trials: number of trials in each block
    unchosen_rewards_to_keep : bating, 0 - no bating, 1 - Bari et al
    subject: 'clever mouse' (decides based on a leaky integrator), 'random' (50-50 chance), 'perfect' (perfect forager)
    min_rewardnum: the subject behaves as a random forager before getting this amount of rewards
    filter_tau_fast, filter_tau_slow: the time constant of the filter when using the 'clever mouse' subject
    filter_tau_slow_amplitude: the relative amplitude of the slow filter relative to the fast filter
    
    '''
    accumulated_rewards_L = 0
    accumulated_rewards_R = 0
    history_choice = np.array([],dtype=int)#1 is right, 0 is left
    history_reward = np.full(0,True,dtype=bool)
    history_rewardrate_constant=np.array([])#1 is right, 0 is left
    history_rewardrate_dynamic=np.array([])#1 is right, 0 is left
    for n_trials_now, p_reward_R_now, p_reward_L_now in zip(n_trials,p_reward_R,p_reward_L):
        for i_trial in range(n_trials_now):
            # assigning reward to lickports
            reward_L = np.random.uniform(0,1) < p_reward_L_now
            reward_R = np.random.uniform(0,1) < p_reward_R_now
            rewardrate_constant=(p_reward_R_now)/(p_reward_R_now+p_reward_L_now)#/2+.5; # current flat reward rate
            history_rewardrate_constant=np.append(history_rewardrate_constant,rewardrate_constant)
            if sum(history_reward == True) < min_rewardnum:
                choice=np.random.choice(['left','right']) # this will be given by the model
                history_rewardrate_dynamic=np.append(history_rewardrate_dynamic,[np.NaN])
            else:
                x=np.arange(len(history_choice)-1,-1,-1)
                yfast=np.exp(-x/filter_tau_fast)+filter_constant
                yslow=np.exp(-x/filter_tau_slow)*filter_tau_slow_amplitude
                y=yfast + yslow
                #y = y/y[-1]+filter_constant
                
                #y = y/sum(y)
                history_reward_local=history_reward*y
                history_choice_local=history_choice
                
                rewardrate_left=np.sum(history_reward_local[history_choice_local==0][-min_rewardnum:])
                rewardrate_right=np.sum(history_reward_local[history_choice_local==1][-min_rewardnum:])
                #print(rewardrate_right+rewardrate_left)
                if rewardrate_right+rewardrate_left == 0:
                    rewardrate_dynamic = .5
                else:
                    rewardrate_dynamic=(rewardrate_right)/(rewardrate_right+rewardrate_left)
                history_rewardrate_dynamic=np.append(history_rewardrate_dynamic,[rewardrate_dynamic])
                if subject == 'win_stay-loose_switch':
                    if history_reward[-1] and history_choice_local[-1] == 0: # there was a reward
                        choice='left'
                    elif history_reward[-1] and history_choice_local[-1] == 1: # there was a reward
                        choice='right'
                    elif history_reward[-1] == False and history_choice_local[-1] == 0: # there was a reward
                        choice='right'
                    elif history_reward[-1] == False and history_choice_local[-1] == 1: # there was a reward
                        choice='left'    
                elif subject == 'win_stay-loose_random':
                    if history_reward[-1] and history_choice_local[-1] == 0: # there was a reward
                        choice='left'
                    elif history_reward[-1] and history_choice_local[-1] == 1: # there was a reward
                        choice='right'
                    else:
                        rewardrate_dynamic = .5                   
                        if np.random.uniform(0,1) < rewardrate_dynamic:
                            choice='right'
                        else:
                            choice='left' 
                else:
                    if subject == 'random':
                        rewardrate_dynamic = .5
                    elif not np.isnan(softmax_temperature):
                        if differential:
                            rewardrate_dynamic = rewardrate_right-rewardrate_left
                            rewardrate_dynamic = 1/(1+np.exp(-softmax_temperature*(rewardrate_dynamic)))
                        else:
                            rewardrate_dynamic = 1/(1+np.exp(-softmax_temperature*(rewardrate_dynamic-.5)))
                    if np.random.uniform(0,1) < rewardrate_dynamic:
                        choice='right'
                    else:
                        choice='left'
                    
                
                if subject == 'perfect': # this one knows the probabilities and the accumulated reward
                    if p_reward_R_now > p_reward_L_now:
                        if accumulated_rewards_R > accumulated_rewards_L: # go for the right
                            choice='right'
                        elif accumulated_rewards_L > accumulated_rewards_R: # go for the left
                            choice='left'
                        else:
                            choice='right'
                    else:
                        if accumulated_rewards_L > accumulated_rewards_R: # go for the left
                            choice='left'
                        elif accumulated_rewards_R > accumulated_rewards_L: # go for the right
                            choice='right'
                        else:
                            choice='left'
            
            
            
            if choice == 'right':
                
                history_choice=np.append(history_choice,[1])
                if reward_R or accumulated_rewards_R > 0:
                    reward = True
                else:
                    reward = False
                accumulated_rewards_R = 0
                if accumulated_rewards_L < unchosen_rewards_to_keep and reward_L:
                    accumulated_rewards_L += 1
            else:
                history_choice=np.append(history_choice,[0])
                if reward_L or accumulated_rewards_L > 0:
                    reward = True
                else:
                    reward = False
                accumulated_rewards_L = 0
                if accumulated_rewards_R < unchosen_rewards_to_keep and reward_R:
                    accumulated_rewards_R += 1
            history_reward=np.append(history_reward,[reward])
    plt.plot(y.T)
    if plot:
        history_choicenum = np.arange(0,len(history_choice))
        fig=plt.figure()
        ax1=fig.add_axes([0,0,1,1])
        ax1.plot(history_choicenum[history_reward==False], history_choice[history_reward==False],'|',color='gray',markersize=15,markeredgewidth=2)
        ax1.plot(history_choicenum[history_reward==True], history_choice[history_reward==True],'k|',color='black',markersize=30,markeredgewidth=2)
        # constant reward rate
        ax1.plot(history_choicenum,history_rewardrate_constant,color='yellow')
        #ax1.plot(history_choicenum,history_rewardrate_constant_actual,color='red')
        #ax1.plot(history_choicenum,history_rewardrate_dynamic,color='green')   
        ax1.plot(moving_average(history_choice,10),color='black')
        ax1.set_yticks([0,1])
        ax1.set_yticklabels(['Left','Right'])
        plt.xlabel('choice #')
        
        ax2=fig.add_axes([1.3,0,1,1])
        ax2.plot(range(-50,0),yfast[-50:],range(-50,0),yslow[-50:],range(-50,0),y[-50:])
        
        plt.xlabel('choice #')
        plt.ylabel('relative value')
        
        
        # calculating actual rewardrates
        block_idx_edges = np.concatenate((np.array([0]),np.cumsum(n_trials[:len(n_trials)])))
        history_rewardrate_constant_actual = np.zeros(len(history_rewardrate_constant))
        p_reward_L_actual =np.zeros(len(p_reward_L))
        p_reward_R_actual =np.zeros(len(p_reward_R))
        p_reward_maximal =np.zeros(len(p_reward_R))
        p_reward_actual =np.zeros(len(p_reward_R))
        
        for blocki, blocknum in enumerate(n_trials):
            idxnow=range(block_idx_edges[blocki],block_idx_edges[blocki+1])
            choices_block = history_choice[idxnow]
            rewards_block = history_reward[idxnow]
            rewardrate_L = np.around(np.mean(rewards_block[choices_block == 0]),4)
            rewardrate_R = np.around(np.mean(rewards_block[choices_block == 1]),4)  
            history_rewardrate_constant_actual[idxnow] = rewardrate_R/(rewardrate_R+rewardrate_L)
            p_reward_L_actual[blocki] = rewardrate_L
            p_reward_R_actual[blocki] = rewardrate_R
            p_reward_maximal[blocki] = np.max([p_reward_L[blocki],p_reward_R[blocki]])
            p_reward_actual[blocki] = np.around(np.mean(rewards_block),4)
            #print(blocki, blocknum,blockidxes,rewardrate_L,rewardrate_R)
        print('expected  L: ',p_reward_L)
        print('actual    L: ',p_reward_L_actual)
        print('expected  R: ',p_reward_R)
        print('actual    R: ',p_reward_R_actual)
        print('maximal R+L: ',p_reward_maximal)
        print('actual  R+L: ',p_reward_actual)
        
        ax3=fig.add_axes([0,-1.3,1,1])
        ax3.plot(history_choicenum,history_rewardrate_constant,color='yellow',label = 'expected relative value')
        ax3.plot(history_choicenum,history_rewardrate_constant_actual,color='red',label = 'actual relative value')
        ax3.set_yticks([0,1])
        ax3.set_yticklabels(['Left','Right'])
        plt.xlabel('choice #')
        plt.legend()
        plt.ylim(0,1)
        
        
        
        windowsize = 20
        minperiod = 5
        pd_reward = pd.DataFrame()
        pd_reward['reward'] = history_reward
        reward_rolling = pd_reward['reward'].rolling(window = windowsize,center = True, min_periods=minperiod).mean()
        
        ax4=fig.add_axes([1.3,-1.3,1,1])
        ax4.plot(reward_rolling)#p_reward_actual
        ax4.plot(np.ones(len(history_reward))*.45,'y--')#p_reward_actual
        plt.xlabel('block #')
        plt.ylabel('actual reward rate')
        
        rewards = np.zeros(len(history_reward))
        p_reward_cum = .355
        rewards[history_reward] = 1/p_reward_cum
        rewards[history_reward==False] = -1/(1-p_reward_cum)
        ax5=fig.add_axes([0,-2.6,1,1])
        ax5.plot(rewards.cumsum())
        
        ax6=fig.add_axes([1.3,-2.6,1,1])
        ax6.hist(reward_rolling,10)
        
        
        np.mean(history_reward)
    return history_reward,history_choice