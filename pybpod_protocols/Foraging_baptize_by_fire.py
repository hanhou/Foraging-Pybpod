from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from pybpodapi.bpod.hardware.events import EventName
from pybpodapi.bpod.hardware.output_channels import OutputChannel
from pybpodapi.com.messaging.trial import Trial
from datetime import datetime
from itertools import permutations
import zaber.serial as zaber_serial
import time
import json
import numpy as np

import os, sys 

usedummyzaber = False # for testing without motor movement - only for debugging
bias_check_auto_train_min_rewarded_trial_num = 1
highest_probability_port_must_change = True
def notify_experimenter(metadata,path):
    filepath = os.path.join(path,'notifications.json')
    metadata['datetime'] = datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
    if os.path.exists(filepath):
        with open(filepath) as json_file:
            notificationssofar = json.load(json_file)
    else:
        notificationssofar = list()
    notificationssofar.append(metadata)
    with open(filepath, 'w') as outfile:
        json.dump(notificationssofar, outfile)

def splitthepath(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

# soft codes : 1 - retract RC motor; 2 - protract RC motor

def my_softcode_handler(data):
    print(data)
    if data == 1:
        positiontomove = variables['motor_retractedposition']
        print("retracting ZaberMotor")
        retract_protract_motor(positiontomove)
    elif data == 2:
        positiontomove = variables['motor_forwardposition']
        print("protracting Zabermotor")
        retract_protract_motor(positiontomove)
        
def retract_protract_motor(positiontomove):
    if usedummyzaber:
        print('dummy zaber moving')
    else:
        for zabertry_i in range(0,1000): # when the COMport is occupied, it will try again
            try:
                with zaber_serial.BinarySerial(variables['comport_motor']) as ser:
                    moveabs_cmd = zaber_serial.BinaryCommand(1,20,positiontomove)
                    ser.write(moveabs_cmd)
                    break
            except zaber_serial.binaryserial.serial.SerialException:
                print('can''t access Zaber ' + str(zabertry_i))
                time.sleep(.01)
def read_motor_position(comport):
    if usedummyzaber:
        print('dummy zaber reading position')
        variables_motor = {
                	'LickPort_Lateral_pos' : 1,
                	'LickPort_RostroCaudal_pos' : 1,
                    }
        return variables_motor
    else:
        for zabertry_i in range(0,1000): # when the COMport is occupied, it will try again
            try:
                with zaber_serial.BinarySerial(comport) as ser:
                    Forward_Backward_device = zaber_serial.BinaryDevice(ser,1)
                    Left_Right_device = zaber_serial.BinaryDevice(ser,2)
                    for zabertry_i in range(0,1000): # when the COMport is occupied, it will try again
                        try:
                            pos_Forward_Backward = Forward_Backward_device.get_position()
                            break
                        except:
                            print('unexpected zaber reply try again')    
                    
                    for zabertry_i in range(0,1000): # when the COMport is occupied, it will try again
                        try:
                            pos_Left_Right = Left_Right_device.get_position()
                            break
                        except:
                            print('unexpected zaber reply try again')    
                    variables_motor = {
                	'LickPort_Lateral_pos' : pos_Left_Right,
                	'LickPort_RostroCaudal_pos' : pos_Forward_Backward,
                    }
                    return variables_motor                
                    break
            except zaber_serial.binaryserial.serial.SerialException:
                print('can''t access Zaber ' + str(zabertry_i))
                time.sleep(.01)
def set_motor_speed():
    if usedummyzaber:
        print('dummy zaber speed set')
    else:
        for zabertry_i in range(0,1000): # when the COMport is occupied, it will try again
            try:
                with zaber_serial.BinarySerial(variables['comport_motor']) as ser:
                    setspeed_cmd = zaber_serial.BinaryCommand(1,42,1000000)
                    ser.write(setspeed_cmd)
                    setacc_cmd = zaber_serial.BinaryCommand(1,43,1000)
                    ser.write(setacc_cmd)
                    break
            except zaber_serial.binaryserial.serial.SerialException:
                print('can''t access Zaber ' + str(zabertry_i))
                time.sleep(.01)


# ======================================================================================
# Main function starts here
# ====================================================================================== 

# ========= Setting up environment (path, metadata, etc.) ==========
my_bpod = Bpod()
history = my_bpod.session.history
experiment_name = 'not defined' 
setup_name = 'not defined' 
subject_name = 'not defined' 
experimenter_name = 'not defined'
for histnow in history:
    if hasattr(histnow, 'infoname'):
        if histnow.infoname ==  'SUBJECT-NAME':
            subject_name = histnow.infovalue
            subject_name = subject_name[2:subject_name[2:].find("'")+2]
        elif histnow.infoname ==  'CREATOR-NAME':
            experimenter_name = histnow.infovalue
            experimenter_name = experimenter_name[2:experimenter_name[2:].find('"')+2]
        elif histnow.infoname == 'SETUP-NAME':
            setup_name = histnow.infovalue
        elif histnow.infoname ==  'EXPERIMENT-NAME':
            experiment_name = histnow.infovalue

print('setup_name: ',setup_name)
print('experiment_name: ',experiment_name)
print('subject_name: ',subject_name)
path = my_bpod.session._path

pathlist = splitthepath(path)
pathnow = ''
for dirnow in pathlist:
    if dirnow == 'Projects':
        rootdir = pathnow
    if dirnow == 'experiments':
        projectdir = pathnow
        subjectdir = os.path.join(projectdir,'subjects',subject_name)
    if dirnow == 'setups':
        experimentpath = pathnow
    if dirnow == 'sessions':
        setuppath = pathnow
    pathnow = os.path.join(pathnow,dirnow)
    
    
# ================ Define subejct-specific variables ===============
# ----- Load previous used parameters from json file -----
subjectfile = os.path.join(subjectdir,'variables.json')
if os.path.exists(subjectfile):
    with open(subjectfile) as json_file:
        variables = json.load(json_file)
    print('subject variables loaded from Json file')
else:
    variables = { # Delayed
            'ValveOpenTime_L' : .04,
            'ValveOpenTime_R' : .04,
            'ValveOpenTime_M' : .04,
            'Trialnumber_in_block' : 15,
            'Trialnumber_in_block_max' : 50,
            'Trialnumber_in_block_min' : 20,
            'block_start_with_bias_check': False,
            #'block_first_to_right':True,
            'block_number':10,
            'difficulty_sum_reward_rate': 1.,
            'difficulty_ratio_pair_num': 0,
            'delay' : 1., # time needed for mouse not to lick before GO cue
            'delay_min' : .5, # minimum value
            'delay_max': 3.,
            'response_time' : 2., # time for the mouse to lick
            'Reward_consume_time' : 1., # time needed without lick  to go to the next trial
            'iti' : 3., 
            'iti_min' : 1., # minimum ITI
            'iti_max': 10.,
            'increase_ITI_on_ignore_trials':False,
            'motor_retractiondistance' : 60000,
            'motor_retract_waterport' : True,
            'accumulate_reward': True,
            'auto_water': True,
            'auto_water_time_multiplier': 0.75,
            'auto_water_min_unrewarder_trials_in_a_row': 5,
            'auto_water_min_ignored_trials_in_a_row': 3,
            'auto_train_min_rewarded_trial_num': 10,
            'early_lick_punishment': False,
            'reward_rate_family': 1,
            'lickport_number':3.,
    }
    
# ----- Generate reward probabilities for this session ------
start_with_bias_check = variables['block_start_with_bias_check']
#first_block_to_right = variables['block_first_to_right']
if 'lickport_number' not in variables.keys() or variables['lickport_number'] == 2:
    lickportnum = 2
    got_stuck_n = 0
    
    if variables['difficulty_ratio_pair_num']<1:
        reward_ratio_pairs = [[1,1]]   # For the very beginning of training
    else:   
        if 'reward_rate_family' not in variables.keys() or variables['reward_rate_family'] <= 1:
            reward_ratio_pairs=[[.4,.05],[.3857,.0643],[.3375,.1125],[.225,.225]]#,        # 8:1, 6:1, 3:1, 1:1
        elif variables['reward_rate_family'] == 2:
            reward_ratio_pairs=[[8/9,1/9],[6/7,1/7],[3/4,1/4],[2/3,1/3],[.5,.5]]#,        # 8:1, 6:1, 3:1, 2:1, 1:1
        elif variables['reward_rate_family'] == 3:
            reward_ratio_pairs=[[1,0],[.9,.1],[.8,.2],[.7,.3],[.6,.4],[.5,.5]]#,
        elif variables['reward_rate_family'] == 4:       # Starting from 6:1, 3:1, 1:1 (Lau2005 = {6:1, 3:1})
            reward_ratio_pairs=[[6, 1],[3, 1],[1, 1]]
            
        # reward_ratio_pairs = (np.array(reward_ratio_pairs)/np.sum(reward_ratio_pairs[0])*variables['difficulty_sum_reward_rate']).tolist()
        reward_ratio_pairs = (np.array(reward_ratio_pairs).T/np.sum(reward_ratio_pairs, axis=1)*variables['difficulty_sum_reward_rate']).T.tolist()
        reward_ratio_pairs = reward_ratio_pairs[:variables['difficulty_ratio_pair_num']]

    blocknum = variables['block_number'] # number of blocks
    if start_with_bias_check:
        p_reward_L = [0,1,0,1] #variables['difficulty_sum_reward_rate']/2# the first block is set to 50% reward rate 
        p_reward_R = [1,0,1,0] #variables['difficulty_sum_reward_rate']/2#the first block is set to 50% rewa 
        bias_check_blocknum = len(p_reward_L)
    else:
        p_reward_L=list()#[.225] #list()#[.225] #list()# the first block is set to 50% reward rate
        p_reward_R=list()#[.225] #list()#[.225] #list()# list()#the first block is set to 50% reward rate
#%
        reward_ratio_pairs_bag = list()
        
        while len(p_reward_L) < blocknum: # reward rate pairs are chosen randomly
            if len(reward_ratio_pairs_bag) == 0:
                for pair in reward_ratio_pairs:
                    reward_ratio_pairs_bag.append(pair)
                    reward_ratio_pairs_bag.append(pair[::-1])
                np.random.shuffle(reward_ratio_pairs_bag)
                
            pair_now = reward_ratio_pairs_bag.pop(0)
            if highest_probability_port_must_change and len(p_reward_L) > 0:
                if not (p_reward_L[-1] == p_reward_R[-1] or pair_now[0] == pair_now[1]) and np.argmax([p_reward_L[-1],p_reward_R[-1]]) == np.argmax(pair_now):
                    prob_change_is_fine = False
                else:
                    prob_change_is_fine = True
            else:
                prob_change_is_fine = True
                
            if (len(p_reward_L) == 0 or p_reward_L[-1] != pair_now[0] or pair_now[0] == pair_now[1]) and prob_change_is_fine or got_stuck_n > 10:
                p_reward_L.append(pair_now[0])
                p_reward_R.append(pair_now[1])
                got_stuck_n = 0
            else:
                reward_ratio_pairs_bag.append(pair_now)
                got_stuck_n += 1
                
    p_reward_M=list(np.zeros(len(p_reward_L))) # 
else:
    lickportnum = 3
    got_stuck_n = 0
    if variables['difficulty_ratio_pair_num']<1:
        reward_ratio_pairs = [[1.,1.,1.]]
    else:
        if 'reward_rate_family' not in variables.keys() or variables['reward_rate_family'] <= 1:
            reward_ratio_pairs = [[6/10,3/10,1/10],[3/6,2/6,1/6],[1/3,1/3,1/3]]
        else:
            reward_ratio_pairs = [[1.,0.,0.],[6/10,3/10,1/10],[3/6,2/6,1/6],[1/3,1/3,1/3]]
        reward_ratio_pairs = (np.array(reward_ratio_pairs)/np.sum(reward_ratio_pairs[0])*variables['difficulty_sum_reward_rate']).tolist()
        reward_ratio_pairs = reward_ratio_pairs[:variables['difficulty_ratio_pair_num']]
        
    blocknum = variables['block_number'] # number of blocks
    if start_with_bias_check:
        p_reward_L = [0,1,0,0,1,0] #variables['difficulty_sum_reward_rate']/2# the first block is set to 50% reward rate 
        p_reward_R = [1,0,0,1,0,0] #variables['difficulty_sum_reward_rate']/2#the first block is set to 50% rewa 
        p_reward_M = [0,0,1,0,0,1] #variables['difficulty_sum_reward_rate']/2#the first block is set to 50% rewa 
        bias_check_blocknum = len(p_reward_L)   
    else:
        p_reward_L=list()#[.225] #list()#[.225] #list()# the first block is set to 50% reward rate
        p_reward_R=list()#[.225] #list()#[.225] #list()# list()#the first block is set to 50% reward rate
        p_reward_M=list()
    
        reward_ratio_pairs_bag = list()
        while len(p_reward_L) < blocknum: # reward rate pairs are chosen randomly
            if len(reward_ratio_pairs_bag) == 0:
                #%
                for pair in reward_ratio_pairs:
                    reward_ratio_pairs_bag.extend(np.unique(list(permutations(pair)),axis = 0))
                np.random.shuffle(reward_ratio_pairs_bag)
                #%
            pair_now = reward_ratio_pairs_bag.pop(0)
            if highest_probability_port_must_change and len(p_reward_L) > 0:
                if not (p_reward_L[-1] == p_reward_R[-1] == p_reward_M[-1] or pair_now[0] == pair_now[1]) and np.argmax([p_reward_L[-1],p_reward_R[-1],p_reward_M[-1]]) == np.argmax(pair_now):
                    prob_change_is_fine = False
                else:
                    prob_change_is_fine = True
            else:
                prob_change_is_fine = True
                
            if (len(p_reward_L) == 0 or pair_now[0] == pair_now[1] or not( p_reward_L[-1] == pair_now[0] and p_reward_R[-1] == pair_now[1] and p_reward_M[-1] == pair_now[2])) and prob_change_is_fine or len(reward_ratio_pairs_bag) == 0 or got_stuck_n > 10:
                p_reward_L.append(pair_now[0])
                p_reward_R.append(pair_now[1])
                p_reward_M.append(pair_now[2])
                got_stuck_n = 0
            else:
                reward_ratio_pairs_bag.append(pair_now)
                got_stuck_n += 1
#%%
# =============================================================================
#     Periodic blocks
# while len(p_reward_L) < blocknum: # reward rate pairs are chosen randomly
#     i = len(p_reward_L)
#     ratiopairidx=np.random.choice(range(len(reward_ratio_pairs)))
#     reward_ratio_pair=reward_ratio_pairs[ratiopairidx]
#     #np.random.shuffle(reward_ratio_pair)
#     if (i % 2) == first_block_to_right:# i == 1 or reward_ratio_pair[0] != p_reward_L[-1]:
#         p_reward_L.append(reward_ratio_pair[0])
#         p_reward_R.append(reward_ratio_pair[1])
#     else:
#         p_reward_L.append(reward_ratio_pair[1])
#         p_reward_R.append(reward_ratio_pair[0])
#     if variables['difficulty_ratio_pair_num'] > 0 and i > 2 and p_reward_L[-1] == p_reward_L[-2]: # blocks shouldn't be the same
#         del p_reward_L[-1]
#         del p_reward_R[-1]
# 
# =============================================================================
variables['reward_probabilities_R']=p_reward_R
variables['reward_probabilities_L']=p_reward_L
variables['reward_probabilities_M']=p_reward_M
print(variables)
variables_subject = variables.copy()


# =================== Define rig-specific variables (ports, etc.) =========================
variables = dict()
setupfile = os.path.join(setuppath,'variables.json')
if os.path.exists(setupfile):
    with open(setupfile) as json_file:
        variables = json.load(json_file)
    print('setup variables loaded from Json file')
else:
    if setup_name =='Tower-1':
        # for setup: Tower - 1
        variables['GoCue_ch'] = OutputChannel.PWM5
        variables['WaterPort_L_ch_out'] = 1
        variables['WaterPort_L_ch_in'] = EventName.Port1In
        variables['WaterPort_R_ch_out'] = 2
        variables['WaterPort_R_ch_in'] = EventName.Port2In
        variables['WaterPort_M_ch_out'] = 3
        variables['WaterPort_M_ch_in'] = EventName.Port3In
# =============================================================================
#         variables['Choice_cue_L_ch'] = OutputChannel.PWM1
#         variables['Choice_cue_R_ch'] = OutputChannel.PWM2
# =============================================================================
        variables['comport_motor'] = 'COM16'
        variables['retract_motor_signal'] = (OutputChannel.PWM8, 255)
        variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)
    elif setup_name =='Tower-2':
        # for setup: Tower - 2
        variables['GoCue_ch'] = OutputChannel.PWM5
        variables['WaterPort_L_ch_out'] = 1
        variables['WaterPort_L_ch_in'] = EventName.Port1In
        variables['WaterPort_R_ch_out'] = 2
        variables['WaterPort_R_ch_in'] = EventName.Port2In
        variables['WaterPort_M_ch_out'] = 3
        variables['WaterPort_M_ch_in'] = EventName.Port3In
