from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from pybpodapi.bpod.hardware.events import EventName
from pybpodapi.bpod.hardware.output_channels import OutputChannel
from pybpodapi.com.messaging.trial import Trial
from datetime import datetime
import zaber.serial as zaber_serial
import time
import json
import numpy as np

import os, sys 

usedummyzaber = False # for testing without motor movement - only for debugging

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
    
my_bpod = Bpod()
history = my_bpod.session.history
experiment_name = 'not defined' 
setup_name = 'not defined' 
subject_name = 'not defined' 
for histnow in history:
    if hasattr(histnow, 'infoname'):
        if histnow.infoname ==  'SUBJECT-NAME':
            subject_name = histnow.infovalue
            subject_name = subject_name[2:subject_name[2:].find("'")+2]
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
    if dirnow == 'experiments':
        projectdir = pathnow
        subjectdir = os.path.join(projectdir,'subjects',subject_name)
    if dirnow == 'setups':
        experimentpath = pathnow
    if dirnow == 'sessions':
        setuppath = pathnow
    pathnow = os.path.join(pathnow,dirnow)
    
subjectfile = os.path.join(subjectdir,'variables.json')
if os.path.exists(subjectfile):
    with open(subjectfile) as json_file:
        variables = json.load(json_file)
    print('subject variables loaded from Json file')
else:
    variables = { # Delayed
            'ValveOpenTime_L' : .04,
            'ValveOpenTime_R' : .04,
            'Trialnumber_in_block' : 15,
            'Trialnumber_in_block_SD' : 5,
            'Trialnumber_in_block_min' : 10,
            'block_start_with_bias_check': False,
            'block_first_to_right':True,
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
    }
#generate reward probabilities
start_with_bias_check = variables['block_start_with_bias_check']
first_block_to_right = variables['block_first_to_right']
if variables['difficulty_ratio_pair_num']<1:
    reward_ratio_pairs = [[1,1]]
else:   
    if 'reward_rate_family' not in variables.keys() or variables['reward_rate_family'] <= 1:
        reward_ratio_pairs=[[.4,.05],[.3857,.0643],[.3375,.1125],[.225,.225]]#,        
    elif variables['reward_rate_family'] == 2:
        reward_ratio_pairs=[[8/9,1/9],[6/7,1/7],[3/4,1/4],[2/3,1/3],[.5,.5]]#,        
    elif variables['reward_rate_family'] >= 3:
        reward_ratio_pairs=[[1,0],[.9,.1],[.8,.2],[.7,.3],[.6,.4],[.5,.5]]#,
    reward_ratio_pairs = (np.array(reward_ratio_pairs)/np.sum(reward_ratio_pairs[0])*variables['difficulty_sum_reward_rate']).tolist()
    reward_ratio_pairs = reward_ratio_pairs[:variables['difficulty_ratio_pair_num']]
        
#%%         Random order of blocks but still equal
blocknum = variables['block_number'] # number of blocks
if start_with_bias_check:
    if variables['block_first_to_right']:
        p_reward_L = [0,1,0,1] #variables['difficulty_sum_reward_rate']/2# the first block is set to 50% reward rate 
        p_reward_R = [1,0,1,0] #variables['difficulty_sum_reward_rate']/2#the first block is set to 50% rewa 
    else:
        p_reward_L = [1,0,1,0] #variables['difficulty_sum_reward_rate']/2# the first block is set to 50% reward rate 
        p_reward_R = [0,1,0,1] #variables['difficulty_sum_reward_rate']/2#the first block is set to 50% rewa 
    bias_check_blocknum = len(p_reward_L)
    bias_check_auto_train_min_rewarded_trial_num = 2# autotrain
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
        pair_now = reward_ratio_pairs_bag.pop()
        p_reward_L.append(pair_now[0])
        p_reward_R.append(pair_now[1])
  
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
#%%
variables['reward_probabilities_R']=p_reward_R
variables['reward_probabilities_L']=p_reward_L

variables_subject = variables.copy()
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
        variables['Choice_cue_L_ch'] = OutputChannel.PWM1
        variables['Choice_cue_R_ch'] = OutputChannel.PWM2
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
        variables['Choice_cue_L_ch'] = OutputChannel.PWM1
        variables['Choice_cue_R_ch'] = OutputChannel.PWM2
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
        variables['Choice_cue_L_ch'] = OutputChannel.PWM1
        variables['Choice_cue_R_ch'] = OutputChannel.PWM2
        variables['comport_motor'] = 'COM7'
        variables['retract_motor_signal'] = (OutputChannel.PWM7, 255)
        variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)
