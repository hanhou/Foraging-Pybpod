import behavior_rozmar as behavior_rozmar
import sys, traceback
import os
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton,  QLineEdit, QCheckBox, QHBoxLayout, \
    QGroupBox, QDialog, QVBoxLayout, QGridLayout, QComboBox, QSizePolicy, qApp, QLabel, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer, Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

import numpy as np
from scipy import stats
import pandas as pd
import re
import time as time
from datetime import datetime
import json
import threading
import shutil

try:
    import zaber.serial as zaber_serial
except:
    pass
print('started')
paths = ['/home/rozmar/Data/Behavior/Behavior_rigs/Tower-2',
         'C:\\Users\\labadmin\\My Documents\\Pybpod\\Projects',
         'C:\\Users\\labadmin\\Documents\\Pybpod\\Projectss',
         'C:\\Users\\labadmin\\Documents\\foraging_projects\\Projects',
         'C:\\Users\\Han2\\Documents\\Pybpod\\Projects',
         'C:\\Users\\aind_behavior\\Documents\\PyBpod']

for defpath in paths:
    print(defpath)
    if os.path.exists(defpath):
        break
#defpath = '/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects'#'C:\\Users\\labadmin\\Documents\\Pybpod\\Projects'#'/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects'#
#%%
class App(QDialog):
    def __init__(self):
        super().__init__()
        print('started')
        self.dirs = dict()
        self.handles = dict()
        self.title = 'behavior - online analysis'
        self.left = 20 # 10
        self.top = 30 # 10
        self.width = 1300 # 1024
        self.height = 900  # 768
        self.dirs['projectdir'] =  defpath
        self.loaddirectorystructure()
        #self.loadthedata()
        self.data = None
        self.variables = None
        self.motorpositions = None
        self.motorpositions_previous = None
        self.initUI()

        self.timer  = QTimer(self)
        self.timer.setInterval(5000)          # Throw event timeout with an interval of 1000 milliseconds
        self.timer.timeout.connect(self.reloadthedata) # each time timer counts a second, call self.blink
        self.pickle_write_thread = None
        self.variables_to_display_old = {'Valve Open Time': {'lickport_number': '# Lickport',
                                                         'ValveOpenTime_L': 'L',
                                                         'ValveOpenTime_R': 'R',
                                                         'ValveOpenTime_M': 'M',
                                                         'accumulate_reward': 'Reward baiting prob.',
                                                        },
                                     'Base reward probability': {'difficulty_sum_reward_rate': 'sum',
                                                      'reward_rate_family': 'family',
                                                      'difficulty_ratio_pair_num': '# of pairs',
                                                      'block_start_with_bias_check': 'bias check (1:hard; 0.5:soft)',
                                                      },
                                     'Block': {'Trialnumber_in_block': 'beta',
                                               'Trialnumber_in_block_min': 'min',
                                               'Trialnumber_in_block_max': 'max',
                                               'auto_train_min_rewarded_trial_num': 'min reward each block',
                                               # 'block_number',
                                               },
                                     'Delay period': {'delay': 'beta',
                                                      'delay_min': 'min',
                                                      'delay_max': 'max',
                                                      'early_lick_punishment': 'early lick punish (<0: retraction)',
                                                      'fixation_reward': 'fixation reward',
                                                      },
                                     'ITI': {'iti': 'beta',
                                             'iti_min': 'min',
                                             'iti_max': 'max',
                                             'increase_ITI_on_ignore_trials': 'increase ITI if ignored',
                                             },
                                     'Auto water': {'auto_water': 'ON',
                                                    'auto_water_time_multiplier': 'multiplier',
                                                    'auto_water_min_unrewarder_trials_in_a_row': 'if unrewarded in a row',
                                                    'auto_water_min_ignored_trials_in_a_row': 'if ignored in a row',
                                                    },
                                     'Misc': {
                                              'response_time': 'RT',
                                              'auto_stop_max_ignored_trials_in_a_row': 'auto stop ignores >',
                                              'motor_retract_waterport': 'retract on ITI?',
                                              'double_dip_retract': 'retract on double dipping?',
                                             },
                                     'Advanced block':{
                                              'auto_block_switch_type': 'Auto (0:off;1:now;2:once)',
                                              'auto_block_switch_threshold': 'auto switch threshold',
                                              'auto_block_switch_points': 'points in a row',
                                              'change_to_go_next_block': 'Next block NOW! (0->1)',
                                             },
                                     'Photostimulation (time)':{
                                            #   'laser_early_ITI_dur': 'early ITI dur',
                                            #   'laser_early_ITI_offset': 'early ITI offset',
                                            #   'laser_late_ITI_dur': 'late ITI dur',
                                            #   'laser_late_ITI_offset': 'late ITI offset (<0: right-aligned)',
                                              'laser_offset': 'offset (sec)',
                                              'laser_duration': 'duration (sec)',
                                             },
                                     '             (schedule)':{
                                              'laser_side': 'side (0:L;1:R;2:LR)',
                                              'laser_random_ratio': 'random ratio',
                                              'laser_min_non_stim_before': 'min non stim before',                                                                }
                                     }


        self.variables_to_display_uncoupled = {'Valve Open Time': {'lickport_number': '# Lickport',
                                                         'ValveOpenTime_L': 'L',
                                                         'ValveOpenTime_R': 'R',
                                                         'ValveOpenTime_M': 'M',
                                                         'accumulate_reward': 'Reward baiting prob.',
                                                        },
                                     'Base reward probability': {'reward_prob_array': 'reward prob. array',
                                                      },
                                     'Block': {
                                               'Trialnumber_in_block_min': 'min',
                                               'Trialnumber_in_block_max': 'max',
                                            #    'auto_train_min_rewarded_trial_num': 'min reward each block',
                                               # 'block_number',
                                               },
                                     'Delay period': {'delay': 'beta',
                                                      'delay_min': 'min',
                                                      'delay_max': 'max',
                                                      'early_lick_punishment': 'early lick punish (<0: retraction)',
                                                      'fixation_reward': 'fixation reward',
                                                      },
                                     'ITI': {'iti': 'beta',
                                             'iti_min': 'min',
                                             'iti_max': 'max',
                                             'increase_ITI_on_ignore_trials': 'increase ITI if ignored',
                                             },
                                     'Auto water': {'auto_water': 'ON',
                                                    'auto_water_time_multiplier': 'multiplier',
                                                    'auto_water_min_unrewarder_trials_in_a_row': 'if unrewarded in a row',
                                                    'auto_water_min_ignored_trials_in_a_row': 'if ignored in a row',
                                                    },
                                     'Misc': {
                                              'response_time': 'RT',
                                              'auto_stop_max_ignored_trials_in_a_row': 'auto stop ignores >',
                                              'motor_retract_waterport': 'retract on ITI?',
                                              'double_dip_retract': 'retract on double dipping?',
                                             },
                                     'Advanced block':{
                                              'auto_block_switch_type': 'Auto (0:off;1:now;2:once)',
                                              'auto_block_switch_threshold': 'auto switch threshold',
                                              'auto_block_switch_points': 'points in a row',
                                              'change_to_go_next_block': 'Next block NOW! (0->1)',
                                             }, 
                                     'Photostimulation (time)':{
                                            #   'laser_early_ITI_dur': 'early ITI dur',
                                            #   'laser_early_ITI_offset': 'early ITI offset',
                                            #   'laser_late_ITI_dur': 'late ITI dur',
                                            #   'laser_late_ITI_offset': 'late ITI offset (<0: right-aligned)',
                                              'laser_offset': 'offset (sec)',
                                              'laser_duration': 'duration (sec)',
                                             },
                                     '             (schedule)':{
                                              'laser_side': 'side (0:L;1:R;2:LR)',
                                              'laser_random_ratio': 'random ratio',
                                              'laser_min_non_stim_before': 'min non stim before', 
                                              }
                                }
        
 

        self.sliding_win_fix_width = True

    def set_parameters_app(self):
        self.parametersetter = App_parametersetter(parent = self)

        self.parametersetter.show()

    def loaddirectorystructure(self,projectnames_needed = None, experimentnames_needed = None,  setupnames_needed=None):
        dirstructure, projectnames, experimentnames, setupnames, sessionnames, subjectnames = behavior_rozmar.loaddirstucture(defpath,projectnames_needed, experimentnames_needed,  setupnames_needed)
        self.dirstruct = dirstructure
        self.alldirs = dict()
        self.alldirs['projectnames'] = projectnames
        self.alldirs['experimentnames'] = experimentnames
        self.alldirs['setupnames'] = setupnames
        self.alldirs['sessionnames'] = sessionnames
        self.alldirs['subjectnames'] = subjectnames
        print('directory structure reloaded')

    def loadthedata(self):
        print('loadthedata')
        self.handles['load_the_data'].setText('Loading...')
        self.handles['load_the_data'].setStyleSheet('QPushButton {color: red;}')
        load_only_last_day = self.handles['only_recent_data'].isChecked()

        selected = dict()
        filterorder = ['project','experiment','setup','subject']
        for filternow in filterorder:
            filterstring = str(self.handles['filter_'+filternow].currentText())
            if not re.findall('all',filterstring):
                selected[filternow] = filterstring
            else:
                selected[filternow] = None

        if self.pickle_write_thread == None or not self.pickle_write_thread.isAlive():  #!!!
            self.pickle_write_thread = threading.Thread(target=behavior_rozmar.save_pickles_for_online_analysis,
                                                        args=(self.dirs['projectdir'],
                                                              selected['project'],
                                                              selected['experiment'],
                                                              selected['setup'],
                                                              load_only_last_day))  # User-defined
                                                                # False))   # Cache all data
                                                                # True))   # Only cache recent 5 days

            self.pickle_write_thread.daemon = True                            # Daemonize thread
            self.pickle_write_thread.start()

            # For debugging ...
            # behavior_rozmar.save_pickles_for_online_analysis(projectdir = self.dirs['projectdir'],
            #                                         projectnames_needed = selected['project'],
            #                                         experimentnames_needed = selected['experiment'],
            #                                         setupnames_needed = selected['setup'],
            #                                         load_only_last_day = load_only_last_day)
            try:
                self.data = behavior_rozmar.load_pickles_for_online_analysis(projectdir = self.dirs['projectdir'],
                                                        projectnames_needed = selected['project'],
                                                        experimentnames_needed = selected['experiment'],
                                                        setupnames_needed = selected['setup'],
                                                        subjectnames_needed = selected['subject'],
                                                        load_only_last_day = load_only_last_day)  # User-defined
                                                        # load_only_last_day = False)   # Load all data
                                                        # load_only_last_day = True)  # Only load recent 5 days
                qApp.processEvents()
                print('pkl loaded!')

                #Update motor position values from previous csv files
                rc_times  = self.data['times']['motor_position_rostrocaudal']
                order = np.argsort(rc_times)
                rc_times  = rc_times[order]
                #lat_times  = self.data['times']['motor_position_lateral'][order]
                lat_values = self.data['values']['motor_position_lateral'][order]
                rc_values = self.data['values']['motor_position_rostrocaudal'][order]

                # bigdiff_idxes = np.concatenate([np.diff(rc_times)>np.timedelta64(6,'h'),[True]])
                # uniquedays_str = np.asarray(np.asarray(rc_times[bigdiff_idxes],dtype = 'datetime64[D]'),dtype = str)
                bigdiff_idxes = np.concatenate([[True], np.diff(rc_times)>np.timedelta64(6,'h')])
                uniquedays_str = np.asarray(np.asarray(rc_times[1:][bigdiff_idxes[:-1]],dtype = 'datetime64[D]'),dtype = str)

                rc_positions = rc_values[bigdiff_idxes]
                lateral_positions = lat_values[bigdiff_idxes]
                self.motorpositions_previous = self.motorpositions
                self.motorpositions = dict()
                self.motorpositions['date'] = uniquedays_str
                self.motorpositions['rc_positions'] = rc_positions
                self.motorpositions['lateral_positions'] = lateral_positions

                self.handles['load_the_data'].setText('Load the data')
                self.handles['load_the_data'].setStyleSheet('QPushButton {color: black;}')
                self.updateUI()
                self.filterthedata()   # Filter and plot here!!

            except Exception as error:
                print('couldn\'t load the data..')
                traceback.print_exc()
                # print(error)
                self.handles['load_the_data'].setText('Load the data')
                self.handles['load_the_data'].setStyleSheet('QPushButton {color: black;}')

                # self.updateUI()
        else:
            print('pickle_write_thread is alive, skipping load')
        #print('data reloaded')
        #print(time.perf_counter())

    @pyqtSlot()
    def reloadthedata(self):
        #self.data = behavior_rozmar.loadcsvdata(self.data, projectdir = self.dirs['projectdir'])
        self.loadthedata()
        #self.filterthedata()
        # print('data reloaded')
        # print(time.perf_counter())

    def auto_load_data(self):
        if self.handles['plot_autorefresh'].isChecked():
            self.timer.start()
        else:
            self.timer.stop()

        # if lastselected != ' ':
    def filterthedata(self, lastselected = ' '):
        print('filterthedata...')

        if type(lastselected) == str and 'filter' in lastselected:
            # print(lastselected)
            self.updateUI_dirstructure(lastselected)

        if type(self.data) == dict:
            self.data_now = self.data.copy()

            if len(self.data_now) > 0:

                # --- Mine data ---
                times, values = self.minethedata(self.data_now, self.handles['select_session'].currentText())

                # --- Perform time range selection here instead of doing it twice in the plotting functions ---
                endtime = np.max(times['alltimes'])
                if self.handles['plot_timeback'].text().isnumeric():
                    plot_timeback = pd.to_timedelta(int(self.handles['plot_timeback'].text()),'s')
                    startime = np.max([np.datetime64(np.max(times['alltimes']) - plot_timeback),
                                       np.min(times['alltimes'])])
                else:
                    startime = np.min(times['alltimes'])

                # Update time and values.  HH20200730
                for timeskey in times.keys():
                    neededidx = (times[timeskey]>=startime) & (times[timeskey]<=endtime)
                    times[timeskey]= times[timeskey][neededidx]

                    if timeskey in values.keys():
                        values[timeskey]= values[timeskey][neededidx]

                    # Borrow reward_p's time range
                    if 'reward_p' in timeskey:
                        random_number_name = 'random_number_' + timeskey[-1]
                        if random_number_name in values.keys():
                            values[random_number_name]= values[random_number_name][neededidx]

                # --- Determine the sliding windows for plotting --
                if lastselected == 'window_number':
                    self.sliding_win_fix_width = False
                    self.handles['plot_timeback_runningwindow'].setStyleSheet('font-weight: bold')
                    self.handles['plot_timeback_runningwindow_in_sec'].setStyleSheet('font-weight: normal')
                elif lastselected == 'window_in_sec':
                    self.sliding_win_fix_width = True
                    self.handles['plot_timeback_runningwindow'].setStyleSheet('font-weight: normal')
                    self.handles['plot_timeback_runningwindow_in_sec'].setStyleSheet('font-weight: bold')

                if self.sliding_win_fix_width:    # Fixed sliding window (in sec)
                    try:   # To handle float number
                        win_width = float(self.handles['plot_timeback_runningwindow_in_sec'].text())
                    except:
                        win_width = 60
                    numberofpoints = int((endtime - startime)/ np.timedelta64(1,'s')/ win_width)
                else:     # Backward compatibility: fixed number of sigments (not to confuse Tina)
                    if self.handles['plot_timeback_runningwindow'].text().isnumeric(): # determining averaging window size
                        numberofpoints = int(self.handles['plot_timeback_runningwindow'].text())
                    else:
                        numberofpoints = 10
                    win_width = (endtime - startime)/ np.timedelta64(1,'s')/ numberofpoints # in sec

                self.handles['plot_timeback_runningwindow'].setText(f'{numberofpoints}')
                self.handles['plot_timeback_runningwindow_in_sec'].setText(f'{win_width:.1f}')

                # -- Update plots --
                if type(self.data_now) == dict and len(self.data_now) > 0:
                    print('Plotting...')
                    # Update plots
                    self.handles['axes'].update_plots(times, values, win_width * np.timedelta64(1,'s'))
                    qApp.processEvents()
                    print('Plotting done\n-------------------')

        if lastselected == 'filter_subject'  :
            print('last selected = filter_subject, reload')
            self.load_parameters()
            self.loadthedata()
