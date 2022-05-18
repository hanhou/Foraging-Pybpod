# !/usr/bin/python3
# -*- coding: utf-8 -*-

"""
HH: calibrate each lickport separately
"""

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from pybpodapi.bpod.hardware.events import EventName
from pybpodapi.bpod.hardware.output_channels import OutputChannel

#############################################################
water_ch = 2	

valvetime = 0.035
dropnum = 300
iti = 0.5

if_use_analog_module = 1

if if_use_analog_module:
    SER_DEVICE = OutputChannel.Serial1
    SER_CMD_GO_CUE = 1 
    WAV_PORTS_SPEAKER = 1
    WAV_ID_GO_CUE = 0
    goCue_command = (SER_DEVICE, SER_CMD_GO_CUE)    # Use Wav ePlayer serial command #SER_CMD_GO_CUE on ephys rig!! 
else:
    goCue_command = ( OutputChannel.PWM5, 255)  # Set PWM5 to 100% duty cycle (always on), which triggers the wav trigger board

############################################################

my_bpod = Bpod()
my_bpod.load_serial_message(int(SER_DEVICE[-1]), SER_CMD_GO_CUE, [ord('P'), WAV_PORTS_SPEAKER, WAV_ID_GO_CUE])  # go cue

for i in range(dropnum):  # Main loop
    print('Trial: ', i + 1)
    
    sma = StateMachine(my_bpod)
   
    sma.add_state(
    		state_name='Open',
    		state_timer=valvetime,
    		state_change_conditions={EventName.Tup: 'ITI'},
    		output_actions = [('Valve', water_ch)])
    
    if i == 0 or i == dropnum - 1:  # Sound the start and end
        sma.add_state(
        		state_name='ITI',
        		state_timer=iti,
        		state_change_conditions={EventName.Tup: 'exit'},
        		output_actions = ([goCue_command]))
    else:
        sma.add_state(
        		state_name='ITI',
        		state_timer=iti,
        		state_change_conditions={EventName.Tup: 'exit'},
        		output_actions = [])

    while True:
        try:
            my_bpod.send_state_machine(sma)  # Send state machine description to Bpod device
            my_bpod.run_state_machine(sma)  # Run state machine
            break
        except:
            pass
    
    
my_bpod.close()