variables_setup = variables.copy()
variables_motor = read_motor_position(variables['comport_motor'])
variables_subject['motor_forwardposition'] = variables_motor['LickPort_RostroCaudal_pos']
variables_subject['motor_retractedposition'] = variables_motor['LickPort_RostroCaudal_pos'] + variables_subject['motor_retractiondistance']
#generate json files

with open(setupfile, 'w') as outfile:
    json.dump(variables_setup, outfile)
with open(subjectfile, 'w') as outfile:
    json.dump(variables_subject, outfile)
print('json files (re)generated')

my_bpod.softcode_handler_function = my_softcode_handler

variables = variables_subject.copy()
variables.update(variables_setup)
print('Variables:', variables)

#print('subjectname for testing:',my_bpod.session.INFO_SUBJECT_NAME)
# ----> Start the task
ignore_trial_num_in_a_row = 0
if variables['accumulate_reward']:
    reward_L_accumulated = True
    reward_R_accumulated = True
else:
    reward_L_accumulated = False
    reward_R_accumulated = False
 
set_motor_speed() # the motors should move FAST    

randomseedvalue = datetime.now().timetuple().tm_yday
np.random.seed(randomseedvalue)
random_values_L = np.random.uniform(0.,1.,2000).tolist()
random_values_R = np.random.uniform(0.,1.,2000).tolist()
print('Random seed:', str(randomseedvalue))

