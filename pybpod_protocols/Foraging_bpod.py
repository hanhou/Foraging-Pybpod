from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from pybpodapi.bpod.hardware.events import EventName
from pybpodapi.bpod.hardware.output_channels import OutputChannel
from pybpodgui_plugin_waveplayer.module_api import WavePlayerModule
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

# ---- Time settings -----
# For the same dig channel, time durations MUST not fall in others' +/-20% toleratnce zones!
# i.e., for a < b, a < 0.8 b (b > 1.25 a)
event_marker_dur = {# bitcode_channel (BNC1)
                    'bitcode_eachbit': 0.01,   # Couldn't be too small (like 1ms), otherwise the timing error of
                                               # bpod may cause problematic bitcodes (4 trials out of 2000 trials)
                    # bitcode_first = 2 * 0.01 = 0.02
                    'go_cue': 0.001,      # Should be the shortest, otherwise will miss some really fast licks
                    'choice_L': 0.002,    # Relatively time-sensitive, should be shorter
                    'choice_R': 0.003,    # Relatively time-sensitive, should be shorter
                    'choice_M': 0.004,    # Relatively time-sensitive, should be shorter
                    'reward': 0.03,       # Not very time-sensitive
                    'iti_start': 0.04     # Not very time-sensitive
                    }

# Bitcode setting
bitcode_digits = 20
bitcode_first_multiplier = 2  # Bitcode start (or trial start) is signaled by a 2x pulse

# Max duration of camera rolling before/after (conventional) trial start/end (in sec)
camera_max_before_start = 100  # Very large value to ensure we record the video as long as possible
camera_max_after_end = 100

# Minimal camera gap
minimal_camera_gap = 0.2   # 100 ms for video recording overhead (close .avi file and open the next)

# For more precise ITIs, iti_compensation = bpod overhead + bit code length is subtracted from the effective ITI
bpod_load_overhead = 0.05  # measured value
bitcode_length = (bitcode_first_multiplier + 2 * bitcode_digits) * event_marker_dur['bitcode_eachbit']  

# ---- Camera fps ----
camera_face_fps = 300 # face camera, side view and bottom view
camera_trunk_fps = 100  # trunc camera
camera_pulse = 0.001   # Use constant camera pulse width to minimize error due to bpod time resolution (0.1 ms)

# --- photo stim ---
reload_wav_player =  False  # Only reload when neccessary to speed up protocol initialization
laser_power_mapper = [ #   mW , left V,  right V (calibrated @ 5/9/2022, 200um 0.39NA neurophotometrics fiber from Kenta)
                      [0.5, 0.14, 0.08],
                      [1.0, 0.25, 0.15],
                      [2.5, 0.75, 0.55],
                      [5.0, 1.5, 1.1],
                      [7.5, 2.2, 1.65],
                      [10.0, 2.95, 2.25],
                      [13.5, 4.8, 3.7],           
                    ]  # Map power of sine wave (mW) to amplitude (V)
laser_sin_ramp_down_dur = 0.2  # TODO: be flexible
mask_amp = 0.5  # Amplitude for masking flash


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

def gen_sin_wave(sampling_rate, freq, duration, phy=0):
    # Duration in seconds
    t = np.arange(0, duration, 1 / sampling_rate)
    return np.sin(2 * np.pi * freq * t + phy)

def add_bitcode(sma, bitcode_channel):
    # To be consistent with Matlab version
    # Note that this will add 2*(1+bitcode_digits)*bitcode_event_marker_dur['bitcode_eachbit'] to the ITI
    randomID = ''

    for digit in range(bitcode_digits):
        sma.add_state(
            state_name=f'OffState{digit+1}',
            state_timer=event_marker_dur['bitcode_eachbit'],
            state_change_conditions={EventName.Tup: f'OnState{digit+1}'},
            output_actions=[])     # Offstate (to separate two on states)

        bit = np.random.randint(2)   # Random int in [0, 1]
        randomID += str(bit)
        sma.add_state(
            state_name=f'OnState{digit+1}',
            state_timer=event_marker_dur['bitcode_eachbit'],
            state_change_conditions={EventName.Tup: f'OffState{digit+2}'},
            output_actions = [(bitcode_channel, 1)] if bit else [])

    sma.add_state(
        state_name=f'OffState{digit+2}',
        state_timer=0,
        state_change_conditions={EventName.Tup: 'ProtractLickports'},
        output_actions = [])

    return randomID, sma

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
    if dirnow.lower() == 'projects':
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
# ----- Load previous used parameters fsrom json file -----
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
start_with_bias_check = float(variables['block_start_with_bias_check'])
#first_block_to_right = variables['block_first_to_right']
if 'lickport_number' not in variables.keys() or variables['lickport_number'] == 2:
    #%%
    lickportnum = 2
    got_stuck_n = 0

    if variables['difficulty_ratio_pair_num']<1:
        reward_ratio_pairs = [[1,1]]   # For the very beginning of training
    else:
        if 'reward_rate_family' not in variables.keys() or variables['reward_rate_family'] <= 1:
            reward_ratio_pairs=[[.4,.05],[.3857,.0643],[.3375,.1125],[.225,.225]]#,        # 8:1, 6:1, 3:1, 1:1
        elif variables['reward_rate_family'] == 2:     # For photostim
            reward_ratio_pairs=[[8, 1], [1, 1]]   # 8:1, 1:1
        elif variables['reward_rate_family'] == 3:
            reward_ratio_pairs=[[1,0],[.9,.1],[.8,.2],[.7,.3],[.6,.4],[.5,.5]]#,
        elif variables['reward_rate_family'] == 4:       # Starting from 6:1, 3:1, 1:1 (Lau2005 = {6:1, 3:1})
            reward_ratio_pairs=[[6, 1],[3, 1],[1, 1]]
        # reward_ratio_pairs = (np.array(reward_ratio_pairs)/np.sum(reward_ratio_pairs[0])*variables['difficulty_sum_reward_rate']).tolist()
        reward_ratio_pairs = (np.array(reward_ratio_pairs).T/np.sum(reward_ratio_pairs, axis=1)*variables['difficulty_sum_reward_rate']).T.tolist()
        reward_ratio_pairs = reward_ratio_pairs[:variables['difficulty_ratio_pair_num']]

    blocknum = variables['block_number'] # number of blocks
    if start_with_bias_check == 1: # Backward compatibility ('True' previously --> hard bias check)
        p_reward_L = [0,1,0,1] #variables['difficulty_sum_reward_rate']/2# the first block is set to 50% reward rate
        p_reward_R = [1,0,1,0] #variables['difficulty_sum_reward_rate']/2#the first block is set to 50% rewa
        bias_check_blocknum = len(p_reward_L)
    else:

        # -- New logic of block generation --
        # 1. Still use the idea of "bag" for balanced sampling
        # 2. Really ensure always flip side, including across the "bag borders"
        # 3. Ensure no consecutive {1:1} blocks
        p_reward_L = []
        p_reward_R = []
        start_side = np.random.randint(2)  # To avoid the border problem, all bags will have the same start side, which is randomized once for each session

        while len(p_reward_L) < blocknum:
            # Fill in the bag for this round
            this_bag = [[],[]]
            for side in [0,1]:
                this_bag[side] = [pair[::-1 if side else 1] for pair in reward_ratio_pairs if pair[0]!=pair[1]]
                np.random.shuffle(this_bag[side])
            this_bag = np.concatenate(np.swapaxes(this_bag, 0, 1))

            # Handle {1:1}: insert only one {1:1} to the bag; avoid consecutive two {1:1}s across the border
            if any([pair[0] == pair[1] for pair in reward_ratio_pairs]):
                if start_with_bias_check == 0.5 and len(p_reward_L)==0:   # Start session with soft bias check
                    insert_pos = 0
                else:  # Random insert
                    insert_pos = np.random.randint(int(len(p_reward_L)>0 and p_reward_L[-1] == p_reward_R[-1]),  # If the last bag ends with {1:1}, then randint starts from 1
                                               len(this_bag) + 1)
                this_bag = np.insert(this_bag, insert_pos, [variables['difficulty_sum_reward_rate']/2] * 2, axis=0)

            if not highest_probability_port_must_change:
                np.random.shuffle(this_bag)

            # Insert to p_reward
            p_reward_L.extend(np.array(this_bag)[:, start_side])
            p_reward_R.extend(np.array(this_bag)[:, 1-start_side])

        p_reward_L = p_reward_L[:blocknum]
        p_reward_R = p_reward_R[:blocknum]

        # p_reward_L=list()#[.225] #list()#[.225] #list()# the first block is set to 50% reward rate
        # p_reward_R=list()#[.225] #list()#[.225] #list()# list()#the first block is set to 50% reward rate
        # reward_ratio_pairs_bag = list()

        # while len(p_reward_L) < blocknum: # reward rate pairs are chosen randomly
        #     if len(reward_ratio_pairs_bag) == 0:
        #         for pair in reward_ratio_pairs:
        #             reward_ratio_pairs_bag.append(pair)
        #             if pair[0] != pair[1]: # This "if" prevents there from being two {1:1} in the bag! HH20200813
        #                 reward_ratio_pairs_bag.append(pair[::-1])
        #         np.random.shuffle(reward_ratio_pairs_bag)

        #     pair_now = reward_ratio_pairs_bag.pop(0)
        #     if highest_probability_port_must_change and len(p_reward_L) > 0:
        #         if not (p_reward_L[-1] == p_reward_R[-1] or pair_now[0] == pair_now[1]) and np.argmax([p_reward_L[-1],p_reward_R[-1]]) == np.argmax(pair_now):
        #             prob_change_is_fine = False
        #         else:
        #             prob_change_is_fine = True
        #     else:
        #         prob_change_is_fine = True

        #     if (len(p_reward_L) == 0 or p_reward_L[-1] != pair_now[0] or pair_now[0] == pair_now[1]) and prob_change_is_fine or got_stuck_n > 10:
        #         p_reward_L.append(pair_now[0])
        #         p_reward_R.append(pair_now[1])
        #         got_stuck_n = 0
        #     else:
        #         reward_ratio_pairs_bag.append(pair_now)
        #         got_stuck_n += 1

        # If there is {1:1} in the reward family, ensure the session starts with one {1:1} block (as a natural bias check)
        # -- maybe I should use a flag to toggle this ==> if 'start_with_bias_check' == 0.5
        # -- Adding a equal probability block
        # equal_blocks = np.where(np.array(p_reward_L) == np.array(p_reward_R))[0]
        if start_with_bias_check == 0.5 and not any([pair[0] == pair[1] for pair in reward_ratio_pairs]):  # Otherwise soft bias check has been added above
            # Insert {1:1} to the first block
            p_reward_L.insert(0, variables['difficulty_sum_reward_rate'] / 2)
            p_reward_R.insert(0, variables['difficulty_sum_reward_rate'] / 2)

    # plt.plot(p_reward_L, 'o-')

    #%%

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
    if start_with_bias_check == 1:
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

            if (len(p_reward_L) == 0 or pair_now[0] == pair_now[1] or not( p_reward_L[-1] == pair_now[0] and p_reward_R[-1] == pair_now[1] and p_reward_M[-1] == pair_now[2])) and prob_change_is_fine or len(reward_ratio_pairs_bag) == 0 \
                or got_stuck_n > 10:
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


