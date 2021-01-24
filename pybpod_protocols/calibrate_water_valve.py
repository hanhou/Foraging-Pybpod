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
water_ch = 3

valvetime = 0.1
dropnum = 100
iti = 0.3


sound_ch = OutputChannel.PWM5
############################################################

my_bpod = Bpod()

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
        		output_actions = [(sound_ch, 255)])
    else:
        sma.add_state(
        		state_name='ITI',
        		state_timer=iti,
        		state_change_conditions={EventName.Tup: 'exit'},
        		output_actions = [])
        
    my_bpod.send_state_machine(sma)  # Send state machine description to Bpod device
    my_bpod.run_state_machine(sma)  # Run state machine
    
    
my_bpod.close()



