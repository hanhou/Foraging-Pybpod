'''
Generate uncoupled block reward schedule
(by on-line updating)

adapted from Cohen lab's Arduino code (with some bug fixes?)
'''

from re import S
import numpy as np
import matplotlib.pyplot as plt

np.random.seed(56)

def generate_first_block():    
    for side in ['L', 'R']:
        generate_next_block(side)
        
    # Avoid both blocks have the lowest reward prob
    while np.all([x[0] == np.min(rwd_prob_array) for x in block_rwd_prob.values()]):
        block_rwd_prob[np.random.choice(['L', 'R'])][0] = np.random.choice(rwd_prob_array)  # Random change one side to another prob
    
    # Start with block stagger: the lower side makes the first block switch earlier
    smaller_side = min(block_rwd_prob, key=lambda x: block_rwd_prob[x][0])
    block_ends[smaller_side][0] -= block_stagger
    

def generate_next_block(side, check_higher_in_a_row=True, check_both_lowest=True):
    other_side = list({'L', 'R'} - {side})[0]
    random_block_len = np.random.randint(low=block_min, high=block_max + 1)
    
    if block_ind[side] == 0:  # The first block
        block_ends[side].append(random_block_len)
        block_rwd_prob[side].append(np.random.choice(rwd_prob_array))
        
    else:  # Not the first block
        block_ends[side].append(random_block_len + block_ends[side][block_ind[side] - 1])       
        
        # If this side has higher prob for too long, force it to be the lowest
        if check_higher_in_a_row:
            # For each effective block, update number of times each side >= the other side
            this_prev = block_rwd_prob[side][block_ind[side] - 1]
            other_now = block_rwd_prob[other_side][block_ind[other_side]]
            if this_prev > other_now:
                rwd_tally[side] += 1
                rwd_tally[other_side] = 0
            elif this_prev == other_now:
                rwd_tally[side] += 1
                rwd_tally[other_side] += 1
            else:
                rwd_tally[other_side] += 1
                rwd_tally[side] = 0
            
            if rwd_tally[side] > 3:  # Only check higher-in-a-row for this side
                print(f'--- {trial_now}: {side} is higher for {rwd_tally[side]} eff_blocks, force {side} to lowest ---')
                block_rwd_prob[side].append(min(rwd_prob_array))
                rwd_tally[side] = rwd_tally[other_side] = 0            
                force_by_tally[side].append(trial_now)
            else:  # Otherwise, randomly choose one
                block_rwd_prob[side].append(np.random.choice(rwd_prob_array))
        else:                
            block_rwd_prob[side].append(np.random.choice(rwd_prob_array))
        
        # Don't repeat the previous rwd prob 
        # (this will not mess up with the "forced" case since the previous block cannot be the lowest prob in the first place)
        while block_rwd_prob[side][-2] == block_rwd_prob[side][-1]:
            block_rwd_prob[side][-1] = np.random.choice(rwd_prob_array)
            
        # If the other side is already at the lowest prob AND this side just generates the same
        # (either through "forced" case or not), push the previous lowest side to a higher prob
        if check_both_lowest and block_rwd_prob[side][-1] == block_rwd_prob[other_side][-1] == min(rwd_prob_array):
            # Stagger this side
            block_ends[side][-1] -= block_stagger
            
            # Force block switch of the other side
            print(f'--- {trial_now}: both side is the lowest, push {side} to higher ---')
            force_by_both_lowest[side].append(trial_now)
            block_ends[other_side][-1] = trial_now
            block_ind[other_side] += 1
            generate_next_block(other_side, check_higher_in_a_row=False, check_both_lowest=False)  # Just generate new block, no need to do checks
            
rwd_prob_array = [0.1, 0.5, 0.9]
block_min = 20
block_max = 35
block_stagger = int((round(block_max - block_min - 0.5) / 2 + block_min) / 2)
total_trial = 1000

perseve_add = True
perseverative_limit = 4

max_block_tally = 3  # Max number of consecutive blocks in which one side has higher rwd prob than the other
rwd_tally = {'L': 0, 'R': 0}

trial_now = 0  # Index of trial number, starting from 0

block_ends = {'L': [], 'R': []} # Trial number on which each block ends
block_rwd_prob = {'L':[], 'R':[]}  # Reward probability
block_ind = {'L': 0, 'R': 0}  # Index of current block (= len(block_end_at_trial))

trial_rwd_prob = {'L':[], 'R': []}  # Rwd prob per trial

force_by_tally = {'L':[], 'R': []}
force_by_both_lowest = {'L':[], 'R': []}

generate_first_block()

while trial_now <= total_trial:    
    for s in ['L', 'R']:
        trial_rwd_prob[s].append(block_rwd_prob[s][block_ind[s]]) 
        
    '''
    run protocol here
    '''
    
    for s in ['L', 'R']:
        if trial_now == block_ends[s][block_ind[s]]:
            block_ind[s] += 1
            generate_next_block(s, check_higher_in_a_row=True, check_both_lowest=True)
    
    trial_now += 1

fig, ax = plt.subplots(2, 1, figsize=[15, 7], sharex='col')

def annotate_block(ax):
    for s, col in zip(['L', 'R'], ['r', 'b']):
        [ax.axvline(x + (0.1 if s=='R' else 0), 0, 1, color=col, ls='--', lw=0.5) for x in block_ends[s]]
        [ax.plot(x, 1.1, marker='>', color=col) for x in force_by_tally[s]]
        [ax.plot(x, 1.0, marker='v', color=col) for x in force_by_both_lowest[s]]

for s, col in zip(['L', 'R'], ['r', 'b']):
    ax[0].plot(trial_rwd_prob[s], col, marker='.', alpha=0.5, lw=2)
annotate_block(ax[0])

ax[1].plot(np.array(trial_rwd_prob['L']) + np.array(trial_rwd_prob['R']), label='sum')
ax[1].plot(np.array(trial_rwd_prob['R']) / (np.array(trial_rwd_prob['L']) + np.array(trial_rwd_prob['R'])), label='R/(L+R)')
ax[1].legend()
annotate_block(ax[1])
   
pass