for blocki , (p_R , p_L) in enumerate(zip(variables['reward_probabilities_R'], variables['reward_probabilities_L'])):
    rewarded_trial_num = 0
    unrewarded_trial_num_in_a_row = 0
    triali = -1
    if start_with_bias_check and blocki < bias_check_blocknum: # for checking bias in the first 4 short blocks
        trialnum_now = 2
        auto_train_min_rewarded_trial_num = bias_check_auto_train_min_rewarded_trial_num
        reward_L_accumulated = False
        reward_R_accumulated = False
    else: # real blocks
        trialnum_now = np.random.normal(variables['Trialnumber_in_block'],variables['Trialnumber_in_block_SD'])
        if trialnum_now < variables['Trialnumber_in_block_min']:
                trialnum_now = variables['Trialnumber_in_block_min'] 
        auto_train_min_rewarded_trial_num =  variables['auto_train_min_rewarded_trial_num']
    while triali < trialnum_now or rewarded_trial_num < auto_train_min_rewarded_trial_num:
        # check if variables changed in json file
        with open(subjectfile) as json_file:
            variables_subject_new = json.load(json_file)
        with open(setupfile) as json_file:
            variables_setup_new = json.load(json_file)
        if variables_setup_new != variables_setup or variables_subject_new != variables_subject:
            variables = variables_subject_new.copy()
            variables.update(variables_setup_new)
            variables_setup = variables_setup_new.copy()
            variables_subject = variables_subject_new.copy()
            print('Variables updated:',variables)
            auto_train_min_rewarded_trial_num =  variables['auto_train_min_rewarded_trial_num']
            if start_with_bias_check and blocki < bias_check_blocknum: # for checking bias in the first 4 short blocks
                auto_train_min_rewarded_trial_num = bias_check_auto_train_min_rewarded_trial_num
                reward_L_accumulated = False
                reward_R_accumulated = False
        
        
        triali += 1
        reward_L = random_values_L.pop(0) < p_L #np.random.uniform(0.,1.) < p_L
        reward_R = random_values_R.pop(0) < p_R # np.random.uniform(0.,1.) < p_R
        iti_now = np.random.exponential(variables['iti'],1) + ignore_trial_num_in_a_row*variables['increase_ITI_on_ignore_trials']*variables['iti']
        #iti_now = 0
        if iti_now < variables['iti_min']:
            iti_now = variables['iti_min']    
        if iti_now > variables['iti_max']:
            iti_now = variables['iti_max']    
        baselinetime_now =  np.random.exponential(variables['delay'],1)# np.random.normal(variables['delay'],variables['delay_rate'])
        if baselinetime_now < variables['delay_min']:
            baselinetime_now = variables['delay_min']   
        if baselinetime_now > variables['delay_max']:
            baselinetime_now = variables['delay_max']
        sma = StateMachine(my_bpod)
        if variables['early_lick_punishment']:
            sma.add_state(
                state_name='Start',
                state_timer=baselinetime_now,
                state_change_conditions={variables['WaterPort_L_ch_in']: 'BackToBaseline', variables['WaterPort_R_ch_in']: 'BackToBaseline',EventName.Tup: 'GoCue'},
                output_actions = [])
        else:
            sma.add_state(
                state_name='Start',
                state_timer=baselinetime_now,
                state_change_conditions={EventName.Tup: 'GoCue'},
                output_actions = [])
        sma.add_state(
        	state_name='BackToBaseline',
        	state_timer=0.001,
        	state_change_conditions={EventName.Tup: 'Start'},
        	output_actions = [])
        # autowater comes here!!
        if variables['auto_water'] and (unrewarded_trial_num_in_a_row >= variables['auto_water_min_unrewarder_trials_in_a_row'] or ignore_trial_num_in_a_row >=variables['auto_water_min_ignored_trials_in_a_row'] ):
            sma.add_state(
            	state_name='GoCue',
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
            sma.add_state(
            	state_name='GoCue_real',
            	state_timer=variables['response_time'],
            	state_change_conditions={variables['WaterPort_L_ch_in']: 'Choice_L', variables['WaterPort_R_ch_in']: 'Choice_R', EventName.Tup: 'ITI'},
            	output_actions = [(variables['GoCue_ch'],255)])
        else:
            sma.add_state(
            	state_name='GoCue',
            	state_timer=variables['response_time'],
            	state_change_conditions={variables['WaterPort_L_ch_in']: 'Choice_L', variables['WaterPort_R_ch_in']: 'Choice_R', EventName.Tup: 'ITI'},
            	output_actions = [(variables['GoCue_ch'],255)])
        if reward_L or reward_L_accumulated:
            sma.add_state(
            	state_name='Choice_L',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'Reward_L'},
            	output_actions = [(variables['Choice_cue_L_ch'],255)])
        else:
            sma.add_state(
            	state_name='Choice_L',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'NO_Reward'},
            	output_actions = [(variables['Choice_cue_L_ch'],255)])
        if reward_R or reward_R_accumulated:
            sma.add_state(
            	state_name='Choice_R',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'Reward_R'},
            	output_actions = [(variables['Choice_cue_R_ch'],255)])
        else:
            sma.add_state(
            	state_name='Choice_R',
            	state_timer=0,
            	state_change_conditions={EventName.Tup: 'NO_Reward'},
            	output_actions = [(variables['Choice_cue_R_ch'],255)])
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
        	state_name='NO_Reward',
        	state_timer=0,
        	state_change_conditions={EventName.Tup: 'ITI'},
        	output_actions = [])
        sma.add_state(
        	state_name='Consume_reward',
        	state_timer=variables['Reward_consume_time'],
        	state_change_conditions={variables['WaterPort_L_ch_in']: 'Consume_reward_return',variables['WaterPort_R_ch_in']: 'Consume_reward_return',EventName.Tup: 'ITI'},
        	output_actions = [])
        sma.add_state(
        	state_name='Consume_reward_return',
        	state_timer=.1,
        	state_change_conditions={EventName.Tup: 'Consume_reward'},
        	output_actions = [])
        if variables['motor_retract_waterport']:
            sma.add_state(
            	state_name='ITI',
            	state_timer=iti_now,
            	state_change_conditions={EventName.Tup: 'End'},
            	output_actions = [variables['retract_motor_signal']]) #(Bpod.OutputChannels.SoftCode, 1)
            sma.add_state(
                state_name = 'End',
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
        
        trialdata = my_bpod.session.current_trial.export()
        reward_L_consumed = not np.isnan(trialdata['States timestamps']['Reward_L'][0][0])
        reward_R_consumed = not np.isnan(trialdata['States timestamps']['Reward_R'][0][0])
        L_chosen = not np.isnan(trialdata['States timestamps']['Choice_L'][0][0])
        R_chosen = not np.isnan(trialdata['States timestamps']['Choice_R'][0][0])
        
        if reward_L_consumed or reward_R_consumed:
            rewarded_trial_num += 1
            unrewarded_trial_num_in_a_row = 0
        else:
            unrewarded_trial_num_in_a_row += 1
            
        if L_chosen or R_chosen:
            ignore_trial_num_in_a_row  = 0
        else:
            ignore_trial_num_in_a_row += 1
            
        if variables['accumulate_reward']:
            if reward_L_consumed:
                reward_L_accumulated = False
            elif reward_L and not reward_L_consumed:
                reward_L_accumulated = True
            if reward_R_consumed:
                reward_R_accumulated = False
            elif reward_R and not reward_R_consumed:
                reward_R_accumulated = True
        
        print('Blocknumber:', blocki + 1)
        print('Trialnumber:', triali + 1)
        print('Trialtype:', 'free choice')
        print('reward_L_accumulated:',reward_L_accumulated)
        print('reward_R_accumulated:',reward_R_accumulated)
        
        variables_motor = read_motor_position(variables['comport_motor'])
        
        print('LickportMotors:',variables_motor)
           
    
    
my_bpod.close()

