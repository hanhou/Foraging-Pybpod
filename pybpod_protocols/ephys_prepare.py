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
laser_amp = 0.05  # 0.04 V is the minimal visible level
laser_dur = 1000  # sec
laser_gap = 1  # sec
laser_chans = 6  # ch2 and ch3
laser_sin_freq = 40

# Masking flash on
mask_amp = 2  #
mask_chan = 8  # ch4
############################################################

my_bpod = Bpod()
SER_DEVICE = OutputChannel.Serial1
SER_PORT = int(SER_DEVICE[-1])
SER_CMD_LASER_ON = 1
SER_CMD_MASK_ON = 253  # Max 254
SER_CMD_ALL_OFF = 254

# --- Load waveform to WavePlayer ---
def gen_sin_wave(sampling_rate, freq, duration, phy=0):
    # Duration in seconds
    t = np.arange(0, duration, 1 / sampling_rate)
    return np.sin(2 * np.pi * freq * t + phy)

SAMPLING_RATE = 10000
wav_player = WavePlayerModule('COM7')   # "Teensy USB" in device manager
wav_player.set_trigger_mode(wav_player.TRIGGER_MODE_MASTER)   # 'Master' - triggers can force-start a new wave during playback.
wav_player.set_sampling_period(SAMPLING_RATE)
wav_player.set_output_range(wav_player.RANGE_VOLTS_MINUS5_5)    
wav_player.set_loop_duration([0, laser_dur * SAMPLING_RATE, laser_dur * SAMPLING_RATE, laser_dur * SAMPLING_RATE, 0, 0, 0, 0])
wav_player.set_loop_mode([0, 1, 1, 1, 0, 0, 0, 0])

# for i in range(64):
#     wav_player.load_waveform(i, [0])    

laser_sin_waveform = laser_amp * (gen_sin_wave(SAMPLING_RATE, laser_sin_freq, 10/laser_sin_freq, phy=np.pi * 3/2) + 1) / 2
laser_sqaure_waveform = [laser_amp]  # Just one sample point is enough

# Note that for the LUXdrive 3021-D of masking flash, the output current is INVERSELY modulated by control voltage...
# http://www.leddynamics.com/wp-content/uploads/2018/11/03021_03023_BuckPuck_v3-1.pdf
masking_flash_waveform = mask_amp * (gen_sin_wave(SAMPLING_RATE, laser_sin_freq, 10/laser_sin_freq, phy=np.pi * 3/2) + 1) / 2

wav_player.load_waveform(1, laser_sin_waveform) 
# wav_player.load_waveform(2, laser_sqaure_waveform) 
wav_player.load_waveform(63, masking_flash_waveform)
wav_player.disconnect()

my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_ON, [ord('P'), laser_chans, 1])  # Turn on both
my_bpod.load_serial_message(SER_PORT, SER_CMD_MASK_ON, [ord('P'), mask_chan, 63])  # Mask flash
my_bpod.load_serial_message(SER_PORT, SER_CMD_ALL_OFF, [ord('X')])  # Stop both

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
                         + [(SER_DEVICE, SER_CMD_MASK_ON)] if i == 1 else []  # Only trigger once so that it can be manually turned off by 'X'
        )   # Give reward in turn
    
    sma.add_state(
        state_name='ITI',
        state_timer=iti,
        state_change_conditions={EventName.Tup: 'exit'},
        output_actions = [(SER_DEVICE, SER_CMD_LASER_ON)] if i == 1 else [])
        
    my_bpod.send_state_machine(sma)  # Send state machine description to Bpod device
    my_bpod.run_state_machine(sma)  # Run state machine

    # If stopped, break
    try:
        my_bpod.session.current_trial.export()
    except:
        break

my_bpod.manual_override(Bpod.ChannelTypes.OUTPUT, channel_name='Serial', channel_number=1, value=SER_CMD_ALL_OFF) 
my_bpod.close()