# =============================================================================
#         data = self.data
#         handlenames = self.handles.keys()
#         filternames = list()
#         for handlename in handlenames:
#             if re.findall('filter',handlename): filternames.append(handlename)
#         if lastselected != ' ':
#             filternames.remove(lastselected)
#             filternames.insert(0,lastselected)
# =============================================================================

    def minethedata(self,data,session):
        times_old = data['times'].copy()
        values_old = data['values'].copy()
        times = dict()
        values = dict()
        days = dict()

        for key in times_old.keys():
            times_now  = times_old[key]
            order = np.argsort(times_now)
            times[key] = times_now[order]
            days[key] = np.asarray(times_now[order],dtype = 'datetime64[D]')

            if len(days[key])>0:
                # needed = days[key] == np.datetime64(session)
                same_day_this_session = times[key][days[key] == np.datetime64(session)]

                earliest_start_cutoff = 1  # The session will not start earlier than 2AM
                longest_session = 6  # Longest session = 6 hours
                if len(same_day_this_session):
                    # Take care of the situation where one training session crosses two days...
                    if key == 'alltimes':
                        start_time_this_session = same_day_this_session[pd.DatetimeIndex(same_day_this_session).hour > earliest_start_cutoff][0]

                    needed = np.logical_and(times[key] >= start_time_this_session, (times[key] - start_time_this_session) < np.timedelta64(longest_session,'h'))
                else:
                    needed = []

            else:
                needed = []

            times[key] = times[key][needed]
            if key in values_old.keys():
                values_now = values_old[key]
                values[key] = values_now[order]
                values[key] = values[key][needed]

            # Retreive random numbers
            if 'reward_p' in key:
                random_number_name = 'random_number_' + key[-1]
                if random_number_name in data['values'].keys():
                    values[random_number_name] = data['values'][random_number_name][needed]  # Borrow reward_p's needed

        return times, values

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        self.createGridLayout()

        windowLayout = QVBoxLayout()
        windowLayout.addWidget(self.horizontalGroupBox_filter)
        windowLayout.addWidget(self.horizontalGroupBox_plot_settings)
        windowLayout.addWidget(self.horizontalGroupBox_axes)
        windowLayout.addWidget(self.horizontalGroupBox_variables)
        self.setLayout(windowLayout)
        self.setWindowFlag(Qt.WindowMinimizeButtonHint, True)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        self.show()

    def createGridLayout(self):
        self.horizontalGroupBox_filter = QGroupBox("Filter")
        layout = QGridLayout()
        self.handles['filter_project'] = QComboBox(self)
        self.handles['filter_project'].setFocusPolicy(Qt.NoFocus)
        self.handles['filter_project'].addItem('all projects')
        #print(self.alldirs['projectnames'])
        self.handles['filter_project'].addItems(self.alldirs['projectnames'])
        self.handles['filter_project'].currentIndexChanged.connect(lambda: self.filterthedata('filter_project'))
        self.handles['filter_experiment'] = QComboBox(self)
        self.handles['filter_experiment'].setFocusPolicy(Qt.NoFocus)
        self.handles['filter_experiment'].addItem('all experiments')
        self.handles['filter_experiment'].addItems(self.alldirs['experimentnames'])
        self.handles['filter_experiment'].currentIndexChanged.connect(lambda: self.filterthedata('filter_experiment'))
        self.handles['filter_setup'] = QComboBox(self)
        self.handles['filter_setup'].setFocusPolicy(Qt.NoFocus)
        self.handles['filter_setup'].addItem('all setups')
        self.handles['filter_setup'].addItems(self.alldirs['setupnames'])
        self.handles['filter_setup'].currentIndexChanged.connect(lambda: self.filterthedata('filter_setup'))
# =============================================================================
#         self.handles['filter_session'] = QComboBox(self)
#         self.handles['filter_session'].setFocusPolicy(Qt.NoFocus)
#         self.handles['filter_session'].addItem('all sessions')
#         self.handles['filter_session'].addItems(self.alldirs['sessionnames'])
#         self.handles['filter_session'].currentIndexChanged.connect(lambda: self.filterthedata('filter_session'))
# =============================================================================

        self.handles['load_the_data'] = QPushButton('Load the data')
        self.handles['load_the_data'].setFocusPolicy(Qt.NoFocus)
        self.handles['load_the_data'].clicked.connect(self.loadthedata)

        self.handles['only_recent_data'] = QCheckBox('Recent data only')
        self.handles['only_recent_data'].setChecked(True)

        self.handles['filter_subject'] = QComboBox(self)
        self.handles['filter_subject'].setFocusPolicy(Qt.NoFocus)
        self.handles['filter_subject'].addItem('all subjects')
        #self.handles['filter_subject'].addItems(self.data['subject'].unique())
        self.handles['filter_subject'].currentIndexChanged.connect(lambda: self.filterthedata('filter_subject'))
