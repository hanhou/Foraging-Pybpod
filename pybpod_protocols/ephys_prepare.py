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
laser_amp = 0.05
laser_dur = 200  # sec
laser_gap = 1  # sec
laser_chans = 6  # ch2 and ch3
laser_sin_freq = 40
############################################################

my_bpod = Bpod()
SER_DEVICE = OutputChannel.Serial1
SER_PORT = int(SER_DEVICE[-1])
SER_CMD_LASER_ON = 1
SER_CMD_LASER_OFF = 2

# --- Load waveform to WavePlayer ---
def gen_sin_wave(sampling_rate, freq, duration, phy=0):
    # Duration in seconds
    t = np.arange(0, duration, 1 / sampling_rate)
    return np.sin(2 * np.pi * freq * t + phy)

SAMPLING_RATE = 5000
wav_player = WavePlayerModule('COM7')   # "Teensy USB" in device manager
wav_player.set_trigger_mode(wav_player.TRIGGER_MODE_MASTER)   # 'Master' - triggers can force-start a new wave during playback.
wav_player.set_sampling_period(SAMPLING_RATE)
wav_player.set_output_range(wav_player.RANGE_VOLTS_MINUS5_5) 
wav_player.set_loop_duration([0, 1000 * SAMPLING_RATE, 1000 * SAMPLING_RATE, 0, 0, 0, 0, 0])
wav_player.set_loop_mode([0, 1, 1, 0, 0, 0, 0, 0])

for i in range(64):
    wav_player.load_waveform(i, [0])    

laser_sin_waveform = laser_amp * (gen_sin_wave(SAMPLING_RATE, laser_sin_freq, laser_dur, phy=np.pi * 3/2) + 1) / 2
wav_player.load_waveform(0, laser_sin_waveform) 

my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_ON, [ord('P'), laser_chans, 0])  # Turn on both
my_bpod.load_serial_message(SER_PORT, SER_CMD_LASER_OFF, [ord('X'), laser_chans])  # Stop both

# --- Start ---
i = 0

# Manual turn on once; to turn off, set "'X'" in emulator
my_bpod.manual_override(Bpod.ChannelTypes.OUTPUT, channel_name='Serial', channel_number=1, value=SER_CMD_LASER_ON)    

while True:
    i += 1
    print(f'Trial: {i}, valve: {water_ports[i % len(water_ports)]} ', i)
    
    sma = StateMachine(my_bpod)

    # sma.set_global_timer(timer_id=1, 
    #                     timer_duration=laser_dur, 
    #                     on_set_delay=0, 
    #                     channel=SER_DEVICE,
    #                     on_message=SER_CMD_LASER_ON, 
    #                     off_message=SER_CMD_LASER_OFF,
    #                     loop_mode=1, 
    #                     send_events=0,
    #                     loop_intervals=laser_gap,
    #                     )

    sma.add_state(
        state_name='Open',
        state_timer=valvetime,
        state_change_conditions={EventName.Tup: 'ITI'},
        output_actions = [('Valve', water_ports[i % len(water_ports)]), 
                          ('GlobalTimerTrig', 1)]
        )   # Give reward in turn
    
    sma.add_state(
        state_name='ITI',
        state_timer=iti,
        state_change_conditions={EventName.Tup: 'exit'},
        output_actions = [])
        
    my_bpod.send_state_machine(sma)  # Send state machine description to Bpod device
    my_bpod.run_state_machine(sma)  # Run state machine

    # If stopped, break
    try:
        my_bpod.session.current_trial.export()
    except:
        break

my_bpod.manual_override(Bpod.ChannelTypes.OUTPUT, channel_name='Serial', channel_number=1, value=SER_CMD_LASER_OFF) 
my_bpod.close()



