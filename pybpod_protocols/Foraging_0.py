# !/usr/bin/python3
# -*- coding: utf-8 -*-

"""
A protocol to calibrate the water system. In addition, to contro the lights.
"""

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from pybpodapi.bpod.hardware.events import EventName
from pybpodapi.bpod.hardware.output_channels import OutputChannel
from pybpodapi.com.messaging.trial import Trial
import zaber.serial as zaber_serial
import time

import numpy as np

# =============================================================================
# setup_name = 'Tower-2' #'Tower-3'#'Tower-2' #
# experiment_name = 'Foraging - Bari Cohen'#'Delayed foraging' #'Foraging - Bari Cohen'
# =============================================================================
usedummyzaber = False
my_bpod = Bpod()
history = my_bpod.session.history
experiment_name = 'not defined' 
setup_name = 'not defined' 
subject_name = 'not defined' 
for histnow in history:
    if hasattr(histnow, 'infoname'):
        if histnow.infoname ==  'SUBJECT-NAME':
            subject_name = histnow.infovalue
        elif histnow.infoname == 'SETUP-NAME':
            setup_name = histnow.infovalue
        elif histnow.infoname ==  'EXPERIMENT-NAME':
            experiment_name = histnow.infovalue
print('setup_name: ',setup_name)
print('experiment_name: ',experiment_name)


start_with_fifty_fifty = True
first_block_to_right = True

reward_ratio_pairs=[[.4,.05],[.3857,.0643],[.3375,.1125]]#,[.225,.225]
blocknum = 20 # number of blocks
if start_with_fifty_fifty:
    p_reward_L=[.225] #list()#[.225] #list()# the first block is set to 50% reward rate
    p_reward_R=[.225] #list()#[.225] #list()# list()#the first block is set to 50% rewa
else:
    p_reward_L=list()#[.225] #list()#[.225] #list()# the first block is set to 50% reward rate
    p_reward_R=list()#[.225] #list()#[.225] #list()# list()#the first block is set to 50% reward rate
for i in range(blocknum): # reward rate pairs are chosen randomly
    ratiopairidx=np.random.choice(range(len(reward_ratio_pairs)))
    reward_ratio_pair=reward_ratio_pairs[ratiopairidx]
    #np.random.shuffle(reward_ratio_pair)
    if (i % 2) == first_block_to_right:# i == 1 or reward_ratio_pair[0] != p_reward_L[-1]:
        p_reward_L.append(reward_ratio_pair[0])
        p_reward_R.append(reward_ratio_pair[1])
    else:
        p_reward_L.append(reward_ratio_pair[1])
        p_reward_R.append(reward_ratio_pair[0])

if experiment_name == 'Foraging - Bari-Cohen':
    variables = { # Cohen
            'Trialnumber_in_block' : 50,
            'Trialnumber_in_block_SD' : 10,
            'Trialnumber_in_block_min' : 40,
            'reward_probabilities_R' : p_reward_R,#[.4,.05,.4,.05,.4,.05,.4,.05,.4,.05],#[1,0,1,0,1,0,1,0,1,0,1,0,1,0,1,0],#,[.7,.3,.6,.4,.5],#[.7,.8,.2,.7,.3,.6,.4,.5],#[1,.9,0,.8,0,.7,0], #p_reward_R,#[.7,.6,,]
            'reward_probabilities_L' : p_reward_L,#[.05,.4,.05,.4,.05,.4,.05,.4,.05,.4],#[0,1,0,1,0,1,0,1,0,1,0,1,0,1,0,1],#[.3,.7,.4,.6,.5], #[.7,.2,.8,.3,.7,.4,.6,.5], #[1,0,.9,0,.8,0,.7],#p_reward_L,#[.7,0,.7,0,.6,0,.5], #[.4,.1,,]
            'baseline_time' : 2, # time needed for mouse not to lick before GO cue
            'baseline_time_min' : 1, # minimum value
            'baseline_time_sd' : 0, # randomization parameter 1
            'GoCue_time' : 2, # time for the mouse to lick
            'Reward_consume_time' : 1, # time needed without lick  to go to the next trial
            'iti_base' : 5., 
            'iti_min' : 1., # minimum ITI
            'iti_sd' : 2., # randomization parameter
            'motor_retractiondistance' : 60000,
            'motor_retract_waterport' : True,
            'accumulate_reward': True,
            'auto_water': True,
            'auto_water_time_multiplier': 0.75,
            'auto_water_min_unrewarder_trials_in_a_row': 50,
            'auto_water_min_ignored_trials_in_a_row': 10,
            'auto_train_min_rewarded_trial_num': 30,
            'early_lick_punishment': True,
    }
    reward_L_accumulated = True
    reward_R_accumulated = True