# =============================================================================
#         self.handles['filter_experimenter'] = QComboBox(self)
#         self.handles['filter_experimenter'].setFocusPolicy(Qt.NoFocus)
#         self.handles['filter_experimenter'].addItem('all experimenters')
#         #self.handles['filter_experimenter'].addItems(self.data['experimenter'].unique())
#         self.handles['filter_experimenter'].currentIndexChanged.connect(lambda: self.filterthedata('filter_experimenter'))
# =============================================================================

        self.handles['loadparams'] = QPushButton('Restore')
        self.handles['loadparams'].setFocusPolicy(Qt.NoFocus)
        self.handles['loadparams'].clicked.connect(self.load_parameters)

        self.handles['loadparams_from_file'] = QPushButton('Load from file')
        self.handles['loadparams_from_file'].setFocusPolicy(Qt.NoFocus)
        self.handles['loadparams_from_file'].clicked.connect(self.load_parameters_from_file)

        self.handles['save_parameters_to_file'] = QPushButton('Save to file')
        self.handles['save_parameters_to_file'].setFocusPolicy(Qt.NoFocus)
        self.handles['save_parameters_to_file'].clicked.connect(self.save_parameters_to_file)

        self.handles['select_session'] = QComboBox(self)
        self.handles['select_session'].setFocusPolicy(Qt.NoFocus)
        self.handles['select_session'].currentIndexChanged.connect(self.filterthedata)
        #self.handles['select_session'].addItem('all sessions')
        #sessionnames = self.alldirs['sessionnames']
        #sessionnames.sort(reverse = True)
        #self.handles['select_session'].addItems(sessionnames)
        #self.handles['select_session'].currentIndexChanged.connect(lambda: self.filterthedata('filter_session'))

        self.handles['set_lickport_position'] = QPushButton('Set lickport position')
        self.handles['set_lickport_position'].setFocusPolicy(Qt.NoFocus)
        self.handles['set_lickport_position'].clicked.connect(self.set_lickport_position)

        layout.addWidget(self.handles['filter_project'] ,0,0)
        layout.addWidget(self.handles['filter_experiment'],0,1)
        layout.addWidget(self.handles['filter_setup'],0,2)
        #layout.addWidget(self.handles['filter_session'],0,3)
        layout.addWidget(self.handles['filter_subject'],0,3)
        layout.addWidget(self.handles['only_recent_data'], 0, 4)
        layout.addWidget(self.handles['load_the_data'],0,5)
        #layout.addWidget(self.handles['filter_experimenter'],0,5)
        layout.addWidget(self.handles['select_session'],0,6)
        layout.addWidget(self.handles['select_session'],0,6)

        layout.addWidget(QLabel('\tParameters'),0,7)
        layout.addWidget(self.handles['loadparams'],0,8)
        layout.addWidget(self.handles['loadparams_from_file'],0,9)
        layout.addWidget(self.handles['save_parameters_to_file'],0,10)
        layout.addWidget(self.handles['set_lickport_position'],0,11)
        self.horizontalGroupBox_filter.setLayout(layout)

        # ----- Online plotting -----
        self.horizontalGroupBox_axes = QGroupBox("plots")
        layout_axes = QGridLayout()

        # Add NavigationToolBar (zoom in/out). HH20200729
        self.handles['axes'] = PlotCanvas(self, width=5, height=4)
        self.handles['navigation_toolbar'] = NavigationToolbar(self.handles['axes'], self, )
        self.handles['training_results'] =  QLineEdit(self)

        # Use only one canvas for all (sub)plots, which makes axis control more straightforward. HH20200729
        # self.handles['axes1'] = PlotCanvas(self, width=5, height=4)
        # self.handles['axes2'] = PlotCanvas(self, width=5, height=4)
        # layout_axes.addWidget(self.handles['axes1'],1,0)
        # layout_axes.addWidget(self.handles['axes2'],2,0)
        # self.handles['axes1'].axes.get_shared_x_axes().join(self.handles['axes1'].axes, self.handles['axes2'].axes)

        layout_axes.addWidget(self.handles['navigation_toolbar'], 0, 0, 1, 2)
        layout_axes.addWidget(self.handles['training_results'], 0, 2, 1, 6 )
        layout_axes.addWidget(self.handles['axes'], 1, 0, 1, 8)

        self.horizontalGroupBox_axes.setLayout(layout_axes)

        self.horizontalGroupBox_plot_settings = QGroupBox("Plot settings")
        layout_plot_settings = QGridLayout()

        layout_plot_settings.addWidget(QLabel('Time back to plot (sec)'),0,0)
        self.handles['plot_timeback'] = QLineEdit(self)
        self.handles['plot_timeback'].setText('(all)')
        self.handles['plot_timeback'].returnPressed.connect(self.filterthedata)
        layout_plot_settings.addWidget(self.handles['plot_timeback'],0,1)

        layout_plot_settings.addWidget(QLabel('Number of segements'),0,2)
        self.handles['plot_timeback_runningwindow'] = QLineEdit(self)
        self.handles['plot_timeback_runningwindow'].setText('(auto)')
        self.handles['plot_timeback_runningwindow'].returnPressed.connect(lambda: self.filterthedata(lastselected='window_number'))
        layout_plot_settings.addWidget(self.handles['plot_timeback_runningwindow'],0,3)

        layout_plot_settings.addWidget(QLabel('Sliding window width (sec)'),0,4)
        self.handles['plot_timeback_runningwindow_in_sec'] = QLineEdit(self)
        self.handles['plot_timeback_runningwindow_in_sec'].setText('100')  # Default value: fixed width 100s
        self.handles['plot_timeback_runningwindow_in_sec'].setStyleSheet('font-weight: bold')
        self.handles['plot_timeback_runningwindow_in_sec'].returnPressed.connect(lambda: self.filterthedata(lastselected='window_in_sec'))
        layout_plot_settings.addWidget(self.handles['plot_timeback_runningwindow_in_sec'],0,5)

        self.handles['plot_autorefresh'] = QCheckBox(self)
        self.handles['plot_autorefresh'].setText('auto refresh data')
        layout_plot_settings.addWidget(self.handles['plot_autorefresh'],0,6)
        self.handles['plot_autorefresh'].stateChanged.connect(self.auto_load_data)
        self.horizontalGroupBox_plot_settings.setLayout(layout_plot_settings)

        self.horizontalGroupBox_variables = QGroupBox("Variables")

    def updateUI(self): # update the other qcomboboxes as well!!!
# =============================================================================
#         self.handles['filter_subject'].currentIndexChanged.disconnect()
#         currtext = self.handles['filter_subject'].currentText()
#         self.handles['filter_subject'].clear()
#         self.handles['filter_subject'].addItem('all subjects')
#         if type(self.data) == pd.DataFrame:
#             self.handles['filter_subject'].addItems(self.data['subject'].unique())
#             idx = self.handles['filter_subject'].findText(currtext)
#             if idx != -1:
#                 self.handles['filter_subject'].setCurrentIndex(idx)
#         currtext = self.handles['filter_subject'].currentText()
#         self.handles['filter_subject'].currentIndexChanged.connect(lambda: self.filterthedata('filter_subject'))
#
# =============================================================================
        if self.motorpositions:
            self.handles['select_session'].currentIndexChanged.disconnect()
            self.handles['select_session'].clear()
            self.handles['select_session'].addItems(self.motorpositions['date'])
            self.handles['select_session'].setCurrentIndex(len(self.motorpositions['date'])-1)
            self.handles['select_session'].currentIndexChanged.connect(self.filterthedata)

# =============================================================================
#         self.handles['filter_experimenter'].currentIndexChanged.disconnect()
#         currtext = self.handles['filter_experimenter'].currentText()
#         self.handles['filter_experimenter'].clear()
#         self.handles['filter_experimenter'].addItem('all experimenters')
#         if type(self.data) == pd.DataFrame:
#             self.handles['filter_experimenter'].addItems(self.data['experimenter'].unique())
#             idx = self.handles['filter_experimenter'].findText(currtext)
#             if idx != -1:
#                 self.handles['filter_experimenter'].setCurrentIndex(idx)
#         self.handles['filter_experimenter'].currentIndexChanged.connect(lambda: self.filterthedata('filter_experimenter'))
# =============================================================================

    def updateUI_dirstructure(self, lastselected):
        project_now = [self.handles['filter_project'].currentText()]
        experiment_now = [self.handles['filter_experiment'].currentText()]
        setup_now =[self.handles['filter_setup'].currentText()]
        #session_now = self.handles['filter_session'].currentText()
        if project_now[0] == 'all projects':
            project_now = None
        if experiment_now[0] == 'all experiments':
            experiment_now = None
        if setup_now[0] == 'all setups':
            setup_now = None
        self.loaddirectorystructure(project_now, experiment_now,  setup_now)
        if lastselected == 'filter_project':
            self.handles['filter_experiment'].currentIndexChanged.disconnect()
            self.handles['filter_experiment'].clear()
            self.handles['filter_experiment'].addItem('all experiments')
            self.handles['filter_experiment'].addItems(self.alldirs['experimentnames'])
            self.handles['filter_experiment'].currentIndexChanged.connect(lambda: self.filterthedata('filter_experiment'))

            self.handles['filter_subject'].currentIndexChanged.disconnect()
            self.handles['filter_subject'].clear()
            self.handles['filter_subject'].addItem('all subjects')
            self.handles['filter_subject'].addItems(self.alldirs['subjectnames'])
            self.handles['filter_subject'].currentIndexChanged.connect(lambda: self.filterthedata('filter_subject'))

        if lastselected == 'filter_project' or lastselected == 'filter_experiment':
            self.handles['filter_setup'].currentIndexChanged.disconnect()
            self.handles['filter_setup'].clear()
            self.handles['filter_setup'].addItem('all setups')
            self.handles['filter_setup'].addItems(self.alldirs['setupnames'])
            self.handles['filter_setup'].currentIndexChanged.connect(lambda: self.filterthedata('filter_setup'))

        try:
            print('load parameters with reload_variable_layout=True')
            self.load_parameters(reload_varialbe_layout=False)
        except:
            import traceback
            traceback.print_exc()
            pass



# =============================================================================
#         if lastselected == 'filter_project' or lastselected == 'filter_experiment' or lastselected == 'filter_setup':
#             #self.handles['select_session'].currentIndexChanged.disconnect()
#             self.handles['select_session'].clear()
#             #self.handles['select_session'].addItem('all sessions')
#             sessionnames = self.alldirs['sessionnames']
#             sessionnames.sort(reverse = True)
#             self.handles['select_session'].addItems(sessionnames)
#             #self.handles['select_session'].currentIndexChanged.connect(lambda: self.filterthedata('filter_session'))
# =============================================================================
# =============================================================================
#     def zaber_move_Lat(self):
#         if 	self.handles['motor_LAT_edit'].text().isnumeric():
#
#         self.zaber_refresh()
#
#
#     def zaber_move_RC(self):
#         if 	self.handles['motor_RC_edit'].text().isnumeric():
#             for zabertry_i in range(0,1000): # when the COMport is occupied, it will try again
#                 try:
#                     with zaber_serial.BinarySerial(variables['comport_motor']) as ser:
#                         moveabs_cmd = zaber_serial.BinaryCommand(1,20,int(self.handles['motor_RC_edit'].text()))
#                         ser.write(moveabs_cmd)
#                         time.sleep(.1)
#                     break
#                 except zaber_serial.binaryserial.serial.SerialException:
#                     print('can''t access Zaber ' + str(zabertry_i))
#                     time.sleep(.01)
#         self.zaber_refresh()
# =============================================================================

    def set_lickport_position(self):
        #%%
        if self.motorpositions:
            idx = self.handles['select_session'].currentText() == np.asarray(self.motorpositions['date'])