# =================== Define rig-specific vSariables (ports, etc.) =========================
variables = dict()
setupfile = os.path.join(setuppath,'variables.json')
# if os.path.exists(setupfile):
#     with open(setupfile) as json_file:
#         variables = json.load(json_file)
#     print('setup variables loaded from Json file')
# else:

# Always rewrite rig setup file
if setup_name =='Tower-1':
    # for setup: Tower - 1
    variables['GoCue_ch'] = OutputChannel.PWM3
    variables['WaterPort_L_ch_out'] = 7
    variables['WaterPort_L_ch_in'] = EventName.Port7In
    variables['WaterPort_R_ch_out'] = 8
    variables['WaterPort_R_ch_in'] = EventName.Port8In
    variables['WaterPort_M_ch_out'] = 3
    variables['WaterPort_M_ch_in'] = EventName.Port3In
# =============================================================================
#         variables['Choice_cue_L_ch'] = OutputChannel.PWM1
#         variables['Choice_cue_R_ch'] = OutputChannel.PWM2
# =============================================================================
    variables['comport_motor'] = 'COM4'
    variables['retract_motor_signal'] = (OutputChannel.PWM1, 255)
    variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)

    variables['bitcode_channel'] = OutputChannel.BNC1  # e.g., bitcode and go
    variables['trial_indicator_channel'] = OutputChannel.BNC2  # e.g., trial indicator
    variables['camera_face_trig'] = OutputChannel.Wire1    # Face camera trigger
    variables['camera_trunk_trig'] = OutputChannel.Wire2   # Trunk camera trigger

elif setup_name =='Tower-2':
    # for setup: Tower - 2
    variables['GoCue_ch'] = OutputChannel.PWM3
    variables['WaterPort_L_ch_out'] = 7
    variables['WaterPort_L_ch_in'] = EventName.Port7In
    variables['WaterPort_R_ch_out'] = 8
    variables['WaterPort_R_ch_in'] = EventName.Port8In
    variables['WaterPort_M_ch_out'] = 3
    variables['WaterPort_M_ch_in'] = EventName.Port4In
# =============================================================================
#         variables['Choice_cue_L_ch'] = OutputChannel.PWM1
#         variables['Choice_cue_R_ch'] = OutputChannel.PWM2
# =============================================================================
    variables['comport_motor'] = 'COM5'
    variables['retract_motor_signal'] = (OutputChannel.PWM1, 255)
    variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)

    variables['bitcode_channel'] = OutputChannel.BNC1  # e.g., bitcode and go
    variables['trial_indicator_channel'] = OutputChannel.BNC2  # e.g., trial indicator
    variables['camera_face_trig'] = OutputChannel.Wire1    # Face camera trigger
    variables['camera_trunk_trig'] = OutputChannel.Wire2   # Trunk camera trigger

elif setup_name == 'Tower-3':
    # for setup: Tower - 3
    variables['GoCue_ch'] = OutputChannel.PWM3
    variables['WaterPort_L_ch_out'] = 7
    variables['WaterPort_L_ch_in'] = EventName.Port7In
    variables['WaterPort_R_ch_out'] = 8
    variables['WaterPort_R_ch_in'] = EventName.Port8In
    variables['WaterPort_M_ch_out'] = 3
    variables['WaterPort_M_ch_in'] = EventName.Port3In
# =============================================================================
#         variables['Choice_cue_L_ch'] = OutputChannel.PWM1
#         variables['Choice_cue_R_ch'] = OutputChannel.PWM2
# =============================================================================
    variables['comport_motor'] = 'COM9'
    variables['retract_motor_signal'] = (OutputChannel.PWM1, 255)
    variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)

    variables['bitcode_channel'] = OutputChannel.BNC1  # e.g., bitcode and go
    variables['trial_indicator_channel'] = OutputChannel.BNC2  # e.g., trial indicator
    variables['camera_face_trig'] = OutputChannel.Wire1    # Face camera trigger
    variables['camera_trunk_trig'] = OutputChannel.Wire2   # Trunk camera trigger

elif setup_name == 'Tower-4':
    # for setup: Tower - 4
    variables['GoCue_ch'] = OutputChannel.PWM5
    variables['WaterPort_L_ch_out'] = 7
    variables['WaterPort_L_ch_in'] = EventName.Port7In
    variables['WaterPort_R_ch_out'] = 8
    variables['WaterPort_R_ch_in'] = EventName.Port8In
    variables['WaterPort_M_ch_out'] = 3
    variables['WaterPort_M_ch_in'] = EventName.Port3In
    variables['comport_motor'] = 'COM14'
    # variables['retract_motor_signal'] = (OutputChannel.PWM2, 255)
    variables['retract_motor_signal'] = (OutputChannel.SoftCode, 1)
    variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)

    variables['bitcode_channel'] = OutputChannel.BNC1  # e.g., bitcode and go
    variables['trial_indicator_channel'] = OutputChannel.BNC2  # e.g., trial indicator
    variables['camera_face_trig'] = OutputChannel.Wire1    # Face camera trigger
    variables['camera_trunk_trig'] = OutputChannel.Wire2   # Trunk camera trigger

