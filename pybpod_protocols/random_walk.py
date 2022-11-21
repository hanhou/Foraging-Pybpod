import numpy as np
import matplotlib.pyplot as plt
import matplotlib
# matplotlib.use('Qt5Agg')

#  np.random.seed(56)

class RandomWalkReward:
    '''
    Generate reward schedule with random walk

    (see Miller et al. 2021, https://www.biorxiv.org/content/10.1101/461129v3.full.pdf)
    '''

    def __init__(self,
                 p_min=0, p_max=1, sigma=0.15,
                 ) -> None:
        
        self.__dict__.update(locals())
        self.p_min, self.p_max, self.sigma = p_min, p_max, sigma
                   
        self.trial_rwd_prob = {'L':[], 'R': []}  # Rwd prob per trial
        self.choice_history = []

        self.hold_this_block = False
        self.first_trial()
    
    def first_trial(self): 
        self.trial_now = 0
        for side in ['L', 'R']:
            self.trial_rwd_prob[side].append(np.random.uniform(self.p_min, self.p_max))
            
    def next_trial(self):
        self.trial_now += 1
        for side in ['L', 'R']:
            if not self.hold_this_block:
                p = np.random.normal(self.trial_rwd_prob[side][-1], self.sigma)
                p = min(self.p_max, max(self.p_min, p))
            else:
                p = self.trial_rwd_prob[side][-1]
            self.trial_rwd_prob[side].append(p)

    def add_choice(self, this_choice):
        self.choice_history.append(this_choice)

    def auto_corr(self, data):
        mean = np.mean(data)
        # Variance
        var = np.var(data)
        # Normalized data
        ndata = data - mean
        acorr = np.correlate(ndata, ndata, 'full')[len(ndata)-1:] 
        acorr = acorr / var / len(ndata)
        return acorr

    def plot_reward_schedule(self):
        fig, ax = plt.subplots(2, 2, figsize=[15, 7], sharex='col', gridspec_kw=dict(width_ratios=[4, 1], wspace=0.1))

        for s, col in zip(['L', 'R'], ['r', 'b']):
            ax[0, 0].plot(self.trial_rwd_prob[s], col, marker='.', alpha=0.5, lw=2)
            ax[0, 1].plot(self.auto_corr(self.trial_rwd_prob[s]), col)

        ax[1, 0].plot(np.array(self.trial_rwd_prob['L']) + np.array(self.trial_rwd_prob['R']), label='sum')
        ax[1, 0].plot(np.array(self.trial_rwd_prob['R']) / (np.array(self.trial_rwd_prob['L']) + np.array(self.trial_rwd_prob['R'])), label='R/(L+R)')
        ax[1, 0].legend()

        ax[0, 1].set(title='auto correlation', xlim=[0, 100])
        ax[0, 1].axhline(y=0, c='k', ls='--')

        plt.show()
        

if __name__ == '__main__':
    total_trial = 1000

    reward_schedule = RandomWalkReward(p_min=0.1, p_max=0.9, sigma=0.1) 

    while reward_schedule.trial_now <= total_trial:    
        reward_schedule.next_trial()
        '''
        run protocol here
        '''

    reward_schedule.plot_reward_schedule()
    
    pass
    # %%