# =============================================================================
#         variables['Choice_cue_L_ch'] = OutputChannel.PWM1
#         variables['Choice_cue_R_ch'] = OutputChannel.PWM2
# =============================================================================
        variables['comport_motor'] = 'COM7'
        variables['retract_motor_signal'] = (OutputChannel.PWM7, 255)
        variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)
    elif setup_name == 'Tower-3':
        # for setup: Tower - 3
        variables['GoCue_ch'] = OutputChannel.PWM5
        variables['WaterPort_L_ch_out'] = 1
        variables['WaterPort_L_ch_in'] = EventName.Port1In
        variables['WaterPort_R_ch_out'] = 2
        variables['WaterPort_R_ch_in'] = EventName.Port2In
        variables['WaterPort_M_ch_out'] = 3
        variables['WaterPort_M_ch_in'] = EventName.Port3In
# =============================================================================
#         variables['Choice_cue_L_ch'] = OutputChannel.PWM1
#         variables['Choice_cue_R_ch'] = OutputChannel.PWM2
# =============================================================================
        variables['comport_motor'] = 'COM7'
        variables['retract_motor_signal'] = (OutputChannel.PWM7, 255)
        variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)
    elif setup_name == 'Voltage-1p-rig':
        # for setup: Tower - 3
        variables['GoCue_ch'] = OutputChannel.PWM5
        variables['WaterPort_L_ch_out'] = 1
        variables['WaterPort_L_ch_in'] = EventName.Port1In
        variables['WaterPort_R_ch_out'] = 2
        variables['WaterPort_R_ch_in'] = EventName.Port2In
        variables['WaterPort_M_ch_out'] = 3
        variables['WaterPort_M_ch_in'] = EventName.Port3In