elif setup_name == 'Ephys_Han':
    # for setup: Ephys_Han
    variables['if_recording_rig'] = True
    variables['bitcode_channel'] = OutputChannel.BNC1  # e.g., bitcode and go
    variables['trial_indicator_channel'] = OutputChannel.BNC2  # e.g., trial indicator
    variables['camera_face_trig'] = OutputChannel.Wire1    # Face camera trigger
    variables['camera_trunk_trig'] = OutputChannel.Wire2   # Trunk camera trigger

    variables['GoCue_ch'] = OutputChannel.Serial1    # Use WavePlayer serial command #1 on ephys rig!!
    variables['WaterPort_L_ch_out'] = 1
    variables['WaterPort_L_ch_in'] = EventName.Port1In
    variables['WaterPort_R_ch_out'] = 2
    variables['WaterPort_R_ch_in'] = EventName.Port2In
    variables['WaterPort_M_ch_out'] = 3
    variables['WaterPort_M_ch_in'] = EventName.Port3In
    variables['comport_motor'] = 'COM3'
    variables['retract_motor_signal'] = (OutputChannel.PWM8, 255)  # Use direct trigger to Zaber motor
    # variables['retract_motor_signal'] = (OutputChannel.SoftCode, 1)  # Use softcode (slightly slower)
    variables['protract_motor_signal'] = (OutputChannel.SoftCode, 2)
    
    
if 'if_recording_rig' in variables.keys() and variables['if_recording_rig']:
    if_use_analog_module = True
    if_bit_code = True
    if_camera_trig = True
else:
    if_use_analog_module = False
    if_bit_code = True
    if_camera_trig = True

# ================ Define WavePlayer if this is a recording rig ==============
if if_use_analog_module:

    SER_DEVICE = OutputChannel.Serial1
    SER_PORT = int(SER_DEVICE[-1])
    SAMPLING_RATE  = 50000 # of samples per second
 
    # --- Settings ---
    # https://sites.google.com/site/bpoddocumentation/user-guide/function-reference/bpodwaveplayer
    # https://sites.google.com/site/bpoddocumentation/user-guide/function-reference/waveplayerserialinterface
    wav_player = WavePlayerModule('COM5')   # "Teensy USB" in device manager
    wav_player.set_trigger_mode(wav_player.TRIGGER_MODE_MASTER)   # 'Master' - triggers can force-start a new wave during playback.
    wav_player.set_sampling_period(SAMPLING_RATE)
    wav_player.set_output_range(wav_player.RANGE_VOLTS_MINUS5_5) 
    wav_player.set_bpod_events([1, 1, 1, 1, 1, 1, 1, 1])  # Set event on Ch2 (L laser) and Ch3 (R laser)
    wav_player.set_loop_duration([0, 0, 0, 100 * SAMPLING_RATE, 0, 0, 0, 0])  # loop chan4 (masking flash)
    wav_player.set_loop_mode([0, 0, 0, 1, 0, 0, 0, 0])
        
    WAV_ID_GO_CUE = 0
    WAV_ID_LASER_LEFT_START = 10  # 10, 11, 12, 13, ... for different amps_left (assuming the length of amp_wrapper < 10)
    WAV_ID_LASER_RIGHT_START = 20  # right sinosoid 
    WAV_ID_LASER_RAMP_LEFT_START = 30 # left ramp starts from 30
    WAV_ID_LASER_RAMP_RIGHT_START = 40  # Right ramp starts from 40
    WAV_ID_MASK = 63  # Max = 63


    if reload_wav_player:  # Only reload when neccessary to speed up protocol initialization
        # --- Waveforms ---
        # 1. go cue sound
        go_cue_amp = 2
        go_cue_freq  = 3000  # of cycles per second (Hz) (frequency of the sine waves)
        go_cue_dur = 0.1
        go_cue_waveform = go_cue_amp * gen_sin_wave(SAMPLING_RATE, go_cue_freq, go_cue_dur)
        
        # 2. photostim constant power
        laser_sin_freq = 40  # 40 Hz
        laser_sin_dur = 20  # Actual duration (stop time) is controled by GlobalTimer
        laser_sin_waveform_left = []
        laser_sin_waveform_right = []
        for _, amp_left, amp_right in laser_power_mapper:
            laser_sin_waveform_left.append(amp_left *   (gen_sin_wave(SAMPLING_RATE, laser_sin_freq, laser_sin_dur, phy=np.pi * 3/2) + 1) / 2)
            laser_sin_waveform_right.append(amp_right * (gen_sin_wave(SAMPLING_RATE, laser_sin_freq, laser_sin_dur, phy=np.pi * 3/2) + 1) / 2)
       
        # 3. photostim ramping down 
        laser_sin_ramp_down_waveform_left = []
        laser_sin_ramp_down_waveform_right = []
        for _, amp_left, amp_right in laser_power_mapper:
            laser_sin_ramp_down_waveform_left.append(amp_left * (gen_sin_wave(SAMPLING_RATE, laser_sin_freq, laser_sin_ramp_down_dur, phy=np.pi * 1/2) + 1) / 2)
            laser_sin_ramp_down_waveform_left[-1] *= np.linspace(1, 0, len(laser_sin_ramp_down_waveform_left[-1]))

            laser_sin_ramp_down_waveform_right.append(amp_right * (gen_sin_wave(SAMPLING_RATE, laser_sin_freq, laser_sin_ramp_down_dur, phy=np.pi * 1/2) + 1) / 2)
            laser_sin_ramp_down_waveform_right[-1] *= np.linspace(1, 0, len(laser_sin_ramp_down_waveform_right[-1]))
        
        # 4. masking flash
        # Same frequency as laser. Use loop on this channel, so only one circle is enough
        mask_sin_waveform = mask_amp * (gen_sin_wave(SAMPLING_RATE, laser_sin_freq, 1 / laser_sin_freq, phy=np.pi * 3/2) + 1) / 2
        
        # --- Load waveform to WavePlayer ---
        # Clear all waveforms
        for i in range(64):
            wav_player.load_waveform(i, [0])    

        wav_player.load_waveform(WAV_ID_GO_CUE, go_cue_waveform)
        
        for amp_id, _ in enumerate(laser_power_mapper):  # Add a series of laser waveform with different amps
            wav_player.load_waveform(WAV_ID_LASER_LEFT_START + amp_id, laser_sin_waveform_left[amp_id])
            wav_player.load_waveform(WAV_ID_LASER_RIGHT_START + amp_id, laser_sin_waveform_right[amp_id])

            wav_player.load_waveform(WAV_ID_LASER_RAMP_LEFT_START + amp_id, laser_sin_ramp_down_waveform_left[amp_id])
            wav_player.load_waveform(WAV_ID_LASER_RAMP_RIGHT_START + amp_id, laser_sin_ramp_down_waveform_right[amp_id])
        
        wav_player.load_waveform(WAV_ID_MASK, mask_sin_waveform)
   
    wav_player.disconnect()

    # --- Load serial messages to Bpod ---
    # https://sites.google.com/site/bpoddocumentation/user-guide/function-reference/loadserialmessages
    # https://readthedocs.org/projects/pybpod-api/downloads/pdf/v1.8.1/
    
    # Waveform starts from 0 
    WAV_PORTS_SPEAKER = 1  # [0000 0001], Chan 1 only
    WAV_PORTS_LASER_L = 2  # Chan 2
    WAV_PORTS_LASER_R = 4  # Chan 3
    WAV_PORTS_MASK = 8  # Chan 4
    
    # serial command starts from 1... (max 254)
    SER_CMD_GO_CUE = 1    
    SER_CMD_MASK = 253
    SER_CMD_STOP = 254

    SER_CMD_LASER_L_START = 20
    SER_CMD_LASER_R_START = 30
    SER_CMD_LASER_LR_START = 40
    SER_CMD_LASER_RAMP_L_START = 50
    SER_CMD_LASER_RAMP_R_START = 60
    SER_CMD_LASER_RAMP_LR_START = 70
     
    # Load serial commands
    my_bpod.load_serial_message(SER_PORT, SER_CMD_GO_CUE, [ord('P'), WAV_PORTS_SPEAKER, WAV_ID_GO_CUE])  # go cue
    my_bpod.load_serial_message(SER_PORT, SER_CMD_MASK, [ord('P'), WAV_PORTS_MASK, WAV_ID_MASK])  # masking flash
    my_bpod.load_serial_message(SER_PORT, SER_CMD_STOP, [ord('X')])  # stop all waveform
       
    for amp_id, _ in enumerate(laser_power_mapper):
        # To send out different voltages according to the calibration curves of the two laseres, 
        # one serial message should play two different waveform to two wave ports.
        #!!! To let this line work, I changed Line 481 of pybpodapi\bpod\bpod_com_protocol.py
        my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_LR_START + amp_id, 
                                    [ord('P'), WAV_PORTS_LASER_L, WAV_ID_LASER_LEFT_START + amp_id,
                                     ord('P'), WAV_PORTS_LASER_R, WAV_ID_LASER_RIGHT_START + amp_id])
        my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_RAMP_LR_START + amp_id, 
                            [ord('P'), WAV_PORTS_LASER_L, WAV_ID_LASER_RAMP_LEFT_START + amp_id,
                             ord('P'), WAV_PORTS_LASER_R, WAV_ID_LASER_RAMP_RIGHT_START + amp_id])
        
        my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_L_START + amp_id, 
                                    [ord('P'), WAV_PORTS_LASER_L, WAV_ID_LASER_LEFT_START + amp_id])
        my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_RAMP_L_START + amp_id, 
                            [ord('P'), WAV_PORTS_LASER_L, WAV_ID_LASER_RAMP_LEFT_START + amp_id])
       
        my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_R_START + amp_id, 
                                    [ord('P'), WAV_PORTS_LASER_R, WAV_ID_LASER_RIGHT_START + amp_id])
        my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_RAMP_R_START + amp_id, 
                            [ord('P'), WAV_PORTS_LASER_R, WAV_ID_LASER_RAMP_RIGHT_START + amp_id])
    
    # Command shorthand for state machine
    goCue_command = (SER_DEVICE, SER_CMD_GO_CUE)    # Use Wav ePlayer serial command #SER_CMD_GO_CUE on ephys rig!! 