# =============================================================================
#             print(self.motorpositions)
#             print(self.motorpositions['rc_positions'][idx][0])
#             print(self.motorpositions['lateral_positions'][idx][0])
#             print(self.variables['subject']['motor_retractiondistance'])
# =============================================================================
            try:
                for zabertry_i in range(0,1000): # when the COMport is occupied, it will try again
                    try:
                        with zaber_serial.BinarySerial(self.variables['setup']['comport_motor']) as ser:
                            moveabs_cmd = zaber_serial.BinaryCommand(2,20,int(self.motorpositions['lateral_positions'][idx][0]))
                            ser.write(moveabs_cmd)
                            time.sleep(.1)
                        break
                    except zaber_serial.binaryserial.serial.SerialException:
                        print('can''t access Zaber ' + str(zabertry_i))
                    time.sleep(.01)
                for zabertry_i in range(0,1000): # when the COMport is occupied, it will try again
                    try:
                        with zaber_serial.BinarySerial(self.variables['setup']['comport_motor']) as ser:
                            pos = int(self.motorpositions['rc_positions'][idx][0]-self.variables['subject']['motor_retractiondistance'])
                            if pos<0:
                                pos = 0
                            moveabs_cmd = zaber_serial.BinaryCommand(1,20,pos)
                            ser.write(moveabs_cmd)
                            time.sleep(.1)
                        break
                    except zaber_serial.binaryserial.serial.SerialException:
                        print('can''t access Zaber ' + str(zabertry_i))
                    time.sleep(.01)
            except:
                print('zaber issue')
                pass

    def load_parameters(self, reload_varialbe_layout=False):
        maxcol = 4 # number of columns
        project_now = self.handles['filter_project'].currentText()
        experiment_now = self.handles['filter_experiment'].currentText()
        setup_now = self.handles['filter_setup'].currentText()
        subject_now = self.handles['filter_subject'].currentText()
                
        if 'uncoupled' in experiment_now:
            self.variables_to_display = self.variables_to_display_uncoupled
        else:
            self.variables_to_display = self.variables_to_display_old 

        if project_now != 'all projects' and experiment_now != 'all experiments' and setup_now != 'all setups' and subject_now != 'all subjects':
            
            subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,f'variables_{experiment_now}.json')
            if not os.path.exists(subject_var_file):
                subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,f'variables.json')  # Backward compatibility
            
            setup_var_file = os.path.join(defpath,project_now,'experiments',experiment_now,'setups',setup_now,'variables.json')
            with open(subject_var_file) as json_file:
                variables_subject = json.load(json_file)
                print(f'load subject variables from {subject_var_file}')
            with open(setup_var_file) as json_file:
                variables_setup = json.load(json_file)

            # laser calibration curve
            laser_calib_file = os.path.join(defpath, project_now, 'experiments', experiment_now, 'setups', setup_now,'laser_power_mapper.json')
            if os.path.exists(laser_calib_file):
                with open(laser_calib_file) as json_file:
                    self.laser_power_mapper = json.load(json_file)['laser_power_mapper']
                self.laser_power_mapper.insert(0, [0] * len(self.laser_power_mapper[0]))
            else:
                self.laser_power_mapper = [[0, 0.0], [1, 1.0], [2, 2.0], [3, 3.0], [4, 4.0], [5, 5.0]]

            if self.variables is None or reload_varialbe_layout:                
                layout = QGridLayout()
            #     self.horizontalGroupBox_preset_variables = QGroupBox("Preset variables")
                self.horizontalGroupBox_variables_setup = QGroupBox("Setup: "+setup_now)
                self.horizontalGroupBox_variables_subject = QGroupBox("Subject: "+subject_now)
            #     layout.addWidget(self.horizontalGroupBox_preset_variables ,0,0)
                layout.addWidget(self.horizontalGroupBox_variables_setup ,1,0)
                layout.addWidget(self.horizontalGroupBox_variables_subject ,2,0)
                self.horizontalGroupBox_variables.setLayout(layout)

            #     # Preset variables
            #     layout_preset = QGridLayout()
            #     self.handles['presetbuttons'] = dict()
            #     for idx,key in enumerate(self.preset_variables.keys()):
            #         self.handles['presetbuttons'][key] = QPushButton(key)
            #         self.handles['presetbuttons'][key].setFocusPolicy(Qt.NoFocus)
            #         self.handles['presetbuttons'][key].clicked.connect(lambda state, x=key: self.preload_parameters(x))
            #         layout_preset.addWidget(self.handles['presetbuttons'][key] ,0,idx)
            #     self.horizontalGroupBox_preset_variables.setLayout(layout_preset)

                # Parameter settings
                layout_setup = QGridLayout()
                row = 0
                col = -1
                self.handles['variables_setup']=dict()
                for idx,key in enumerate(variables_setup.keys()):
                    if key in self.variables_to_display:
                        col +=1
                        if col > maxcol*2:
                            col = 0
                            row += 1
                        layout_setup.addWidget(QLabel(key+':') ,row,col)
                        col +=1
                        self.handles['variables_setup'][key] =  QLineEdit(str(variables_setup[key]))
                        self.handles['variables_setup'][key].returnPressed.connect(self.save_parameters)
                        self.handles['variables_setup'][key].textChanged.connect(self.check_parameters)
                        layout_setup.addWidget(self.handles['variables_setup'][key] ,row,col)
                self.horizontalGroupBox_variables_setup.setLayout(layout_setup)

                self.handles['variables_subject']=dict()
                layout_subject = QGridLayout()

                for row, cat_name in enumerate(self.variables_to_display):
                    # Category name
                    layout_subject.addWidget(QLabel(cat_name +':'), row, 0, 1, 2)
                    col = 2

                    # Variables in this category
                    for var_name in self.variables_to_display[cat_name]:
                        var_name_alias = self.variables_to_display[cat_name][var_name]
                        layout_subject.addWidget(QLabel(var_name_alias + ' = '), row, col, alignment=Qt.AlignRight)
                        col += 1

                        if var_name in variables_subject.keys():   # If we have this var_name (back compatibility)
                            self.handles['variables_subject'][var_name] = QLineEdit(str(variables_subject[var_name]))
                            self.handles['variables_subject'][var_name].returnPressed.connect(self.save_parameters)
                            self.handles['variables_subject'][var_name].textChanged.connect(self.check_parameters)
                        else:
                            self.handles['variables_subject'][var_name] = QLineEdit("NA")
                            self.handles['variables_subject'][var_name].returnPressed.connect(self.save_parameters)
                            self.handles['variables_subject'][var_name].textChanged.connect(self.check_parameters)
                            self.handles['variables_subject'][var_name].setStyleSheet('QLineEdit {background: grey;}')

                        layout_subject.addWidget(self.handles['variables_subject'][var_name], row, col, alignment=Qt.AlignRight)
                        col += 1

                self.handles['actual_reward_prob'] = QLabel('')
                layout_subject.addWidget(self.handles['actual_reward_prob'], 1, 10, 1, 2)

                self.handles['success_switched'] = QLabel('')
                layout_subject.addWidget(self.handles['success_switched'], 7, 10, 1, 2)

                # Laser power selector
                self.handles['laser_power'] = QComboBox(self)
                self.handles['laser_power'].setFocusPolicy(Qt.NoFocus)
                self.update_laser_power_selector(variables_subject)

                layout_subject.addWidget(QLabel('power (mW)'), 9, 10, alignment=Qt.AlignRight)
                layout_subject.addWidget(self.handles['laser_power'], 9, 11, 1, 1)

                # Laser start alignment selector
                self.handles['laser_align_to'] = QComboBox(self)
                self.handles['laser_align_to'].setFocusPolicy(Qt.NoFocus)
                self.handles['laser_align_to'].addItems(['After ITI START', 'Before GO CUE', 'After GO CUE'])

                if 'laser_align_to' in variables_subject:
                     self.handles['laser_align_to'].setCurrentText(variables_subject['laser_align_to'])

                self.handles['laser_align_to'].currentIndexChanged.connect(self.save_parameters)

                layout_subject.addWidget(QLabel('start aligned to'), 8, 6, alignment=Qt.AlignRight)
                layout_subject.addWidget(self.handles['laser_align_to'], 8, 7, 1, 1)

                self.horizontalGroupBox_variables_subject.setLayout(layout_subject)
                self.variables=dict()
                
            else:
                self.horizontalGroupBox_variables_setup.setTitle("Setup: "+setup_now)
                self.horizontalGroupBox_variables_subject.setTitle("Subject: "+subject_now)

                for key in self.handles['variables_subject'].keys():
                    if key in variables_subject.keys():
                        self.handles['variables_subject'][key].setText(str(variables_subject[key]))
                    else:  # Just in case there are missing parameters (due to updated parameter tables)
                        self.handles['variables_subject'][key].setText("NA")
                        self.handles['variables_subject'][key].setStyleSheet('QLineEdit {background: grey;}')

                for key in self.handles['variables_setup'].keys():
                    self.handles['variables_setup'][key].setText(str(variables_setup[key]))

                self.update_laser_power_selector(variables_subject)


            self.show_actual_reward_prob()
            self.variables['subject'] = variables_subject
            self.variables['setup'] = variables_setup
            self.variables['subject_file'] = subject_var_file
            self.variables['setup_file'] = setup_var_file

        self.enable_disable_fields()

    def update_laser_power_selector(self, variables_subject):
        try:
            self.handles['laser_power'].currentIndexChanged.disconnect()
        except:
            pass
        self.handles['laser_power'].clear()

        if len(self.laser_power_mapper[0]) == 3:
            self.handles['laser_power'].addItems([f'{pow:>6} mW : L = {L_v:>5} V, R = {R_v:>5} V' for pow, L_v, R_v in self.laser_power_mapper])
        else:
            self.handles['laser_power'].addItems([f'{pow:>6} mW : {v:>5} V' for pow, v in self.laser_power_mapper])

        if 'laser_power' in variables_subject:
            preset = [id for id, (pow, *_) in enumerate(self.laser_power_mapper)
                        if pow == variables_subject['laser_power']]
            if len(preset):
                self.handles['laser_power'].setCurrentIndex(preset[0])  # Should be placed BEFORE the next line!!
            else:
                self.handles['laser_power'].setCurrentIndex(0)  # Should be placed BEFORE the next line!!

        self.handles['laser_power'].currentIndexChanged.connect(self.save_parameters)


    def load_parameters_from_file(self):
        project_now = self.handles['filter_project'].currentText()
        fname = QFileDialog.getOpenFileName(self, 'Open file',
                                           os.path.join(defpath, project_now,'subjects'),
                                           "Json files (*.json)")
        if not fname[0]:  return
        with open(fname[0]) as json_file:
            variables_subject = json.load(json_file)

        for key in self.handles['variables_subject'].keys():
            if key in variables_subject.keys():
                self.handles['variables_subject'][key].setText(str(variables_subject[key]))
            else:  # Just in case there are missing parameters (due to updated parameter tables)
                self.handles['variables_subject'][key].setText("NA")
                self.handles['variables_subject'][key].setStyleSheet('QLineEdit {background: grey;}')

        self.check_parameters()

    def save_parameters_to_file(self):
        project_now = self.handles['filter_project'].currentText()
        subject_now = self.handles['filter_subject'].currentText()
        experiment_now = self.handles['filter_experiment'].currentText()
        
        subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,f'variables_{experiment_now}.json')
        if not os.path.exists(subject_var_file):
            subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,f'variables.json')  # Backward compatibility

        # Copy the current variable file to a new file
        fname = QFileDialog.getSaveFileName(self, 'Open file',
                                           os.path.join(defpath, project_now,'subjects'),
                                           "Json files (*.json)")
        if fname[0]:
            shutil.copy(subject_var_file, fname[0])


    def check_parameters(self):
        project_now = self.handles['filter_project'].currentText()
        experiment_now = self.handles['filter_experiment'].currentText()
        setup_now = self.handles['filter_setup'].currentText()
        subject_now = self.handles['filter_subject'].currentText()
        
        subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,f'variables_{experiment_now}.json')
        if not os.path.exists(subject_var_file):
            subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,f'variables.json')  # Backward compatibility
        
        # Experiment-specific variables
        setup_var_file = os.path.join(defpath,project_now,'experiments',experiment_now,'setups',setup_now,'variables.json')
        with open(subject_var_file) as json_file:
            variables_subject = json.load(json_file)
        with open(setup_var_file) as json_file:
            variables_setup = json.load(json_file)

        self.variables['subject'] = variables_subject
        self.variables['setup'] = variables_setup
        for dicttext in ['subject','setup']:
            for key in self.handles['variables_'+dicttext].keys():
                valuenow = None

                # Auto formatting
                if key in self.variables[dicttext].keys():  # If json file has the parameter in the GUI (backward compatibility). HH20200730
                    if type(self.variables[dicttext][key]) == bool:
                        if 'true' in self.handles['variables_'+dicttext][key].text().lower() or '1' in self.handles['variables_'+dicttext][key].text():
                            valuenow = True
                        else:
                            valuenow = False
                    elif type(self.variables[dicttext][key]) == float:
                        try:
                            valuenow = float(self.handles['variables_'+dicttext][key].text())
                        except:
                            print('not proper value')
                            valuenow = None
                    elif type(self.variables[dicttext][key]) == int:
                        try:
                            valuenow = int(round(float(self.handles['variables_'+dicttext][key].text())))
                        except:
                            print('not proper value')
                            valuenow = None
                    else:  # string of list, etc
                        try:
                            valuenow = json.loads(self.handles['variables_'+dicttext][key].text())
                        except:
                            print('not proper value')
                            valuenow = None


                    # Turn the newly changed parameters to red
                    if valuenow == self.variables[dicttext][key]:
                        self.handles['variables_'+dicttext][key].setStyleSheet('QLineEdit {color: black;}')
                    else:
                        self.handles['variables_'+dicttext][key].setStyleSheet('QLineEdit {color: red;}')
                else:   # If json file has missing parameters (backward compatibility). HH20200730
                    # self.handles['variables_subject'][key].setText("NA")
                    self.handles['variables_subject'][key].setStyleSheet('QLineEdit {background: grey;}')
        try:
            self.enable_disable_fields()            
        except:
            print('Warning: "enable_disable_fields" failed...')
        self.show_actual_reward_prob()
        qApp.processEvents()

    def enable_disable_fields(self):
        
        if 'uncoupled' in self.handles['filter_experiment'].currentText():
            # self.cache_auto_train_min_rewarded_trial_num = int(self.handles['variables_subject']['auto_train_min_rewarded_trial_num'].text())
            self.handles['variables_subject']['auto_block_switch_threshold'].setEnabled(False)
            self.handles['variables_subject']['auto_block_switch_points'].setEnabled(False)

            if self.handles['variables_subject']['auto_water'].text() == 'True':
                self.handles['variables_subject']['auto_water_time_multiplier'].setEnabled(True)
                self.handles['variables_subject']['auto_water_min_ignored_trials_in_a_row'].setEnabled(True)
                self.handles['variables_subject']['auto_water_min_unrewarder_trials_in_a_row'].setEnabled(True)
            else:
                self.handles['variables_subject']['auto_water_time_multiplier'].setEnabled(False)
                self.handles['variables_subject']['auto_water_min_ignored_trials_in_a_row'].setEnabled(False)
                self.handles['variables_subject']['auto_water_min_unrewarder_trials_in_a_row'].setEnabled(False)

            if int(self.handles['variables_subject']['lickport_number'].text()) == 2:
                self.handles['variables_subject']['ValveOpenTime_M'].setEnabled(False)
            else:
                self.handles['variables_subject']['ValveOpenTime_M'].setEnabled(True)
                
            try:
                if float(self.handles['variables_subject']['laser_random_ratio'].text()) == -1:
                    self.handles['variables_subject']['laser_min_non_stim_before'].setEnabled(False)
                else:
                    self.handles['variables_subject']['laser_min_non_stim_before'].setEnabled(True)
            except:
                pass
        else:
            # self.cache_auto_train_min_rewarded_trial_num = int(self.handles['variables_subject']['auto_train_min_rewarded_trial_num'].text())
            if self.handles['variables_subject']['auto_block_switch_type'].text() == 'NA' or not int(self.handles['variables_subject']['auto_block_switch_type'].text()):
                self.handles['variables_subject']['auto_train_min_rewarded_trial_num'].setEnabled(True)
                self.handles['variables_subject']['auto_block_switch_threshold'].setEnabled(False)
                self.handles['variables_subject']['auto_block_switch_points'].setEnabled(False)
                if self.handles['variables_subject']['auto_train_min_rewarded_trial_num'].text() == '999':
                    self.handles['variables_subject']['auto_train_min_rewarded_trial_num'].setText('0')
            else:
                self.handles['variables_subject']['auto_train_min_rewarded_trial_num'].setEnabled(False)
                self.handles['variables_subject']['auto_block_switch_threshold'].setEnabled(True)
                self.handles['variables_subject']['auto_block_switch_points'].setEnabled(True)

            if self.handles['variables_subject']['auto_water'].text() == 'True':
                self.handles['variables_subject']['auto_water_time_multiplier'].setEnabled(True)
                self.handles['variables_subject']['auto_water_min_ignored_trials_in_a_row'].setEnabled(True)
                self.handles['variables_subject']['auto_water_min_unrewarder_trials_in_a_row'].setEnabled(True)
            else:
                self.handles['variables_subject']['auto_water_time_multiplier'].setEnabled(False)
                self.handles['variables_subject']['auto_water_min_ignored_trials_in_a_row'].setEnabled(False)
                self.handles['variables_subject']['auto_water_min_unrewarder_trials_in_a_row'].setEnabled(False)

            if int(self.handles['variables_subject']['lickport_number'].text()) == 2:
                self.handles['variables_subject']['ValveOpenTime_M'].setEnabled(False)
            else:
                self.handles['variables_subject']['ValveOpenTime_M'].setEnabled(True)

            try:
                if float(self.handles['variables_subject']['laser_random_ratio'].text()) == -1:
                    self.handles['variables_subject']['laser_min_non_stim_before'].setEnabled(False)
                else:
                    self.handles['variables_subject']['laser_min_non_stim_before'].setEnabled(True)
            except:
                pass

    def save_parameters(self):
        project_now = self.handles['filter_project'].currentText()
        experiment_now = self.handles['filter_experiment'].currentText()
        setup_now = self.handles['filter_setup'].currentText()
        subject_now = self.handles['filter_subject'].currentText()

        subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,f'variables_{experiment_now}.json')
        if not os.path.exists(subject_var_file):
            subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,f'variables.json')  # Backward compatibility

        setup_var_file = os.path.join(defpath,project_now,'experiments',experiment_now,'setups',setup_now,'variables.json')
        with open(subject_var_file) as json_file:
            variables_subject = json.load(json_file)
        with open(setup_var_file) as json_file:
            variables_setup = json.load(json_file)
        self.variables['subject'] = variables_subject
        self.variables['setup'] = variables_setup
        print('save')
        for dicttext in ['subject','setup']:
            for key in self.handles['variables_'+dicttext].keys():

                # Auto formatting
                if key in self.variables[dicttext].keys():  # If json file has the parameter in the GUI (backward compatibility). HH20200730
                    if type(self.variables[dicttext][key]) == bool:
                        if 'true' in self.handles['variables_'+dicttext][key].text().lower() or '1' in self.handles['variables_'+dicttext][key].text():
                            self.variables[dicttext][key] = True
                        else:
                            self.variables[dicttext][key] = False
                    elif type(self.variables[dicttext][key]) == float:
                        try:
                            self.variables[dicttext][key] = float(self.handles['variables_'+dicttext][key].text())
                        except:
                            print('not proper value')
                    elif type(self.variables[dicttext][key]) == int:
                        try:
                            self.variables[dicttext][key] = int(round(float(self.handles['variables_'+dicttext][key].text())))
                        except:
                            print('not proper value')
                    else:  # string of list, etc
                        try:
                            self.variables[dicttext][key] = json.loads(self.handles['variables_'+dicttext][key].text())
                        except:
                            print('not proper value')
  
                else:   # If json file has missing parameters, we add this new parameter (backward compatibility). HH20200730
                    if type(self.handles['variables_'+dicttext][key].text()) == int:
                        self.variables[dicttext][key] = int(self.handles['variables_'+dicttext][key].text())   # Only consider int now
                    else:
                        self.variables[dicttext][key] = float(self.handles['variables_'+dicttext][key].text())   # Only consider int now

        # Laser power
        self.variables['subject']['laser_power'] = float(self.handles['laser_power'].currentText().split('mW')[0])

        # Laser alignment
        self.variables['subject']['laser_align_to'] = self.handles['laser_align_to'].currentText()

        with open(self.variables['setup_file'], 'w') as outfile:
            json.dump(self.variables['setup'], outfile, indent=4)
        with open(self.variables['subject_file'], 'w') as outfile:
            json.dump(self.variables['subject'], outfile, indent=4)

        self.load_parameters()
        self.check_parameters()

    def preload_parameters(self,key):
        presetvars = self.preset_variables[key]
        for dicttext in ['subject','setup']:
            for key in self.handles['variables_'+dicttext].keys():
                if key in presetvars.keys():
                    self.handles['variables_'+dicttext][key].setText(str(presetvars[key]))
        self.check_parameters()

    def show_actual_reward_prob(self):
        # Show actual reward probability (same code as pybpod protocol)
        try:
            reward_rate_family = float(self.handles['variables_subject']['reward_rate_family'].text())
            difficulty_sum_reward_rate = float(self.handles['variables_subject']['difficulty_sum_reward_rate'].text())
            difficulty_ratio_pair_num = int(self.handles['variables_subject']['difficulty_ratio_pair_num'].text())

            if difficulty_ratio_pair_num < 1:
                reward_ratio_pairs = [[1,1]]   # For the very beginning of training
            else:
                if reward_rate_family <= 1:
                    reward_ratio_pairs=[[.4,.05],[.3857,.0643],[.3375,.1125],[.225,.225]]#,        # 8:1, 6:1, 3:1, 1:1
                elif reward_rate_family == 2:
                    reward_ratio_pairs=[[8, 1], [1, 1]]   # 8:1, 1:1
                elif reward_rate_family == 3:
                    reward_ratio_pairs=[[1,0],[.9,.1],[.8,.2],[.7,.3],[.6,.4],[.5,.5]]#,
                elif reward_rate_family == 4:       # Starting from 6:1, 3:1, 1:1 (Lau2005 = {6:1, 3:1})
                    reward_ratio_pairs=[[6, 1],[3, 1],[1, 1]]
                reward_ratio_pairs = (np.array(reward_ratio_pairs).T/np.sum(reward_ratio_pairs, axis=1)*difficulty_sum_reward_rate).T
                reward_ratio_pairs = np.round(reward_ratio_pairs[:difficulty_ratio_pair_num], 2).tolist()

            self.handles['actual_reward_prob'].setText(f'{reward_ratio_pairs}')
        except:
            pass