# =============================================================================
#         variables['Choice_cue_L_ch'] = OutputChannel.PWM1
#         variables['Choice_cue_R_ch'] = OutputChannel.PWM2
# =============================================================================
        variables['comport_motor'] = 'COM5'
        variables['retract_motor_signal'] = (OutputChannel.SoftCode, 1)
        variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)
        
        
variables_setup = variables.copy()

# -------- Define the default **protracted** position as the current motor position -------
variables_motor = read_motor_position(variables['comport_motor'])
if subject_name == 'test_setup':
    retract_protract_motor(0)
    variables_motor['LickPort_RostroCaudal_pos'] = 0
    print('protracting zaber motor to avoid watering the camera below..')
    
variables_subject['motor_forwardposition'] = variables_motor['LickPort_RostroCaudal_pos']
variables_subject['motor_retractedposition'] = variables_motor['LickPort_RostroCaudal_pos'] + variables_subject['motor_retractiondistance']
#generate json files

with open(setupfile, 'w') as outfile:
    json.dump(variables_setup, outfile)
with open(subjectfile, 'w') as outfile:
    json.dump(variables_subject, outfile)
print('json files (re)generated')

my_bpod.softcode_handler_function = my_softcode_handler   # Assign the SoftCode function

variables = variables_subject.copy()
variables.update(variables_setup)
print('Variables:', variables)