else:
    goCue_command = (variables['GoCue_ch'], 255)  # Set PWM5 to 100% duty cycle (always on), which triggers the wav trigger board




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
variables.update(variables_setup)   # `variables` now includes both subject and setup parameters
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
randomseedvalue = int(time.time())  # datetime.now().timetuple().tm_yday
np.random.seed(randomseedvalue)
random_values_L = np.random.uniform(0.,1.,2000).tolist()
random_values_R = np.random.uniform(0.,1.,2000).tolist()
random_values_M = np.random.uniform(0.,1.,2000).tolist()
print('Random seed:', str(randomseedvalue))

# ===============  Session start ====================

bpod_stopped = False

# Initialization for manual block switch
if 'change_to_go_next_block' not in variables.keys():
    variables['change_to_go_next_block'] = 0  # Which never changes (backward compatibility)
change_to_go_next_block_previous = variables['change_to_go_next_block']

# Retract the lickport to standby position
# and wait for some time until session starts
retract_protract_motor(variables_subject['motor_retractedposition'])  
triali_in_session = 0

# For randomized photostim
laser_number_of_trials_no_stim_before = 0  # Number of trials before this trial that don't have photostim
laser_baited = 0  # Whether laser has been assigned previously but not delivered because 
                  # laser_number_of_trials_no_stim_before < min_non_stim_before 

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

        print('-----------------------------')

        # Update variables if variables changed in json file DURING RUNNING (from behavior_online_analysis GUI)
        # Note: those who control block structure will not take effect unless rerunning the protocol!!! (eg: reward probs)
        with open(subjectfile) as json_file:
            try:
                variables_subject_new = json.load(json_file)
            except:
                print('Loading variables_subject_new failed... Will try again on next trial')  # Just in case file write is unfinished.
                pass

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
            laser_baited = 0  # Reset baited laser trials (even other parameters are changed...)
        
        # Manual override to go to the next block immediately if variables['change_to_go_next_block'] has changed from 0 to 1
        if change_to_go_next_block_previous == 0 and variables['change_to_go_next_block'] == 1:
            change_to_go_next_block_previous = variables['change_to_go_next_block']
            print('Go to next block NOW (manual override)!')
            break  # Go to the next block NOW
        change_to_go_next_block_previous = variables['change_to_go_next_block']

        triali += 1  # First trial number = 0;
                     # By incrementing triali here, the trial number will include ignored trials.
        triali_in_session += 1
        
        # Generate NEW reward for each port based on the predetermined random sequences
        reward_L = random_values_L.pop(0) < p_L #np.random.uniform(0.,1.) < p_L
        reward_R = random_values_R.pop(0) < p_R # np.random.uniform(0.,1.) < p_R
        reward_M = random_values_M.pop(0) < p_M # np.random.uniform(0.,1.) < p_R

        # Generate ITI for this trial
        iti_this = np.random.exponential(variables['iti'],1) + variables['iti_min'] + ignore_trial_num_in_a_row*variables['increase_ITI_on_ignore_trials']*variables['iti']
        #iti_this = 0
        if iti_this > variables['iti_max']:
            iti_this = variables['iti_max']
        
        # Generate delay period for this trial
        delay_this =  np.random.exponential(variables['delay'],1)+variables['delay_min']# np.random.normal(variables['delay'],variables['delay_rate'])
        if delay_this > variables['delay_max']:
            delay_this = variables['delay_max']

        # If bias check: at the begining of the session, force the mouse to navigate all the lickports in sequence (two rounds)
        if start_with_bias_check == 1 and blocki < bias_check_blocknum:
            trialnum_now = 1  # Override block length = 1
            auto_train_min_rewarded_trial_num = bias_check_auto_train_min_rewarded_trial_num  # At least get XX reward (XX = 1);
                                                                                              # Make sure the animal indeed chooses each port sequentially during bias check
            reward_L_accumulated = False  # We don't need baiting during bias check
            reward_R_accumulated = False
            reward_M_accumulated = False
            # Regular timing
            iti_this = 2
            delay_this = 1
        # (Else: If no bias check or bias check has been done --> Normal trial begins)

        # --------- New way of handling ITI ------
        # Compensate for bpod overhead and bitcode length
        iti_this -= bpod_load_overhead + bitcode_length

        # (obsoleted!) Then split iti_this into half, one before START and the other after END
        # (obsoleted!) This is to ensure the "camera blackout" has the least effect
        # iti_before = iti_previous / 2  # For a historical reason, ITI before a trial is defined by the ITI generated from the last trial
        # iti_after = iti_this / 2

        # iti_before_video_on = min(iti_before - minimal_camera_gap/2, camera_max_before_start)
        # iti_before_video_off = iti_before - iti_before_video_on
                
        # iti_after_video_on = min(iti_after - minimal_camera_gap/2, camera_max_after_end)
        # iti_after_video_off = iti_after - iti_after_video_on

        # (latest!) Now I decide to move the blackout period to the END of the last trial, for two reasons:
        # (1) this maximizes the duration of uninterrupted video recording when aligned to either ITI_start or next_trial_start 
        # (2) easier to handle photostimulation
        # but I still leave the "iti_before" and "iti_after" implementation here for a kind of flexibility
        iti_video_on_duration = min(iti_this - (minimal_camera_gap - bpod_load_overhead), camera_max_before_start)  # Also move the minimal_camera_gap to ITI before
        iti_video_off_duration = iti_this - iti_video_on_duration  
                
        # ============= StateMachine ===========
        sma = StateMachine(my_bpod)
        print('Blocknumber:', blocki + 1)
        print('Trialnumber:', triali + 1)
        print('Trialnumber in session:', triali_in_session)

        if if_camera_trig:
        	# Use global timer to trigger cameras
        	# https://pybpod.readthedocs.io/projects/pybpod-api/en/v1.8.1/pybpodapi/state_machine/state_machine.html?highlight=global_timers#module-pybpodapi.state_machine.global_timers

            # Global timer #1 (1): 300 Hz face cameras
            sma.set_global_timer(timer_id=1, 
                                 timer_duration=camera_pulse, 
                                 on_set_delay=0, 
                                 channel=variables['camera_face_trig'],
                                 on_message=1,
                                 off_message=1,
                                 loop_mode=1,
                                 send_events=0,
                                 loop_intervals=1/camera_face_fps - camera_pulse,
                                 )
            
            # Global timer #2 (2): 100 Hz body camera
            sma.set_global_timer(timer_id=2,
                                 timer_duration=camera_pulse,
                                 on_set_delay=0,
                                 channel=variables['camera_trunk_trig'],
                                 on_message=1,
                                 off_message=1,
                                 loop_mode=1,
                                 send_events=0,
                                 loop_intervals=1/camera_trunk_fps - camera_pulse,
                                 )

        if if_bit_code:
            # Global timer #3 (4): bpod trial indicator
            sma.set_global_timer(timer_id=3,
                                 timer_duration=777,  # Infinity
                                 on_set_delay=0,
                                 channel=variables['trial_indicator_channel'],
                                 on_message=1,
                                 off_message=1,
                                 loop_mode=0,
                                 send_events=0,
                                 )

        laser_this_trial = False  # By default

        if if_use_analog_module:
            # -- Prepare photostim --
            laser_power = variables_subject['laser_power'] if 'laser_power' in variables_subject.keys() else 0

            # Assign laser to this trial
            if laser_power > 0 and variables['laser_duration']:  # As a master switch
                laser_random = np.random.uniform(0, 1) < variables_subject['laser_random_ratio']
                laser_baited += laser_random  # laser trials could be accumulated to ensure the overall ratio
                print('laser baited = ', laser_baited)
                if laser_baited > 0 and laser_number_of_trials_no_stim_before >= variables_subject['laser_min_non_stim_before']:
                    laser_this_trial = True
                    laser_baited -= 1
                
                                        
            if not laser_this_trial:
                laser_number_of_trials_no_stim_before += 1
            else:  # Do it
                laser_number_of_trials_no_stim_before = 0
                amp_id =  [id for id, (pow, _, _) in enumerate(laser_power_mapper) if pow == laser_power][0]
                laser_side = variables_subject['laser_side'] if 'laser_side' in variables_subject.keys() else 2  # Default bilateral

                print('laser power (mW, V):', laser_power_mapper[amp_id])
                print('laser side (0:L, 1:R, 2:LR):', laser_side)
                # print( min(variables['laser_early_ITI_dur'],
                #                              iti_after - variables['laser_early_ITI_offset'] + 2 
                #                              ) - laser_sin_ramp_down_dur, iti_before, iti_after)
                
                # -- Handle temporal laser alignment --
                # New logic (05/15/2022)
                # see https://alleninstitute.sharepoint.com/:p:/s/NeuralDynamics/ESNj88mJ8v5IoAAUYGpuDyEBsHLNQbFJbreWGf75jqpa9A?e=PWRCcH&nav=eyJzSWQiOjI1NywiY0lkIjozMjA4NzYxMjB9 
                # variables_subject['laser_align_to'] = {'After ITI START', 'Before GO CUE', 'After GO CUE'}
                
                iti_to_go_cue = iti_this + bitcode_length + delay_this  # both iti_this and delay_this don't include bitcode length
                
                if variables_subject['laser_align_to'] == 'After ITI START':   # Left-aligned to ITI start, ramping down before Go Cue
                    laser_timer_duration = min(variables['laser_duration'], iti_to_go_cue - variables['laser_offset']) - laser_sin_ramp_down_dur
                    laser_timer_offset = variables['laser_offset']
                elif variables_subject['laser_align_to'] == 'Before GO CUE':   # Right-aligned to Go Cue, start no earlier than last ITI start
                    laser_timer_duration = min(variables['laser_duration'], iti_to_go_cue - variables['laser_offset']) - laser_sin_ramp_down_dur
                    laser_timer_offset = iti_to_go_cue - laser_timer_duration - laser_sin_ramp_down_dur - variables['laser_offset']
                elif variables_subject['laser_align_to'] == 'After GO CUE':  # Left-aligned to Go Cue, hard stop at the next ITI start
                    laser_timer_duration = variables['laser_duration'] - laser_sin_ramp_down_dur   # If this is longer than actual Go Cue to the next ITI start (which is controlled by the mouse), the laser will be terminated by next ITI start
                    laser_timer_offset = variables['laser_offset']                    

                # Global timer #4 (8): photostimulation (triggered by either ITI start or Go cue)
                sma.set_global_timer(timer_id=4, 
                                    timer_duration=max(laser_timer_duration, 0),
                                    on_set_delay=max(laser_timer_offset, 0),
                                    channel=SER_DEVICE,
                                    on_message=((SER_CMD_LASER_LR_START if laser_side == 2 else
                                                SER_CMD_LASER_L_START if laser_side == 0 else
                                                SER_CMD_LASER_R_START)
                                                + amp_id),   # 40 Hz
                                    off_message=((SER_CMD_LASER_RAMP_LR_START if laser_side == 2 else
                                                 SER_CMD_LASER_RAMP_L_START if laser_side == 0 else
                                                 SER_CMD_LASER_RAMP_R_START)
                                                 + amp_id),  # Ramping down
                                    loop_mode=0, 
                                    send_events=0,
                                    )
                
                # # Global timer #5 (16): photostimulation, early ITI (ITI after the trial)
                # sma.set_global_timer(timer_id=5, 
                #                     timer_duration=early_ITI_duration,
                #                                     # (will be turned off manually at the start of the next trial!!)
                #                     on_set_delay=early_ITI_offset,
                #                     channel=SER_DEVICE,
                #                     on_message=((SER_CMD_LASER_LR_START if laser_side == 2 else
                #                                 SER_CMD_LASER_L_START if laser_side == 0 else
                #                                 SER_CMD_LASER_R_START)
                #                                 + amp_id),
                #                     off_message=((SER_CMD_LASER_RAMP_LR_START if laser_side == 2 else
                #                                  SER_CMD_LASER_RAMP_L_START if laser_side == 0 else
                #                                  SER_CMD_LASER_RAMP_R_START)
                #                                  + amp_id),
                #                     loop_mode=0, 
                #                     send_events=0,
                #                     )
       
        # ------- 0. Start of a trial (bit code if necessary) ---------
        # ---------- Now the trial starts with ITIBefore ----------
        # ITI_before = ITI_before_video_on + ITI_before_video_off
        if if_use_analog_module:
            sma.add_state(
                state_name='StopWavePlayer',
                state_timer=0,
                state_change_conditions={EventName.Tup: 
                                        'ITIBeforeLaserTimerStart' 
                                        if laser_this_trial and variables_subject['laser_align_to'] in ['After ITI START', 'Before GO CUE']
                                        else 'MaskFlashOn'},
                output_actions = [(SER_DEVICE, SER_CMD_STOP)]  # Manually turn off all waveform output from the previous trial                
                )
         
        if laser_this_trial and variables_subject['laser_align_to'] in ['After ITI START', 'Before GO CUE']:
            sma.add_state(
                state_name='ITIBeforeLaserTimerStart',  # I keep the name for backward compatibility
                state_timer=0,
                state_change_conditions={EventName.Tup: 'MaskFlashOn'},
                output_actions = [('GlobalTimerTrig', 8)]  # Start photostim timer (#4)
                )
            
        if if_use_analog_module:
            sma.add_state(
                state_name='MaskFlashOn',  # Always turn on mask flash as soon as bpod starts running
                state_timer=0, 
                state_change_conditions={EventName.Tup: 'ITIBeforeVideoOff'},
                output_actions = [(SER_DEVICE, SER_CMD_MASK)]   # Start masking flash
	            ) 
        
        sma.add_state(
            state_name='ITIBeforeVideoOff',
            state_timer=max(iti_video_off_duration, 0), 
            state_change_conditions={EventName.Tup: 'ITIBeforeVideoOn'},
            output_actions = [('GlobalTimerTrig', 4)] if if_bit_code else []      # Start global timer #3 (trial indicator)
            )    
        
        sma.add_state(
            state_name='ITIBeforeVideoOn',
            state_timer=max(iti_video_on_duration, 0), 
            state_change_conditions={EventName.Tup: 'Start'},
            output_actions = [('GlobalTimerTrig', 3)] if if_camera_trig else []     # Start global timer #1 & #2 (cameras)
																					#!!! To let this line work, I changed Line 241 of pybpodapi\state_machine\state_machine_base.py
            )    

        # Bit code
        if if_bit_code:
            sma.add_state(
                state_name='Start',
                state_timer=event_marker_dur['bitcode_eachbit']*bitcode_first_multiplier,  # Signals the start of bitcode (1.5x width)
                state_change_conditions={EventName.Tup: 'OffState1'},
                output_actions = [(variables['bitcode_channel'], 1),   # Start the onset of bitcode
                                 ]
                )
            randomID, sma = add_bitcode(sma, variables['bitcode_channel'])
            print('TrialBitCode: ', randomID)    # Moved it here to avoid the bug where there is ITI but no bitcode

        else:  # Not bit code. Start = DelayStart
            sma.add_state(
                state_name='Start',
                state_timer=0,
                state_change_conditions={EventName.Tup: 'ProtractLickports'},
                output_actions = [])

        # Protract the lickport *AFTER* bitcode. Otherwise early licks may interrupt the bitcode.
        #!!! be careful of the moving time of the lickport
        # TODO: Use trigger instead of softcode for lickport protraction as well
        if variables['motor_retract_waterport']:
            # Protract lickports (using SoftCode 2)
            # 1. Line 410: my_bpod.softcode_handler_function = my_softcode_handler
            # 2. my_softcode_handler(2) brings the lickports to variables['motor_forwardposition'],
            #    which has been set OUTSIDE the trial loop.
            # 3. my_softcode_handler() only controls the RostroCaudal axis
            # 4. Therefore, any manual adjustment along the LEFT-RIGHT axis will be kept over a session,
            #    whereas the RostroCaudal position will be reset to the original value in every trial.
            sma.add_state(
                state_name = 'ProtractLickports',
                state_timer = 0,
                state_change_conditions={EventName.Tup: 'DelayStart'},
                output_actions=[variables['protract_motor_signal']])  #(Bpod.OutputChannels.SoftCode, 2)
        else:  # Do nothing
            sma.add_state(
                state_name = 'ProtractLickports',
                state_timer = 0,
                state_change_conditions={EventName.Tup: 'DelayStart'},
                output_actions=[variables['protract_motor_signal']])  # Also to protract position (temp workaround)

        # ---- 1. Delay period ----
        if variables['early_lick_punishment'] == 0:
            # If NO early lick punishment: start the go cue after the FIXED delay period
            sma.add_state(
                state_name='DelayStart',
                state_timer=delay_this,
                state_change_conditions={EventName.Tup: 'GoCue'},
                output_actions = [])
        else:
            # If early lick punishment, go to a state called BackToDelayStart
            sma.add_state(
                state_name='DelayStart',
                state_timer=delay_this,
                state_change_conditions={variables['WaterPort_L_ch_in']: 'BackToDelayStart',
                                         variables['WaterPort_R_ch_in']: 'BackToDelayStart',
                                         variables['WaterPort_M_ch_in']: 'BackToDelayStart',
                                         EventName.Tup: 'GoCue'},
                output_actions = [])
            # Define actual punishiment
            if variables['early_lick_punishment'] > 0 or not variables['motor_retract_waterport']:
                # Add timeout (during which more early licks will be ignored), then restart the trial
                sma.add_state(
                	state_name='BackToDelayStart',
                	# state_timer=2,
                    # state_timer=variables['delay'],  # Control timeout by delay itself
                    state_timer = abs(variables['early_lick_punishment']), # As the timeout
                	state_change_conditions={EventName.Tup: 'DelayStart'},
                	output_actions = [])

            elif variables['early_lick_punishment'] < 0:
                # Abort the trial directly (avoid guessing during delay period)
                # -- Should not go to ITI, otherwise the block length etc. could be incorrect ---
                # sma.add_state(
                # 	state_name='BackToDelayStart',
                #     state_timer = 0,
                # 	state_change_conditions={EventName.Tup: 'ITI'},
                # 	output_actions = [])

                # Still go to 'BackToDelayStart', but Retract lickports
                sma.add_state(
                 	state_name='BackToDelayStart',
                    state_timer = abs(variables['early_lick_punishment']),
                 	state_change_conditions={EventName.Tup: 'BackToDelayStartProtract'},
                 	output_actions = [variables['retract_motor_signal']])

                # Protract lickports before DelayStart (but still the same trial, no bit code again)
                sma.add_state(
                	state_name='BackToDelayStartProtract',
                	state_timer=0,
                	state_change_conditions={EventName.Tup: 'DelayStart'},
                	output_actions = [variables['protract_motor_signal']]) #(Bpod.OutputChannels.SoftCode, 1)
            else:   # No early lick punishment
                pass


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

            # Now go_cue duration will always be event_marker_dur['go_cue'],
            # but for rigs that use wav trig board, add another state to ensure success trigger.
            # By doing this, we keep the GoCue bitcode duration the same across all rigs (for Kenta's photometry experiments on training rigs)
            sma.add_state(
            	state_name='GoCue_real',
                state_timer=event_marker_dur['go_cue'],    # Now go_cue duration will always be event_marker_dur['go_cue']
            	state_change_conditions={EventName.Tup: 'AfterGoCue'
                                         if if_use_analog_module else
                                        'GoCue_WavTrigBoard'},
            	output_actions = ([goCue_command, (variables['bitcode_channel'], 1)]  # Go cue command & bitcode
                                  if if_bit_code else
                                  [goCue_command])   # Go cue command only
                               )

            if not if_use_analog_module:
                sma.add_state(
                   	state_name='GoCue_WavTrigBoard',
                    state_timer=0.01,   # WAV trigger board need longer durtion to trigger
                   	state_change_conditions={EventName.Tup: 'AfterGoCue'},
                   	output_actions = [goCue_command])

            sma.add_state(
            	state_name='AfterGoCue',
            	state_timer=variables['response_time'],
            	state_change_conditions={variables['WaterPort_L_ch_in']: 'Choice_L',
                                         variables['WaterPort_R_ch_in']: 'Choice_R',
                                         variables['WaterPort_M_ch_in']: 'Choice_M',
                                         EventName.Tup: 'ITI_retract' if variables['motor_retract_waterport'] else 'ITI'},
            	output_actions = [])   # Reaction time

            # End of autowater's gocue

        else:
            # ------ 2. GoCue (normal) --------
            # Licks detected within the response time --> Choice_X, where X is the first licked port;
            # Otherwise, Tup --> ITI` --> end of this trial

            # Now go_cue duration will always be event_marker_dur['go_cue'],
            # but for rigs that use wav trig board, add another state to ensure success trigger.
            # By doing this, we keep the GoCue bitcode duration the same across all rigs (for Kenta's photometry experiments on training rigs)
            sma.add_state(
            	state_name='GoCue',
                state_timer=event_marker_dur['go_cue'],    # Now go_cue duration will always be event_marker_dur['go_cue']
            	state_change_conditions={EventName.Tup: 
                                          'AfterGoCueLaserTimerStart'
                                          if laser_this_trial and variables_subject['laser_align_to'] in ['After GO CUE']
                                          else 'AfterGoCue'
										  if if_use_analog_module else
                                          'GoCue_WavTrigBoard'},
            	output_actions = ([goCue_command, (variables['bitcode_channel'], 1)] 
                                  if if_bit_code else 
                                  [goCue_command]) 
                               )
            
            if laser_this_trial and variables_subject['laser_align_to'] in ['After GO CUE']:
                sma.add_state(
                    state_name='AfterGoCueLaserTimerStart',  # I keep the name for backward compatibility
                    state_timer=0,
                    state_change_conditions={EventName.Tup: 'AfterGoCue'},
                    output_actions = [('GlobalTimerTrig', 8)]   # Start photostim timer (#4)
                )

            if not if_use_analog_module:
                sma.add_state(
                   	state_name='GoCue_WavTrigBoard',
                    state_timer=0.01,   # WAV trigger board need longer durtion to trigger
                   	state_change_conditions={EventName.Tup: 'AfterGoCue'},
                   	output_actions = [goCue_command])

            sma.add_state(
            	state_name='AfterGoCue',
                state_timer=variables['response_time'],
            	state_change_conditions={variables['WaterPort_L_ch_in']: 'Choice_L_fixation_reward',
                                         variables['WaterPort_R_ch_in']: 'Choice_R_fixation_reward',
                                         variables['WaterPort_M_ch_in']: 'Choice_M_fixation_reward',
                                         EventName.Tup: 'ITI_retract' if variables['motor_retract_waterport'] else 'ITI'},
            	output_actions = [])

            # Give the mouse a small amount of water for successful holding in the delay period
            for lickport in ['L', 'R', 'M']:
                sma.add_state(
                	state_name=f'Choice_{lickport}_fixation_reward',
                    state_timer=variables['fixation_reward'] if 'fixation_reward' in variables.keys() else 0,
                	state_change_conditions={EventName.Tup: f'Choice_{lickport}'},  # Go to the real score
                	output_actions = [('Valve',variables[f'WaterPort_{lickport}_ch_out'])])

        # ----- 3. Reward delivery -----
        # Note that the states 'Choice_X' are shared with the autowater mode.
        # Therefore, in the autowater mode, there will be extra water AFTER the autowater

        # === Test of new lick port retraction logic (HH20200805) ===
        # Retract both lickports when the mouse switches side rather than when the trial is unrewarded.
        # Pseudo code:
        #
        # First lick on X within 'response_time' after [GoCue] --> [Choice_X]; TimeUp --> [ITI]
        # If reward:
        #     [Choice_X] --> [Reward_X]  --> [Consume_reward_X]
        # elif no reward:
        #     [Choice_X] --> [Consume_reward_X] (fake reward)
        #
        # In [Consume_reward_X]:
        #     Lick X --> Go back to [Consume_reward]
        #     Lick any port other than X --> [ITI]
        #     TimeUp 1s --> [ITI]

        sma.add_state(
        	state_name='Choice_L',
        	state_timer=event_marker_dur['choice_L'],  # Send a event marker to BNC1
        	state_change_conditions={EventName.Tup:
                                     'Reward_L'  if reward_L or reward_L_accumulated  # reward_L: reward generated in the current trial
                                                                                      # reward_L_accumulated: reward baited from the last trial
                                     else 'Consume_reward_L'},         # No reward
        	output_actions = [(variables['bitcode_channel'], 1)] if if_bit_code else [])  #(variables['Choice_cue_L_ch'],255)   # Not to confuse the mice with too many sounds.

        sma.add_state(
        	state_name='Choice_R',
        	state_timer=event_marker_dur['choice_R'],  # Send a event marker to BNC1
        	state_change_conditions={EventName.Tup:
                                     'Reward_R'  if reward_R or reward_R_accumulated
                                     else 'Consume_reward_R'},
        	output_actions = [(variables['bitcode_channel'], 1)] if if_bit_code else [])  #(variables['Choice_cue_L_ch'],255)   # Not to confuse the mice with too many sounds.

        sma.add_state(
        	state_name='Choice_M',
        	state_timer=event_marker_dur['choice_M'],  # Send a event marker to BNC1
        	state_change_conditions={EventName.Tup:
                                     'Reward_M'  if reward_M or reward_M_accumulated
                                     else 'Consume_reward_M'},
        	output_actions = [(variables['bitcode_channel'], 1)] if if_bit_code else [])  #(variables['Choice_cue_L_ch'],255)   # Not to confuse the mice with too many sounds.


        for lickport in ('L', 'R', 'M'):
            sma.add_state(
            	state_name=f'Reward_{lickport}',
            	state_timer=variables[f'ValveOpenTime_{lickport}'],
            	state_change_conditions={EventName.Tup: f'EventMarker_reward_{lickport}'},
            	output_actions = [('Valve',variables[f'WaterPort_{lickport}_ch_out'])])
            sma.add_state(
            	state_name=f'EventMarker_reward_{lickport}',
            	state_timer=event_marker_dur['reward'],
            	state_change_conditions={EventName.Tup: f'Consume_reward_{lickport}'},
            	output_actions = [(variables['bitcode_channel'], 1)] if if_bit_code else [])


        # sma.add_state(
        # 	state_name='NO_Reward',
        # 	state_timer=0,
        # 	state_change_conditions={EventName.Tup: 'ITI'},
        # 	output_actions = [])


        # # -- Back to consume_reward --
        # sma.add_state(
        # 	state_name='NO_Reward',
        # 	state_timer=0,
        # 	state_change_conditions={EventName.Tup: 'Consume_reward'},
        # 	output_actions = [])        # End of reward delivery

        # --- 3. Enjoy the water! ---
        # No lickport retraction even in unrewarded trial until:
        # 1. The mouse switches side
        # or 2. No licks for some duration

        # The mice are free to lick, until no lick in 'Reward_consume_time', which is hard-coded to 1s.
        # sma.add_state(
        # 	state_name='Consume_reward',
        # 	state_timer=variables['Reward_consume_time'],  # time needed without lick to go to the next trial
        # 	state_change_conditions={variables['WaterPort_L_ch_in']: 'Consume_reward_return',variables['WaterPort_R_ch_in']: 'Consume_reward_return',variables['WaterPort_M_ch_in']: 'Consume_reward_return',EventName.Tup: 'ITI'},
        # 	output_actions = [])

        # --- Any better way? Can the pbod store some local variables (i.e., the last choice)? ---

        sma.add_state(
        	state_name='Consume_reward_L',
        	state_timer=variables['Reward_consume_time'],  # time needed without lick to go to the next trial
        	state_change_conditions={variables['WaterPort_L_ch_in']: 'Consume_reward_return_L',     # Lick L, continue to consume water at L
                                  # If the mouse switches to other lickports or no lick after variables['WaterPort_L_ch_in'],
                                  # retract both lickports!!!
                                  variables['WaterPort_R_ch_in']: 'Double_dipped_to_R', # if variables['double_dip_retract'] else 'Consume_reward_return_R',
                                  variables['WaterPort_M_ch_in']: 'Double_dipped_to_M', # if variables['double_dip_retract'] else 'Consume_reward_return_M',
                                  EventName.Tup: 'ITI_retract' if variables['motor_retract_waterport'] else 'ITI'},
        	output_actions = [])
        # This dummy state is necessary to return to the Consume_reward_L state!
        # Is there any way to reset the state_timer? Then we don't need this.
        sma.add_state(
        	state_name='Consume_reward_return_L',
        	state_timer=0,
        	state_change_conditions={EventName.Tup: 'Consume_reward_L'},
            output_actions = [])

        sma.add_state(
        	state_name='Consume_reward_R',
        	state_timer=variables['Reward_consume_time'],
        	state_change_conditions={variables['WaterPort_L_ch_in']: 'Double_dipped_to_L', # if variables['double_dip_retract'] else 'Consume_reward_return_L',
                                  variables['WaterPort_R_ch_in']: 'Consume_reward_return_R',
                                  variables['WaterPort_M_ch_in']: 'Double_dipped_to_M', # if variables['double_dip_retract'] else 'Consume_reward_return_M',
                                  EventName.Tup: 'ITI_retract' if variables['motor_retract_waterport'] else 'ITI'},
        	output_actions = [])
        sma.add_state(
        	state_name='Consume_reward_return_R',
        	state_timer=0,
        	state_change_conditions={EventName.Tup: 'Consume_reward_R'},
            output_actions = [])

        sma.add_state(
        	state_name='Consume_reward_M',
        	state_timer=variables['Reward_consume_time'],
        	state_change_conditions={variables['WaterPort_L_ch_in']: 'Double_dipped_to_L', # if variables['double_dip_retract'] else 'Consume_reward_return_L',
                                  variables['WaterPort_R_ch_in']: 'Double_dipped_to_R', # if variables['double_dip_retract'] else 'Consume_reward_return_R',
                                  variables['WaterPort_M_ch_in']: 'Consume_reward_return_M',
                                  EventName.Tup: 'ITI_retract' if variables['motor_retract_waterport'] else 'ITI'},
        	output_actions = [])
        sma.add_state(
        	state_name='Consume_reward_return_M',
        	state_timer=0,
        	state_change_conditions={EventName.Tup: 'Consume_reward_M'},
            output_actions = [])
        
        # Now, if variables['double_dip_retract'] = False, we only detect double dipping but do nothing
        # In this case, there could be more than one double-dippings in one trial
        for side in ['L', 'R', 'M']:
            sma.add_state(
                state_name=f'Double_dipped_to_{side}',
                state_timer=0,
                state_change_conditions={EventName.Tup: 'Double_dipping_retract' if variables['double_dip_retract'] else f'Consume_reward_return_{side}'},
                output_actions = [])

        if variables['double_dip_retract']:
            # This state retracts lickports on double dipping
            sma.add_state(
                state_name='Double_dipping_retract',  # 'Double_dipped'
                state_timer=variables['Reward_consume_time'] * 2,  # Add a timeout here which is 2x no-lick-and-trial-end period (hard-coded for now)
                # If we don't retract on ITI, we should protract after retraction on double-dipping; otherwise, wait to be protracted on the start of next trial
                state_change_conditions={EventName.Tup: 'Double_dipping_protract' 
                                         if not variables['motor_retract_waterport'] 
                                         else 'ITI'},    # Won't retract twice at ITI even variables['motor_retract_waterport']=True
                output_actions = [variables['retract_motor_signal']])
            
            # If retract on double-dipping but not on ITI
            if not variables['motor_retract_waterport']:
                sma.add_state(  
                    state_name='Double_dipping_protract',
                    state_timer=0,
                    state_change_conditions={EventName.Tup: 'ITI'},
                    output_actions = [variables['protract_motor_signal']])  

        # --- 4. ITI_after ----
        if variables['motor_retract_waterport']:
            sma.add_state(
                state_name='ITI_retract',
                state_timer=0.01,  # This is needed for reliable retraction by PWM signal
                state_change_conditions={EventName.Tup: 'ITI'},
                output_actions = [variables['retract_motor_signal']]
                )
            
        # Keep the state 'ITI' here for backward-compatibility. It won't retract lickports, only send ITI bitcode if needed
        sma.add_state(
        	state_name='ITI',
        	state_timer=event_marker_dur['iti_start'],
        	state_change_conditions={EventName.Tup: 'End'},
        	output_actions = [(variables['bitcode_channel'], 1)] if if_bit_code else []
            )
            
        # --- 5. All ITI is now placed in the next bpod trial, before next trial start ---    
        sma.add_state(
            state_name = 'End',
            state_timer = 0,
            state_change_conditions={EventName.Tup: 'exit'},
            output_actions=[('GlobalTimerCancel', 3)] if if_camera_trig else []      # Stop global timer #1 & #2 (cameras)
            )


        my_bpod.send_state_machine(sma)  # Send state machine description to Bpod device

        my_bpod.run_state_machine(sma)  # Run state machine

        # ----------- End of state machine ------------

        # -------- Handle reward baiting, print log messages, etc. ---------
        # Check if the mouse got a reward in this trial
        try:
            trialdata = my_bpod.session.current_trial.export()

            reward_L_consumed = not np.isnan(trialdata['States timestamps']['Reward_L'][0][0])
            reward_R_consumed = not np.isnan(trialdata['States timestamps']['Reward_R'][0][0])
            reward_M_consumed = not np.isnan(trialdata['States timestamps']['Reward_M'][0][0])
            L_chosen = not np.isnan(trialdata['States timestamps']['Choice_L'][0][0])
            R_chosen = not np.isnan(trialdata['States timestamps']['Choice_R'][0][0])
            M_chosen = not np.isnan(trialdata['States timestamps']['Choice_M'][0][0])
        except:
            reward_L_consumed, reward_R_consumed, reward_M_consumed, L_chosen, R_chosen, M_chosen = [None] * 6
            # print('current_trial.export failed')
            bpod_stopped = True    # A correct indication of STOP is pressed
                                   # (bpod_status = my_bpod.run_state_machine(sma) didn't work)

        # Update counters
        if reward_L_consumed or reward_R_consumed or reward_M_consumed:
            rewarded_trial_num += 1
            unrewarded_trial_num_in_a_row = 0
        else:
            unrewarded_trial_num_in_a_row += 1
        if L_chosen or R_chosen or M_chosen:
            ignore_trial_num_in_a_row  = 0
        else:
            print(f'ignored {ignore_trial_num_in_a_row}')
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

        print('Trialtype:', 'free choice')
        print('reward_L_accumulated:',reward_L_accumulated)
        print('reward_R_accumulated:',reward_R_accumulated)
        print('reward_M_accumulated:',reward_M_accumulated)

        # Plot current base reward prob. HH
        print('reward_p_L:', p_L)
        print('reward_p_R:', p_R)
        print('reward_p_M:', p_M)

        # Update the lickport (**protracted**) positions
        variables_motor = read_motor_position(variables['comport_motor'])

        print('LickportMotors:',variables_motor)

        if not(start_with_bias_check == 1 and blocki < bias_check_blocknum):

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
                print('mouse is slowing down!')
                # metadata = dict()
                # metadata['experiment_name'] = experiment_name
                # metadata['setup_name'] = setup_name
                # metadata['subject_name'] = subject_name
                # metadata['experimenter_name'] = experimenter_name
                # metadata['reason'] = '5 ignores in a row .. mouse is slowing down!'
                # notify_experimenter(metadata,os.path.join(rootdir,'Notifications'))
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

        # If STOP button has been pressed, break the remaining trials to avoid "too many ignores"
        if bpod_stopped:  break

    # also break the remaining blocks
    if bpod_stopped:
        print('STOP button pressed!')
        break

    if ignore_trial_num_in_a_row > auto_stop_max_ignored_trials_in_a_row:
        print(f'too many ignores {ignore_trial_num_in_a_row} > {auto_stop_max_ignored_trials_in_a_row}')
        # metadata = dict()
        # metadata['experiment_name'] = experiment_name
        # metadata['setup_name'] = setup_name
        # metadata['subject_name'] = subject_name
        # metadata['experimenter_name'] = experimenter_name
        # metadata['reason'] = '10 ignores in a row - experiment was terminated!'
        # notify_experimenter(metadata,os.path.join(rootdir,'Notifications'))
        break

    # ------ End of this block --------

# ------- End of the whole session -----------
if if_use_analog_module:
    # Turn on any ongoing stimulation (wave player won't stop even if bpod is stopped!!)
    my_bpod.manual_override(Bpod.ChannelTypes.OUTPUT, channel_name='Serial', channel_number=1, value=SER_CMD_STOP)    
    
my_bpod.close()