class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)

        # Use one canvas for all plots, which makes axis control more straightforward. HH20200729
        #  self.axes = fig.add_subplot(111)
        # self.axes = fig.subplots(2,1, sharex=True)
        # fig.tight_layout()

        gs = GridSpec(2, 10, wspace = 3, hspace = 0.1, bottom = 0.13, top = 0.85, left = 0.04, right = 0.98)
        self.ax1 = self.fig.add_subplot(gs[0, 0:7])
        self.ax2 = self.fig.add_subplot(gs[1, 0:7])
        self.ax3 = self.fig.add_subplot(gs[0:2, 7:])

        self.ax1.get_shared_x_axes().join(self.ax1, self.ax2)

        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        #self.plot()

    def update_plots(self, times, values, win_width):

        # --- Plotting ---
        self.plot_licks_and_rewards(times)
        (num_total_trials, num_finished_trials, num_rewarded_trials, for_eff_optimal, for_eff_optimal_actual,
                   early_licks_per_trial, double_dipping_per_trial) = self.plot_bias(times, values, win_width)
        slope, intercept, r_value = self.plot_matching(times, win_width)

        self_parent = self.parent().parent()
        valve_time = float(self_parent.handles['variables_subject']['ValveOpenTime_L'].text())
        setup_now = self_parent.handles['filter_setup'].currentText()

        # Lickport's relative lateral position
        aver_len = min(5, len(values['motor_position_lateral']))
        lat_pos_relative = np.median(values['motor_position_lateral'][-aver_len:]) - np.median(values['motor_position_lateral'][:aver_len])

        self_parent.handles['training_results'].setText(f'{setup_now}\t'
                                                        f'{num_total_trials}\t{num_finished_trials}\t'
                                                        f'{num_rewarded_trials}\t{for_eff_optimal*100:.1f}\t{for_eff_optimal_actual*100:.1f}\t'
                                                        f'{early_licks_per_trial:.2f}\t{double_dipping_per_trial:.2f}\t{intercept:.2f}\t{valve_time}\t{int(lat_pos_relative)}')

        pass

    # Moved minethedata() to App
    # def minethedata(self,data,session):
    #     times_old = data['times'].copy()
    #     values_old = data['values'].copy()
    #     times = dict()
    #     values = dict()
    #     days = dict()

    #     for key in times_old.keys():
    #         times_now  = times_old[key]
    #         order = np.argsort(times_now)
    #         times[key] = times_now[order]
    #         days[key] = np.asarray(times_now[order],dtype = 'datetime64[D]')
    #         if len(days[key])>0:
    #             needed = days[key] == np.datetime64(session)
    #         else:
    #             needed = []
    #         times[key] = times[key][needed]
    #         if key in values_old.keys():
    #             values_now = values_old[key]
    #             values[key] = values_now[order]
    #             values[key] = values[key][needed]