#print('subjectname for testing:',my_bpod.session.INFO_SUBJECT_NAME)


# ============== Final preparations ==============
# ----> Start the task
ignore_trial_num_in_a_row = 0
if variables['accumulate_reward']:   # Always get a reward on the first trial
    reward_L_accumulated = True
    reward_R_accumulated = True
    if lickportnum == 3:
        reward_M_accumulated = True
    else:
        reward_M_accumulated = False
else:
    reward_L_accumulated = False
    reward_R_accumulated = False
    reward_M_accumulated = False
 
set_motor_speed() # the motors should move FAST    

# Save the random seed for reproducibility
randomseedvalue = datetime.now().timetuple().tm_yday    
np.random.seed(randomseedvalue)
random_values_L = np.random.uniform(0.,1.,2000).tolist()
random_values_R = np.random.uniform(0.,1.,2000).tolist()
random_values_M = np.random.uniform(0.,1.,2000).tolist()
print('Random seed:', str(randomseedvalue))    

# ===============  Session start ====================
# For each block
for blocki , (p_R , p_L, p_M) in enumerate(zip(variables['reward_probabilities_R'], variables['reward_probabilities_L'],variables['reward_probabilities_M'])):
    
    # Initialization
    rewarded_trial_num = 0
    unrewarded_trial_num_in_a_row = 0
    triali = -1
    
    # Generate run length of this block (not exactly truncated exponential, but has flatter hazard function than scipy.stats.truncexpon)
    trialnum_now = np.random.exponential(variables['Trialnumber_in_block'],1)+variables['Trialnumber_in_block_min']
    if trialnum_now > variables['Trialnumber_in_block_max']:
            trialnum_now = variables['Trialnumber_in_block_max'] 
    auto_train_min_rewarded_trial_num =  variables['auto_train_min_rewarded_trial_num']
    
    # ------ For each trial ------
    # Make sure the subject gets at least `auto_train_min_rewarded_trial_num` rewards
    while triali < trialnum_now - 1 or rewarded_trial_num < auto_train_min_rewarded_trial_num:
        
        # Update variables if variables changed in json file DURING RUNNING (from behavior_online_analysis GUI)
        # Note: those who control block structure will not take effect unless rerunning the protocol!!! (eg: reward probs)
        with open(subjectfile) as json_file:
            variables_subject_new = json.load(json_file)
        with open(setupfile) as json_file:
            variables_setup_new = json.load(json_file)
        if variables_setup_new != variables_setup or variables_subject_new != variables_subject:
            # Update effective `variables` ( = subject + setup)
            variables = variables_subject_new.copy()
            variables.update(variables_setup_new)
            # Cache the old values for future variable updates
            variables_setup = variables_setup_new.copy() 
            variables_subject = variables_subject_new.copy()
            print('Variables updated:',variables)  # Print to csv after each parameter update
            auto_train_min_rewarded_trial_num =  variables['auto_train_min_rewarded_trial_num']
        
        triali += 1  # First trial number = 0; 
                     # By incrementing triali here, the trial number will include ignored trials.
        
        # Generate NEW reward for each port based on the predetermined random sequences
        reward_L = random_values_L.pop(0) < p_L #np.random.uniform(0.,1.) < p_L
        reward_R = random_values_R.pop(0) < p_R # np.random.uniform(0.,1.) < p_R
        reward_M = random_values_M.pop(0) < p_M # np.random.uniform(0.,1.) < p_R
        
        # Generate ITI for this trial 
        iti_now = np.random.exponential(variables['iti'],1) + variables['iti_min'] + ignore_trial_num_in_a_row*variables['increase_ITI_on_ignore_trials']*variables['iti']
        #iti_now = 0
        if iti_now > variables['iti_max']:
            iti_now = variables['iti_max']    
            
        # Generate delay period for this trial 
        baselinetime_now =  np.random.exponential(variables['delay'],1)+variables['delay_min']# np.random.normal(variables['delay'],variables['delay_rate'])  
        if baselinetime_now > variables['delay_max']:
            baselinetime_now = variables['delay_max']
        
        # If bias check: at the begining of the session, force the mouse to navigate all the lickports in sequence (two rounds)    
        if start_with_bias_check and blocki < bias_check_blocknum: 
            trialnum_now = 1  # Override block length = 1
            auto_train_min_rewarded_trial_num = bias_check_auto_train_min_rewarded_trial_num  # At least get XX reward (XX = 1); 
                                                                                              # Make sure the animal indeed chooses each port sequentially during bias check
            reward_L_accumulated = False  # We don't need baiting during bias check
            reward_R_accumulated = False
            reward_M_accumulated = False
            # Regular timing
            iti_now = 2
            baselinetime_now = 1
        # (Else: If no bias check or bias check has been done --> Normal trial begins)
        
        # ------- Start of a trial ---------
        sma = StateMachine(my_bpod)
        
        # ---- 1. Delay period ----
        if variables['early_lick_punishment']:
            # Lick before timeup of the delay timer ('baselinetime_now') --> Reset the delay timer
            sma.add_state(
                state_name='Start',
                state_timer=baselinetime_now,
                state_change_conditions={variables['WaterPort_L_ch_in']: 'BackToBaseline', variables['WaterPort_R_ch_in']: 'BackToBaseline',variables['WaterPort_M_ch_in']: 'BackToBaseline',EventName.Tup: 'GoCue'},
                output_actions = [])
            
            # Add timeout (during which more early licks will be ignored), then restart the trial
            sma.add_state(
            	state_name='BackToBaseline',
            	# state_timer=2,
                state_timer=variables['delay'],  # Control timeout by delay itself
            	state_change_conditions={EventName.Tup: 'Start'},
            	output_actions = [])

        else: # If NO early lick punishment: start the go cue after the FIXED delay period
            sma.add_state(
                state_name='Start',
                state_timer=baselinetime_now,
                state_change_conditions={EventName.Tup: 'GoCue'},
                output_actions = [])

        # autowater comes here!! (for encouragement)
        if variables['auto_water'] and (unrewarded_trial_num_in_a_row >= variables['auto_water_min_unrewarder_trials_in_a_row'] or ignore_trial_num_in_a_row >=variables['auto_water_min_ignored_trials_in_a_row'] ):
            # ------ 2. GoCue (with autowater) --------
            # Note: even in the autowater mode, the water does not always come out automatically in all ports.
            # It happens only if
            # 1. Too many unrewarded or ignored trials in a row (controled by the two thresholds).
            # 2. The reward is indeed baited in the corresponding port.
            
            # During auto_water, the 'GoCue' state does not deliver any sound (not 'GoCue_real', see below)
            sma.add_state(
            	state_name='GoCue',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'Auto_Water_M'},
            	output_actions = [])
            
            # "Auto" means the water automatically comes out WITHOUT LICKING, but it still needs reward to be present.
            if reward_M or reward_M_accumulated:  
                sma.add_state(
                	state_name='Auto_Water_M',
                	state_timer=variables['ValveOpenTime_M']*variables['auto_water_time_multiplier'],
                	state_change_conditions={EventName.Tup: 'Auto_Water_L'},
                	output_actions = [('Valve',variables['WaterPort_M_ch_out'])])
            else:
                sma.add_state(
                	state_name='Auto_Water_M',
                	state_timer=0,
                	state_change_conditions={EventName.Tup: 'Auto_Water_L'},
                	output_actions = [])
                
            if reward_L or reward_L_accumulated:
                sma.add_state(
                	state_name='Auto_Water_L',
                	state_timer=variables['ValveOpenTime_L']*variables['auto_water_time_multiplier'],
                	state_change_conditions={EventName.Tup: 'Auto_Water_R'},
                	output_actions = [('Valve',variables['WaterPort_L_ch_out'])])
            else:
                sma.add_state(
                	state_name='Auto_Water_L',
                	state_timer=0,
                	state_change_conditions={EventName.Tup: 'Auto_Water_R'},
                	output_actions = [])
                
            if reward_R or reward_R_accumulated:
                sma.add_state(
                	state_name='Auto_Water_R',
                	state_timer=variables['ValveOpenTime_R']*variables['auto_water_time_multiplier'],
                	state_change_conditions={EventName.Tup: 'GoCue_real'},
                	output_actions = [('Valve',variables['WaterPort_R_ch_out'])])
            else:
                sma.add_state(
                	state_name='Auto_Water_R',
                	state_timer=0,
                	state_change_conditions={EventName.Tup: 'GoCue_real'},
                	output_actions = [])
                
            # In the autowater mode, it is the 'GoCue_real' that tells the mouse to lick
            sma.add_state(
            	state_name='GoCue_real',
            	state_timer=variables['response_time'],
            	state_change_conditions={variables['WaterPort_L_ch_in']: 'Choice_L', variables['WaterPort_R_ch_in']: 'Choice_R', variables['WaterPort_M_ch_in']: 'Choice_M', EventName.Tup: 'ITI'},
            	output_actions = [(variables['GoCue_ch'],255)])   # PWM5 --> 100% duty cycle (always on)
                                                                  # Q: Why not using DigitalOut?
                                                                  # A: Because PWM is the only 3.3V digital out port (designed to control LED brightness)
                                                                  #    'Valve' is also digital out but it's 12V!
                                                                  # See here: https://sanworks.io/forum/showthread.php?tid=25
            # End of autowater's gocue
            
        else:
            # ------ 2. GoCue (normal) --------
            # Licks detected within the response time --> Choice_X, where X is the first licked port; 
            # Otherwise, Tup --> ITI --> end of this trial 
            sma.add_state(
            	state_name='GoCue',
                state_timer=variables['response_time'],
            	state_change_conditions={variables['WaterPort_L_ch_in']: 'Choice_L', variables['WaterPort_R_ch_in']: 'Choice_R', variables['WaterPort_M_ch_in']: 'Choice_M', EventName.Tup: 'ITI'},
            	output_actions = [(variables['GoCue_ch'],255)])   # Set PWM5 to 100% duty cycle (always on), which triggers the wav trigger board
                                                                  # Make sure that the sd card in the wav-trigger board is set properly 
                                                                  # such that it will be triggered by the ONSET of PWM signal!!
        
        # ----- 3. Reward delivery -----
        # Note that the states 'Choice_X' are shared with the autowater mode. 
        # Therefore, in the autowater mode, there will be extra water AFTER the autowater?
        
        if reward_L or reward_L_accumulated:  # reward_L: reward generated in the current trial
                                              # reward_L_accumulated: reward baited from the last trial
            sma.add_state(
            	state_name='Choice_L',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'Reward_L'},
            	output_actions = [])#(variables['Choice_cue_L_ch'],255)   # Not to confuse the mice with too many sounds.
        else:
            sma.add_state(
            	state_name='Choice_L',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'NO_Reward'},
            	output_actions = []) #(variables['Choice_cue_L_ch'],255)
            
        if reward_R or reward_R_accumulated:
            sma.add_state(
            	state_name='Choice_R',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'Reward_R'},
            	output_actions = [])#(variables['Choice_cue_R_ch'],255)
        else:
            sma.add_state(
            	state_name='Choice_R',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'NO_Reward'},
            	output_actions = [])#(variables['Choice_cue_R_ch'],255)
            
        if reward_M or reward_M_accumulated:
            sma.add_state(
            	state_name='Choice_M',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'Reward_M'},
            	output_actions = [])#(variables['Choice_cue_R_ch'],255)
        else:
            sma.add_state(
            	state_name='Choice_M',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'NO_Reward'},
            	output_actions = [])#(variables['Choice_cue_R_ch'],255)
        
        # Actual reward delivery
        # All the licks during reward delivery are ignored (valve open time is very short anyway).
        sma.add_state(
        	state_name='Reward_L',
        	state_timer=variables['ValveOpenTime_L'],
        	state_change_conditions={EventName.Tup: 'Consume_reward'},
        	output_actions = [('Valve',variables['WaterPort_L_ch_out'])])
        sma.add_state(
        	state_name='Reward_R',
        	state_timer=variables['ValveOpenTime_R'],
        	state_change_conditions={EventName.Tup: 'Consume_reward'},
        	output_actions = [('Valve',variables['WaterPort_R_ch_out'])])
        sma.add_state(
        	state_name='Reward_M',
        	state_timer=variables['ValveOpenTime_M'],
        	state_change_conditions={EventName.Tup: 'Consume_reward'},
        	output_actions = [('Valve',variables['WaterPort_M_ch_out'])])
        
        sma.add_state(
        	state_name='NO_Reward',
        	state_timer=0,
        	state_change_conditions={EventName.Tup: 'ITI'},
        	output_actions = [])
        
        # End of reward delivery
        
        # --- 3. Enjoy the water! ---    
        # The mice are free to lick, until no lick in 'Reward_consume_time', which is hard-coded to 1s.
        sma.add_state(
        	state_name='Consume_reward',
        	state_timer=variables['Reward_consume_time'],  # time needed without lick to go to the next trial
        	state_change_conditions={variables['WaterPort_L_ch_in']: 'Consume_reward_return',variables['WaterPort_R_ch_in']: 'Consume_reward_return',variables['WaterPort_M_ch_in']: 'Consume_reward_return',EventName.Tup: 'ITI'},
        	output_actions = [])
        
        # Is this state redundant? Can we assign a state to its own targeted state,
        # i.e., "variables['WaterPort_L_ch_in']: 'Consume_reward'" in the state 'Consume_reward' ?
        sma.add_state(
        	state_name='Consume_reward_return',
        	state_timer=.1,
        	state_change_conditions={EventName.Tup: 'Consume_reward'},
        	output_actions = [])
        
        # --- 4. ITI ----
        if variables['motor_retract_waterport']:
            # Retract lickports (using PWM7 or 8)
            sma.add_state(
            	state_name='ITI',
            	state_timer=iti_now,
            	state_change_conditions={EventName.Tup: 'End'},
            	output_actions = [variables['retract_motor_signal']]) #(Bpod.OutputChannels.SoftCode, 1)
            
            # Protract lickports (using SoftCode 2)
            # 1. Line 410: my_bpod.softcode_handler_function = my_softcode_handler
            # 2. my_softcode_handler(2) brings the lickports to variables['motor_forwardposition'], 
            #    which has been set OUTSIDE the trial loop.
            # 3. my_softcode_handler() only controls the RostroCaudal axis
            # 4. Therefore, any manual adjustment along the LEFT-RIGHT axis will be kept over a session, 
            #    whereas the RostroCaudal position will be reset to the original value in every trial.         
            sma.add_state(
                state_name = 'End',   # Actually it's more like the start of the next trial
                state_timer = 0,
                state_change_conditions={EventName.Tup: 'exit'},
                output_actions=[variables['protract_motor_signal']]) #(Bpod.OutputChannels.SoftCode, 2)
            
        else:    
            sma.add_state(
            	state_name='ITI',
            	state_timer=iti_now,
            	state_change_conditions={EventName.Tup: 'End'},
            	output_actions = [])
            sma.add_state(
                state_name = 'End',
                state_timer = 0,
                state_change_conditions={EventName.Tup: 'exit'},
                output_actions=[])
    
        my_bpod.send_state_machine(sma)  # Send state machine description to Bpod device
    
        my_bpod.run_state_machine(sma)  # Run state machine
        
        # ----------- End of state machine ------------
        
        # -------- Handle reward baiting, print log messages, etc. ---------
        # Check if the mouse got a reward in this trial
        trialdata = my_bpod.session.current_trial.export()
        reward_L_consumed = not np.isnan(trialdata['States timestamps']['Reward_L'][0][0])
        reward_R_consumed = not np.isnan(trialdata['States timestamps']['Reward_R'][0][0])
        reward_M_consumed = not np.isnan(trialdata['States timestamps']['Reward_M'][0][0])
        L_chosen = not np.isnan(trialdata['States timestamps']['Choice_L'][0][0])
        R_chosen = not np.isnan(trialdata['States timestamps']['Choice_R'][0][0])
        M_chosen = not np.isnan(trialdata['States timestamps']['Choice_M'][0][0])
        
        # Update counters
        if reward_L_consumed or reward_R_consumed or reward_M_consumed:
            rewarded_trial_num += 1
            unrewarded_trial_num_in_a_row = 0
        else:
            unrewarded_trial_num_in_a_row += 1  
        if L_chosen or R_chosen or M_chosen:
            ignore_trial_num_in_a_row  = 0
        else:
            ignore_trial_num_in_a_row += 1
        
        # Handle reward baiting
        if variables['accumulate_reward']:
            if reward_L_consumed:
                reward_L_accumulated = False
            elif reward_L and not reward_L_consumed:
                reward_L_accumulated = True
                
            if reward_R_consumed:
                reward_R_accumulated = False
            elif reward_R and not reward_R_consumed:
                reward_R_accumulated = True
            
            if reward_M_consumed:
                reward_M_accumulated = False
            elif reward_M and not reward_M_consumed:
                reward_M_accumulated = True
        
        print('Blocknumber:', blocki + 1)
        print('Trialnumber:', triali + 1)
        print('Trialtype:', 'free choice')
        print('reward_L_accumulated:',reward_L_accumulated)
        print('reward_R_accumulated:',reward_R_accumulated)
        print('reward_M_accumulated:',reward_M_accumulated)
        
        # Update the lickport (**protracted**) positions
        variables_motor = read_motor_position(variables['comport_motor'])
        
        print('LickportMotors:',variables_motor)
        
        if not(start_with_bias_check and blocki < bias_check_blocknum): 
            
            # If too many ignores, abort the whole session.
            
            if 'auto_stop_max_ignored_trials_in_a_row' in variables.keys(): # A new variable added. HH
                auto_stop_max_ignored_trials_in_a_row = variables['auto_stop_max_ignored_trials_in_a_row']
            else:
                auto_stop_max_ignored_trials_in_a_row = 10  # Backward compatibility
            
            if ignore_trial_num_in_a_row > auto_stop_max_ignored_trials_in_a_row:
                break