elif experiment_name == 'Delayed foraging':
    variables = { # Delayed
            'Trialnumber_in_block' : 50,
            'Trialnumber_in_block_SD' : 10,
            'Trialnumber_in_block_min' : 40,
            'reward_probabilities_R' : p_reward_R,#[.4,.05,.4,.05,.4,.05,.4,.05,.4,.05],#[1,0,1,0,1,0,1,0,1,0,1,0,1,0],#,[.7,.3,.6,.4,.5],#[.7,.8,.2,.7,.3,.6,.4,.5],#[1,.9,0,.8,0,.7,0], #p_reward_R,#[.7,.6,,]
            'reward_probabilities_L' : p_reward_L,#[.05,.4,.05,.4,.05,.4,.05,.4,.05,.4],#[0,1,0,1,0,1,0,1,0,1,0,1,0,1],#[.3,.7,.4,.6,.5], #[.7,.2,.8,.3,.7,.4,.6,.5], #[1,0,.9,0,.8,0,.7],#p_reward_L,#[.7,0,.7,0,.6,0,.5], #[.4,.1,,]
            'baseline_time' : 1.5, # time needed for mouse not to lick before GO cue
            'baseline_time_min' : 1, # minimum value
            'baseline_time_sd' : 1, # randomization parameter 1
            'GoCue_time' : .5, # time for the mouse to lick
            'Reward_consume_time' : 1, # time needed without lick  to go to the next trial
            'iti_base' : 5., 
            'iti_min' : 1., # minimum ITI
            'iti_sd' : 2., # randomization parameter
            'motor_retractiondistance' : 60000,
            'motor_retract_waterport' : True,
            'accumulate_reward': True,
            'auto_water': True,
            'auto_water_time_multiplier': 0.75,
            'auto_water_min_unrewarder_trials_in_a_row': 100,
            'auto_water_min_ignored_trials_in_a_row': 10,
            'auto_train_min_rewarded_trial_num': 30,
            'early_lick_punishment': True,
    }
    reward_L_accumulated = True
    reward_R_accumulated = True

if setup_name =='Tower-2':
    # for setup: Tower - 2
    variables['ValveOpenTime_L'] = .038
    variables['ValveOpenTime_R'] = .040
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
    variables['ValveOpenTime_L'] = .040# .035#.029#
    variables['ValveOpenTime_R'] = .040#.035#.029#
    variables['GoCue_ch'] = OutputChannel.PWM5
    variables['WaterPort_L_ch_out'] = 1
    variables['WaterPort_L_ch_in'] = EventName.Port1In
    variables['WaterPort_R_ch_out'] = 2
    variables['WaterPort_R_ch_in'] = EventName.Port2In
    variables['Choice_cue_L_ch'] = OutputChannel.PWM1
    variables['Choice_cue_R_ch'] = OutputChannel.PWM2
    variables['comport_motor'] = 'COM12'
    variables['retract_motor_signal'] = (OutputChannel.PWM7, 255)
    variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)

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


variables_motor = read_motor_position(variables['comport_motor'])
variables['motor_forwardposition'] = variables_motor['LickPort_RostroCaudal_pos']
variables['motor_retractedposition'] = variables_motor['LickPort_RostroCaudal_pos'] + variables['motor_retractiondistance']


my_bpod.softcode_handler_function = my_softcode_handler

print('Variables:', variables)

#print('subjectname for testing:',my_bpod.session.INFO_SUBJECT_NAME)
# ----> Start the task
ignore_trial_num_in_a_row = 0
for blocki , (p_R , p_L) in enumerate(zip(variables['reward_probabilities_R'], variables['reward_probabilities_L'])):
    rewarded_trial_num = 0
    unrewarded_trial_num_in_a_row = 0
    
    triali = -1
    #for triali in range(variables['Trialnumber_in_block']):  # Main loop
    trialnum_now = np.random.normal(variables['Trialnumber_in_block'],variables['Trialnumber_in_block_SD'])
    if trialnum_now < variables['Trialnumber_in_block_min']:
            trialnum_now = variables['Trialnumber_in_block_min'] 
    while triali < variables['Trialnumber_in_block'] or rewarded_trial_num < variables['auto_train_min_rewarded_trial_num']:
        triali += 1
        reward_L = np.random.uniform(0.,1.) < p_L
        reward_R = np.random.uniform(0.,1.) < p_R
        iti_now = np.random.normal(variables['iti_base']+ignore_trial_num_in_a_row,variables['iti_sd'])#
        #iti_now = 0
        if iti_now < variables['iti_min']:
            iti_now = variables['iti_min']    
        baselinetime_now = np.random.normal(variables['baseline_time'],variables['baseline_time_sd'])
        if baselinetime_now < variables['baseline_time_min']:
            baselinetime_now = variables['baseline_time_min']   
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
            	state_timer=variables['GoCue_time'],
            	state_change_conditions={variables['WaterPort_L_ch_in']: 'Choice_L', variables['WaterPort_R_ch_in']: 'Choice_R', EventName.Tup: 'ITI'},
            	output_actions = [(variables['GoCue_ch'],255)])
        else:
            sma.add_state(
            	state_name='GoCue',
            	state_timer=variables['GoCue_time'],
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