# =============================================================================
#         print(times_old)
#         print(times)
#         print(values_old)
#         print(values)
# =============================================================================
        # print(days)
        # return times, values

    def plot_licks_and_rewards(self, times): #, startime=None, endtime=None):

        # self.axes.cla()
        # ax = self.axes[0]
        ax = self.ax1
        ax.cla()

        # if type(data) == dict and len(data) > 0:
        # times, values = self.minethedata(data,session)  # Moved to update_plots

        # Moved to minethedata(). HH20200730
        # if startime == None:
        #     startime = np.min(times['alltimes'])
        # else:
        #     startime = np.max([np.datetime64(np.max(times['alltimes']) - startime),np.min(times['alltimes'])])
        # endtime = np.max(times['alltimes'])

        # for timeskey in times.keys():
        #     neededidx = (times[timeskey]>=startime) & (times[timeskey]<=endtime)
        #     times[timeskey]= times[timeskey][neededidx]
# =============================================================================
#             if  handles and handles['plot_timeback'].text().isnumeric():
#                 alltimes = []
#                 for timeskey in times.keys(): # finding endtime
#                    if len(alltimes) > 0:
#                        alltimes = pd.concat([alltimes,times[timeskey]])
#                    else:
#                        alltimes = times[timeskey]
#                 endtime = max(alltimes)
#                 #self.startime = endtime - int(handles['plot_timeback'].text())*np.timedelta64(1,'s')
#                 for timeskey in times.keys():
#                     timediffs = (times[timeskey] - endtime).to_numpy()
#                     neededidx = (timediffs/np.timedelta64(1,'s')+int(handles['plot_timeback'].text()))>0
#                     times[timeskey]= times[timeskey][neededidx]
#                   #  idxes[timeskey]= idxes[timeskey][neededidx]
#                 #print(neededidx )
# =============================================================================
        ax.cla()
        # ax.plot(times['trialstart'], np.zeros(len(times['trialstart']))+.5, 'b|', markersize = 150, label='TrialStart')
        # ax.plot(times['trialend'], np.zeros(len(times['trialend']))+.5, 'r|', markersize = 150)
        # ax.plot(times['GoCue'], np.zeros(len(times['GoCue']))+.5, 'g|', markersize = 100, label='GoCue')

        # Changed to show real trial END. HH
        ax.eventplot(times['trialstart'], lineoffsets=.5, linelengths=1.5, linewidth=0.6, color='b', label='TrialStart', alpha=0.5)
        ax.eventplot(times['GoCue'], lineoffsets=.5, linelengths=1, linewidth=0.6, color='g', label='GoCue', alpha=0.5)
        ax.eventplot(times['ITI_start'], lineoffsets=.5, linelengths=1.5, linewidth=0.6, color='r', label='TrialEnd(ITIStart)', alpha=0.5)

        ax.plot(times['lick_L'], np.zeros(len(times['lick_L'])), 'k|')
        ax.plot(times['lick_R'], np.zeros(len(times['lick_R']))+1, 'k|')
        ax.plot(times['choice_L'], np.zeros(len(times['choice_L']))+.1, 'go', markerfacecolor = (1, 1, 1, 1))
        ax.plot(times['choice_R'], np.zeros(len(times['choice_R']))+.9, 'go',markerfacecolor = (1, 1, 1, 1))
        ax.plot(times['reward_L'], np.zeros(len(times['reward_L']))+.2, 'go', markerfacecolor = (0, 1, 0, 1))
        ax.plot(times['reward_R'], np.zeros(len(times['reward_R']))+.8, 'go',markerfacecolor = (0, 1, 0, 1))
        ax.plot(times['autowater_L'], np.zeros(len(times['autowater_L']))+.7, 'go', markerfacecolor = (0, 0, 1, 1))
        #ax.plot(times['autowater_L'], np.zeros(len(times['autowater_L']))+.1, 'go', markerfacecolor = (0, 0, 1, 1))
        #ax.plot(times['autowater_R'], np.zeros(len(times['autowater_R']))+.9, 'go',markerfacecolor = (0, 0, 1, 1))

        if 'lick_M' in times.keys():
            ax.plot(times['lick_M'], np.zeros(len(times['lick_M']))+.5, 'k|')
            ax.plot(times['choice_M'], np.zeros(len(times['choice_M']))+.45, 'go',markerfacecolor = (1, 1, 1, 1))
            ax.plot(times['reward_M'], np.zeros(len(times['reward_M']))+.55, 'go', markerfacecolor = (0, 1, 0, 1))
            #ax.plot(times['autowater_M'], np.zeros(len(times['autowater_M']))+.45, 'go',markerfacecolor = (0, 0, 1, 1))

        # ax.set_title('Lick and reward history', fontsize=12)
        ax.set_yticks([0,1])
        ax.set_yticklabels(['L', 'R'])
        ax.set_ylim(-0.15, 1.15)
        # ax.set_xlim([startime, endtime])

        # ax.legend(bbox_to_anchor=(0., 1.02, .25, .102), ncol=3, loc=3, fontsize=8)
        ax.legend(loc='lower left', fontsize=8)
        ax.set_xticks([])

        # HH20211124 photostimulation indicators
        try:
            # ax.plot(times['EarlyITI'], np.zeros(len(times['EarlyITI']))+1.05, 'cs', markerfacecolor = 'c')
            ax.plot(times['laserITI'], np.zeros(len(times['laserITI']))+1.05, 'cs', markerfacecolor = 'c')
            ax.plot(times['laserGoCue'], np.zeros(len(times['laserGoCue']))+1.10, 'gs', markerfacecolor = 'g')
        except:
            pass


        #if  handles and handles['plot_timeback'].text().isnumeric():
            #ax.set_xlim(self.startime,endtime)
        self.draw()

    def plot_bias(self, times, values, win_width, causal=True): #, startime=None, endtime=None, numberofpoints = 10):

        # self.axes.cla()
        # ax = self.axes[1]
        ax = self.ax2
        ax.cla()

        # if type(data) == dict and len(data) > 0:
        # times, values = self.minethedata(data,session)

        # Moved to minethedata(). HH20200730
        # if startime == None:
        #     startime = np.min(times['alltimes'])
        # else:
        #     startime = np.max([np.datetime64(np.max(times['alltimes']) - startime),np.min(times['alltimes'])])

        # endtime = np.max(times['alltimes'])