# =============================================================================
#             elif ignore_trial_num_in_a_row == 3:
#                 print('too many ignores')
#                 metadata = dict()
#                 metadata['experiment_name'] = experiment_name
#                 metadata['setup_name'] = setup_name
#                 metadata['subject_name'] = subject_name
#                 metadata['experimenter_name'] = experimenter_name        
#                 metadata['reason'] = '3 ignores in a row .. mouse is getting nervous?'
#                 notify_experimenter(metadata,os.path.join(rootdir,'Notifications'))
# =============================================================================
            elif ignore_trial_num_in_a_row == auto_stop_max_ignored_trials_in_a_row / 2:
                print('too many ignores')
                metadata = dict()
                metadata['experiment_name'] = experiment_name
                metadata['setup_name'] = setup_name
                metadata['subject_name'] = subject_name
                metadata['experimenter_name'] = experimenter_name        
                metadata['reason'] = '5 ignores in a row .. mouse is slowing down!'
                notify_experimenter(metadata,os.path.join(rootdir,'Notifications'))
# =============================================================================
#             if unrewarded_trial_num_in_a_row == 10:
#                 print('lot of wrong choices')
#                 metadata = dict()
#                 metadata['experiment_name'] = experiment_name
#                 metadata['setup_name'] = setup_name
#                 metadata['subject_name'] = subject_name
#                 metadata['experimenter_name'] = experimenter_name        
#                 metadata['reason'] = '10 unrewarded trials in a row .. mouse is not paying attention?'
#                 notify_experimenter(metadata,os.path.join(rootdir,'Notifications'))
# =============================================================================

        # ------- End of this trial -------
        
    if ignore_trial_num_in_a_row > auto_stop_max_ignored_trials_in_a_row:
        print('too many ignores')
        metadata = dict()
        metadata['experiment_name'] = experiment_name
        metadata['setup_name'] = setup_name
        metadata['subject_name'] = subject_name
        metadata['experimenter_name'] = experimenter_name        
        metadata['reason'] = '10 ignores in a row - experiment was terminated!'
        notify_experimenter(metadata,os.path.join(rootdir,'Notifications'))
        break
    
    # ------ End of this block --------

# ------- End of the whole session -----------
    
my_bpod.close()

