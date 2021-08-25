# !/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Ephys preparation
1. Give reward occationally
2. Lasers turn on with low power for aiming / calibration
"""
import numpy as np

from pybpodapi.bpod import Bpod
from pybpodapi.state_machine import StateMachine
from pybpodapi.bpod.hardware.events import EventName
from pybpodapi.bpod.hardware.output_channels import OutputChannel
from pybpodgui_plugin_waveplayer.module_api import WavePlayerModule

#############################################################
# Auto reward
water_ports = [1, 2]
valvetime = 0.02
iti = 30   # Reward per iti

# Laser on
laser_dur = 1000  # sec
laser_chans = 6  # ch2 and ch3
laser_sin_freq = 40

# Masking flash on
mask_amp = 2  #
mask_chan = 8  # ch4
############################################################

my_bpod = Bpod()

# Same as Foraging_bpod to avoid time-consuming overload
SER_DEVICE = OutputChannel.Serial1
SER_PORT = int(SER_DEVICE[-1])

WAV_ID_LASER_RAMP_START = 10

# Don't reload waveforms, only change loop mode
SAMPLING_RATE = 50000
wav_player = WavePlayerModule('COM7')   # "Teensy USB" in device manager
wav_player.set_loop_duration([0, laser_dur * SAMPLING_RATE, laser_dur * SAMPLING_RATE, laser_dur * SAMPLING_RATE, 0, 0, 0, 0])
wav_player.set_loop_mode([0, 1, 1, 1, 0, 0, 0, 0])
wav_player.disconnect()

my_bpod.load_serial_message(SER_PORT, 1, [ord('P'), laser_chans, WAV_ID_LASER_RAMP_START + 0])  # Lowest power
my_bpod.load_serial_message(SER_PORT, 2, [ord('P'), mask_chan, 63])  # Mask flash
my_bpod.load_serial_message(SER_PORT, 3, [ord('X')])  # Stop both

# --- Start ---
i = 0

# Manual turn on once; to turn off, set "'X'" in emulator
# !! Manual sending this is not stable (weird output waveform; only can be fixed by reconnect USB)
# my_bpod.manual_override(Bpod.ChannelTypes.OUTPUT, channel_name='Serial', channel_number=1, value=SER_CMD_MASK_ON)    
# my_bpod.manual_override(Bpod.ChannelTypes.OUTPUT, channel_name='Serial', channel_number=1, value=SER_CMD_LASER_ON)    

while True:
    i += 1
    print(f'Trial: {i}, valve: {water_ports[i % len(water_ports)]} ', i)
    
    sma = StateMachine(my_bpod)

    sma.add_state(
        state_name='Open',
        state_timer=valvetime,
        state_change_conditions={EventName.Tup: 'ITI'},
        output_actions = [('Valve', water_ports[i % len(water_ports)])] \
                         + [(SER_DEVICE, 2)] if i == 1 else []  # Only trigger once so that it can be manually turned off by 'X'
        )   # Give reward in turn
    
    sma.add_state(
        state_name='ITI',
        state_timer=iti,
        state_change_conditions={EventName.Tup: 'exit'},
        output_actions = [(SER_DEVICE, 1)] if i == 1 else [])
        
    my_bpod.send_state_machine(sma)  # Send state machine description to Bpod device
    my_bpod.run_state_machine(sma)  # Run state machine

    # If stopped, break
    try:
        my_bpod.session.current_trial.export()
    except:
        break

my_bpod.manual_override(Bpod.ChannelTypes.OUTPUT, channel_name='Serial', channel_number=1, value=3) 
my_bpod.close()