# =============================================================================
#             ax.cla()
#             print(times['motor_position_rostrocaudal'])
#             print(values['motor_position_rostrocaudal'])
#             ax.plot(times['motor_position_rostrocaudal'], values['motor_position_rostrocaudal'], 'ko',label = 'RC')
#             ax.plot(times['motor_position_lateral'], values['motor_position_lateral'], 'ro',label = 'Lat')
# =============================================================================
        #print(startime , endtime)
        #lick_left_num = np.zeros(len(win_centers))
        #lick_right_num  = np.zeros(len(win_centers))

        numberofpoints = int(np.ptp(times['alltimes']) / win_width)
        win_centers = pd.date_range(start = np.min(times['alltimes']), end = np.max(times['alltimes']), periods = numberofpoints*10)  # Stepsize = window width / 10 (hardcoded)

        choice_left_num = np.zeros(len(win_centers))
        choice_right_num = np.zeros(len(win_centers))
        reward_left_num = np.zeros(len(win_centers))
        reward_right_num = np.zeros(len(win_centers))
        finish_trials = np.zeros(len(win_centers))
        all_trials = np.zeros(len(win_centers))

        if_3lp = 'lick_M' in times.keys() and np.nansum(values['reward_p_M']) > 0  # Better way of determining whether it's a 3lp task

        if if_3lp: #'lick_M' in times.keys():
            # lick_middle_num  = np.zeros(len(win_centers))
            choice_middle_num = np.zeros(len(win_centers))

        for idx,timenow in enumerate(win_centers):
            timenow = np.datetime64(timenow)

            #lick_left_num[idx] = sum((timenow+win_width > times['lick_L']) & (timenow-win_width<times['lick_L']))
            #lick_right_num[idx] = sum((timenow+win_width > times['lick_R']) & (timenow-win_width<times['lick_R']))

            # choice_left_num[idx] = sum((timenow+win_width > times['choice_L']) & (timenow-win_width<times['choice_L']))
            # choice_right_num[idx] = sum((timenow+win_width > times['choice_R']) & (timenow-win_width<times['choice_R']))

            if causal:
                # Causal sliding window (only trials before timenow contribute)
                choice_left_num[idx] = sum((timenow - win_width < times['choice_L']) & (times['choice_L'] < timenow))
                choice_right_num[idx] = sum((timenow - win_width < times['choice_R']) & (times['choice_R'] < timenow))
                reward_left_num[idx] = sum((timenow - win_width < times['reward_L']) & (times['reward_L'] < timenow))
                reward_right_num[idx] = sum((timenow - win_width < times['reward_R']) & (times['reward_R'] < timenow))
            else:
                # Non-causal
                choice_left_num[idx] = sum((timenow - win_width/2 < times['choice_L']) & (times['choice_L'] < timenow + win_width/2))
                choice_right_num[idx] = sum((timenow - win_width/2 < times['choice_R']) & (times['choice_R'] < timenow + win_width/2))
                reward_left_num[idx] = sum((timenow - win_width < times['reward_L']) & (times['reward_L'] < timenow))
                reward_right_num[idx] = sum((timenow - win_width < times['reward_R']) & (times['reward_R'] < timenow))

            if if_3lp: #'lick_M' in times.keys():
                # lick_middle_num[idx] = sum((timenow+win_width > times['lick_M']) & (timenow-win_width<times['lick_M']))
                # choice_middle_num[idx] = sum((timenow+win_width > times['choice_M']) & (timenow-win_width<times['choice_M']))

                if causal:
                    choice_middle_num[idx] = sum((timenow - win_width < times['choice_M']) & (times['choice_M'] < timenow))
                else:
                    choice_middle_num[idx] = sum((timenow - win_width/2 < times['choice_M']) & (times['choice_M'] < timenow + win_width/2))

            # Finish rate
            finish_trials[idx] = (sum((timenow - win_width < times['choice_L']) & (times['choice_L'] < timenow)) +
                                  sum((timenow - win_width < times['choice_R']) & (times['choice_R'] < timenow)) +
                                  sum((timenow - win_width < times['choice_M']) & (times['choice_M'] < timenow)))
            all_trials[idx] = sum((timenow - win_width < times['trialstart']) & (times['trialstart'] < timenow))


        # Show the window in ax1
        if causal:
            self.ax1.plot([np.max(times['alltimes']) - win_width, np.max(times['alltimes'])], [-0.1] * 2, color='k', lw=4)
        else:
            self.ax1.plot([np.max(times['alltimes']) - win_width/2, np.max(times['alltimes'])+ win_width/2], [-0.1] * 2, color='k', lw=4)

        # ax.cla()
        if if_3lp: # 'lick_M' in times.keys():
            # There's no need for idxes any more. HH20200730
            # idxes = np.where(times['p_reward_ratio'])

            golden_reward_R_1 = values['reward_p_L']/(values['reward_p_L']+values['reward_p_R']+values['reward_p_M'])
            golden_reward_R_2 = (values['reward_p_L']+values['reward_p_M'])/(values['reward_p_L']+values['reward_p_R']+values['reward_p_M'])

            choice_sum_num = choice_right_num+choice_left_num+choice_middle_num

            #ax.plot(win_centers, bias_lick_R, 'k-',label = 'Lick bias')
            #ax.plot(win_centers, bias_reward_R, 'g-',label = 'choice bias')
            ax.stackplot(win_centers,  choice_left_num/choice_sum_num ,  choice_middle_num/choice_sum_num ,  choice_right_num/choice_sum_num ,colors=['r','g','b'], alpha=0.4 )
            #ax.plot(win_centers, bias_reward_R_1, 'g-',label = 'choice bias')
            #ax.plot(win_centers, bias_reward_R_2, 'g-',label = 'choice bias')

            ax.plot(times['reward_p_R'], values['reward_p_R'], 'b-',label = 'R') # 'Reward probability Right')
            ax.plot(times['reward_p_M'], values['reward_p_M'], 'g-',label = 'M') #'Reward probability Middle')
            ax.plot(times['reward_p_L'], values['reward_p_L'], 'r-',label = 'L') #'Reward probability Left')
            ax.plot(times['p_reward_ratio'], golden_reward_R_1, 'y-') #,label = 'Reward ratio')
            ax.plot(times['p_reward_ratio'], golden_reward_R_2, 'y-') #,label = 'Reward ratio')
            ax.plot(win_centers, finish_trials / all_trials, 'c', lw=0.5, label='finish ratio')
            #ax.plot(times['p_reward_ratio'], values['p_reward_ratio'], 'y-',label = 'Reward ratio')
            ax.legend(loc='lower left', fontsize=8)
            ax.set_ylim(-0.05, 1.05)
            # vals = ax.get_yticks()
            # ax.set_yticklabels(['{:.0%}'.format(x) for x in vals])
        else:  # 2 lick port
            #bias_lick_R = lick_right_num/(lick_right_num+lick_left_num)
            bias_reward_R = reward_right_num/(reward_right_num+reward_left_num)
            bias_choice_R = choice_right_num/(choice_right_num+choice_left_num)
            #ax.plot(win_centers, bias_lick_R, 'k-',label = 'Lick bias')
            # idxes = times['p_reward_ratio'] > startime
            ax.plot(times['reward_p_L'], values['reward_p_L'], 'r-', lw=0.7, label = 'p_L')
            ax.plot(times['reward_p_R'], values['reward_p_R'], 'b-', lw=0.7, label = 'p_R')
            ax.plot(times['p_reward_ratio'], values['p_reward_ratio'], 'y-', label = 'p_R_frac')
            ax.plot(win_centers, bias_reward_R, 'g-', lw=1, label = 'reward_frac')
            ax.plot(win_centers, bias_choice_R, 'k-', lw=2, label = 'choice_frac')
            ax.plot(win_centers, finish_trials / all_trials, 'c', lw=0.5, label='finish ratio')
            ax.legend(loc='lower left', fontsize=8)
            ax.set_yticks([0,1])
            ax.set_yticklabels(['L', 'R'])
            ax.set_ylim(-.1,1.1)

            # Plot reward refills to confirm
            # refill_L = values['random_number_L'] <= values['reward_p_L']
            # refill_R = values['random_number_R'] <= values['reward_p_R']
            # ax.eventplot(times['reward_p_L'][refill_L], colors='g', lineoffsets=-0.1, linelengths=0.1, linewidth=2)
            # ax.eventplot(times['reward_p_R'][refill_R], colors='g', lineoffsets=1.1, linelengths=0.1, linewidth=2)

        # Trial numbers info
        num_total_trials = times['trialstart'].size
        if if_3lp:
            num_finished_trials = times['choice_L'].size + times['choice_R'].size + times['choice_M'].size
            num_rewarded_trials = times['reward_L'].size + times['reward_R'].size + times['reward_M'].size
        else:
            num_finished_trials = times['choice_L'].size + times['choice_R'].size
            num_rewarded_trials_L = times['reward_L'].size
            num_rewarded_trials_R = times['reward_R'].size
            num_rewarded_trials = num_rewarded_trials_L + num_rewarded_trials_R

        # Double dipping
        if 'Double_dipped' in times.keys():
            num_double_dipping = times['Double_dipped'].size
            double_dipping_per_trial = num_double_dipping / num_finished_trials if num_finished_trials else np.nan
        else:
            num_double_dipping = np.nan
            double_dipping_per_trial = np.nan

        # Early licks (there can be multiple early licks per trial)
        if 'early_licks' in times.keys() and num_finished_trials > 0:
            early_licks_per_trial = times['early_licks'].size / num_finished_trials
        else:
            early_licks_per_trial = np.nan

        reward_rate = num_rewarded_trials / num_finished_trials if num_finished_trials else np.nan

        if not if_3lp:
            if 'random_number_L' in values.keys():
                for_eff_classic, for_eff_optimal, for_eff_optimal_actual = self._foraging_eff(reward_rate,
                                                                      values['reward_p_L'],
                                                                      values['reward_p_R'],
                                                                      values['random_number_L'],
                                                                      values['random_number_R'])
            else:
                for_eff_classic, for_eff_optimal, for_eff_optimal_actual = self._foraging_eff(reward_rate,
                                                      values['reward_p_L'],
                                                      values['reward_p_R'])

        else:
            for_eff_classic, for_eff_optimal, for_eff_optimal_actual = [np.nan] * 3  # Not well-defined for 3lp (so far)

        self.ax1.set_title(f'Total={num_total_trials}, finished={num_finished_trials}({num_finished_trials/num_total_trials:.1%}). '
                     f'Rewarded={num_rewarded_trials}({num_rewarded_trials_L}+{num_rewarded_trials_R}, {reward_rate:.1%}). '
                     f'Efficiency: classic = {for_eff_classic:.1%}, optimal(actual) = {for_eff_optimal:.1%}({for_eff_optimal_actual:.1%})\n'
                     f'Early lick pulishment per finished trial = {early_licks_per_trial:.2f}. Double-dippings per finished trial = {double_dipping_per_trial:.2f}', fontsize=10)

        # ax.set_title('Lick and reward bias')
        self.draw()

        # === Automatic block control using the current choice ratio ===
        if not if_3lp:
            subject_variables = self.parent().parent().variables['subject']
            subject_handles = self.parent().parent().handles['variables_subject']
            auto_block_switch_type = subject_variables['auto_block_switch_type']
            auto_block_switch_threshold = subject_variables['auto_block_switch_threshold']
            auto_block_switch_points = subject_variables['auto_block_switch_points']

            # Get the current side
            p_reward_ratio = values['p_reward_ratio'][~np.isnan(values['p_reward_ratio'])]
            if p_reward_ratio[-1] == 0.5:
                self.success_switch_now = True
                self.success_switch_once = True
            else:
                idx_now = len(p_reward_ratio)
                if len(np.where(np.diff(p_reward_ratio))[0]):
                    idx_last_switch = np.where(np.diff(p_reward_ratio))[0][-1]
                else:
                    idx_last_switch = 0

                if idx_now - idx_last_switch < 5 or not hasattr(self, 'success_switch_now'):  # Keep false immediately after block transition
                    self.success_switch_now = False
                    self.success_switch_once = False
                else:
                    if not self.success_switch_once and self.success_switch_now:
                        self.success_switch_once = True

                    recent_choice = bias_choice_R[-auto_block_switch_points:]
                    if p_reward_ratio[-1] > 0.5:  # Rightward block
                        self.success_switch_now = np.all(recent_choice >= auto_block_switch_threshold)
                    else:
                        self.success_switch_now = np.all(recent_choice <= 1 - auto_block_switch_threshold)

            # Always show success switch
            # tmpstr= f'(cached {self.parent().parent().cache_auto_train_min_rewarded_trial_num})' if auto_block_switch_type == 1 else ''
            tmpstr= 'is on the correct side now' if auto_block_switch_type == 1 else 'has been on the correct side'
            if not auto_block_switch_type or 'uncoupled' in self.handles['filter_experiment'].currentText():
                self.parent().parent().handles['success_switched'].setText('')
            else:
                actual_sucess_flag = self.success_switch_now if auto_block_switch_type == 1 else self.success_switch_once
                if actual_sucess_flag:
                    subject_handles['auto_train_min_rewarded_trial_num'].setText('0')
                    self.parent().parent().handles['success_switched'].setText(f'Behavior {tmpstr}? YES!!')
                else:
                    subject_handles['auto_train_min_rewarded_trial_num'].setText('999')
                    self.parent().parent().handles['success_switched'].setText(f'Behavior {tmpstr}? NO...')

                if not hasattr(self, 'last_success_switch'):
                    self.last_success_switch = -100

                # Save parameters only when the success flag changed
                if actual_sucess_flag != self.last_success_switch:
                    self.parent().parent().save_parameters()
                self.last_success_switch = actual_sucess_flag
                # self.parent().parent().cache_auto_train_min_rewarded_trial_num = real_cached_min_reward # Really restore the cached value

        return (num_total_trials, num_finished_trials, num_rewarded_trials, for_eff_optimal, for_eff_optimal_actual,
                   early_licks_per_trial, double_dipping_per_trial)


    def plot_matching(self, times, win_width):
        # ========== Choice fraction vs Reward fraction (only lickport R and lickport L pairswise matching) =======
        ax = self.ax3
        ax.cla()

        # Generate sliding windows for matching plot
        num_of_steps_per_sliding_win_width = 5
        numberofpoints = int(np.ptp(times['alltimes']) / win_width)
        win_centers = pd.date_range(start = np.min(times['alltimes']), end = np.max(times['alltimes']),
                                    periods = numberofpoints * num_of_steps_per_sliding_win_width)

        choice_R_frac = np.empty(len(win_centers))
        choice_R_frac[:] = np.nan
        reward_R_frac = choice_R_frac.copy()
        choice_R_log_ratio = choice_R_frac.copy()
        reward_R_log_ratio = choice_R_frac.copy()

        for idx,timenow in enumerate(win_centers):
            timenow = np.datetime64(timenow)
            choice_R = sum((timenow - win_width/2 < times['choice_R']) & (times['choice_R'] < timenow + win_width/2))
            choice_L =  sum((timenow - win_width/2 < times['choice_L']) & (times['choice_L'] < timenow + win_width/2))
            reward_R = sum((timenow - win_width/2 < times['reward_R']) & (times['reward_R'] < timenow + win_width/2))
            reward_L =  sum((timenow - win_width/2 < times['reward_L']) & (times['reward_L'] < timenow + win_width/2))

            if choice_R + choice_L and reward_R + reward_L:
                choice_R_frac[idx] = choice_R / (choice_R + choice_L)
                reward_R_frac[idx] = reward_R / (reward_R + reward_L)

            if choice_R and choice_L and reward_R and reward_L:
                choice_R_log_ratio[idx] = np.log(choice_R / choice_L)
                reward_R_log_ratio[idx] = np.log(reward_R / reward_L)

        # -- Plot fractions --
        # ax.plot(reward_R_frac, choice_R_frac, 'ko')
        # ax.plot([0, 1], [0,1], 'k--', lw=0.5)
        # ax.set(xlabel=f'Reward_R fraction (win_width = {win_width/np.timedelta64(1,"s"):.0f} s)',
        #         ylabel='Choice_R fraction')

        # -- Plot log ratios --
        ax.plot(reward_R_log_ratio, choice_R_log_ratio, 'ko')
        max_range = max(np.abs(ax.get_xlim()).max(), np.abs(ax.get_ylim()).max())
        ax.plot([-max_range, max_range], [-max_range, max_range], 'k--', lw=1)
        ax.set(xlabel=f'Log Reward_R/L (win = {win_width/np.timedelta64(1,"s"):.0f} s, dots/win = {num_of_steps_per_sliding_win_width})',
                ylabel='Log Choice_R/L')

        # -- Do linear fitting in log_ratio space --
        try:
            non_nan = ~np.isnan(reward_R_log_ratio) & ~np.isnan(choice_R_log_ratio)
            x = reward_R_log_ratio[non_nan]
            y = choice_R_log_ratio[non_nan]
            slope, intercept, r_value, p_value, _ = stats.linregress(x, y)

            # xx = np.linspace(0, 1, 100)
            # yy = (xx ** slope) / (xx ** slope + np.exp(intercept) * ((1 - xx) ** slope))
            xx = x
            yy = x * slope + intercept

            ax.plot(xx, yy, 'r', label=f'r = {r_value:.3f}\np = {p_value:.2e}')
            ax.set_title(f'Matching slope = {slope:.2f}, bias_R = {intercept:.2f}', fontsize=12)
            ax.set_xlim(-0.05, 1.05)
            ax.legend(loc='lower right', fontsize=10)
            ax.axis('equal')
        except:
            slope, intercept, r_value = [np.nan] * 3
            pass

        self.draw()
        return slope, intercept, r_value


    def _foraging_eff(self, reward_rate, p_Ls, p_Rs, random_number_L=None, random_number_R=None):  # Calculate foraging efficiency (only for 2lp)
        # Classic method (Corrado2005)
        for_eff_classic = reward_rate / (np.nanmean(p_Ls + p_Rs))

        # --- Optimal-aver (there is no simple way of only considering finished trials in the online script,
        # so here I assume all the trials are not ignored)
        p_stars = np.zeros_like(p_Ls)
        for i, (p_L, p_R) in enumerate(zip(p_Ls, p_Rs)):   # Sum over all ps
            p_max = np.max([p_L, p_R])
            p_min = np.min([p_L, p_R])
            if p_min > 0:
                m_star = np.floor(np.log(1-p_max)/np.log(1-p_min))
                p_stars[i] = p_max + (1-(1-p_min)**(m_star + 1)-p_max**2)/(m_star+1)
            else:
                p_stars[i] = p_max
        for_eff_optimal = reward_rate / np.nanmean(p_stars)

        if random_number_L is None:
            return for_eff_classic, for_eff_optimal, np.nan

        # --- Optimal-actual (uses the actual random numbers by simulation)
        block_trans = np.where(np.diff(np.hstack([np.inf, p_Ls, np.inf])))[0].tolist()
        reward_refills = [p_Ls >= random_number_L, p_Rs >= random_number_R]
        reward_optimal_actual = 0
        # Generate optimal choice pattern
        for b_start, b_end in zip(block_trans[:-1], block_trans[1:]):
            p_max = np.max([p_Ls[b_start], p_Rs[b_start]])
            p_min = np.min([p_Ls[b_start], p_Rs[b_start]])
            side_max = np.argmax([p_Ls[b_start], p_Rs[b_start]])

            reward_refill = np.vstack([reward_refills[1 - side_max][b_start:b_end],
                             reward_refills[side_max][b_start:b_end]]).astype(int)  # Max = 1, Min = 0

            # Get choice pattern
            if p_min > 0:
                m_star = np.floor(np.log(1-p_max)/np.log(1-p_min))
                this_choice = np.array((([1]*int(m_star)+[0]) * 10000) [:b_end-b_start])
            else:
                this_choice = np.array([1] * (b_end-b_start))

            # Do simulation
            reward_remain = [0,0]
            for t in range(b_end - b_start):
                reward_available = reward_remain | reward_refill[:, t]
                reward_optimal_actual += reward_available[this_choice[t]]
                reward_remain = reward_available.copy()
                reward_remain[this_choice[t]] = 0

            if reward_optimal_actual:
                for_eff_optimal_actual = reward_rate / (reward_optimal_actual / len(p_Ls))
            else:
                for_eff_optimal_actual = np.nan

        return for_eff_classic, for_eff_optimal, for_eff_optimal_actual

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
