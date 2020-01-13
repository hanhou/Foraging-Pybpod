import behavior_rozmar as behavior_rozmar
import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton,  QLineEdit, QCheckBox, QHBoxLayout, QGroupBox, QDialog, QVBoxLayout, QGridLayout, QComboBox, QSizePolicy, qApp, QLabel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer, Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import re
import time as time
from datetime import datetime
import json
import threading
try:
    import zaber.serial as zaber_serial
except:
    pass
print('started')
paths = ['/home/rozmar/Data/Behavior/Behavior_rigs/Tower-2','C:\\Users\\labadmin\\Documents\\Pybpod\\Projects']
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
        self.left = 10
        self.top = 10
        self.width = 1024
        self.height = 768
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
        self.variables_to_display = ['ValveOpenTime_L',
                                     'ValveOpenTime_R',
                                     'ValveOpenTime_M',
                                     'Trialnumber_in_block',
                                     'Trialnumber_in_block_max',
                                     'Trialnumber_in_block_min',
                                     'block_start_with_bias_check',
                                     'block_number',
                                     'difficulty_sum_reward_rate',
                                     'difficulty_ratio_pair_num',
                                     'delay',
                                     'delay_min',
                                     'delay_max',
                                     'response_time',
                                     'iti', 
                                     'iti_min', # minimum ITI
                                     'iti_max',
                                     'increase_ITI_on_ignore_trials',
                                     'auto_water',
                                     'auto_water_time_multiplier',
                                     'auto_water_min_unrewarder_trials_in_a_row',
                                     'auto_water_min_ignored_trials_in_a_row',
                                     'auto_train_min_rewarded_trial_num',
                                     'early_lick_punishment',
                                     'reward_rate_family',
                                     'lickport_number',
                                     ]
        free_water = {
                      'difficulty_ratio_pair_num' : 0,
                      'response_time' : 2.,
                      'increase_ITI_on_ignore_trials' : False, 
                      'block_start_with_bias_check' : False,
                      'auto_water' : True,
                      'auto_water_min_unrewarder_trials_in_a_row' : 3,
                      'auto_water_min_ignored_trials_in_a_row' : 1,
                      'early_lick_punishment' : False,
                      }
        pretraining = {
                'Trialnumber_in_block' : 1,
                'Trialnumber_in_block_min' : 0,
                'Trialnumber_in_block_max' : 0,
                'block_start_with_bias_check' : False,
                'block_number' : 500,
                'difficulty_sum_reward_rate' : 1,
                'difficulty_ratio_pair_num' : 1,
                'reward_rate_family' : 3,
                'response_time' : 2.,
                'auto_train_min_rewarded_trial_num' : 4,
                'early_lick_punishment' : False,
                }
        pretraining_early_lick = {
                'Trialnumber_in_block' : 1,
                'Trialnumber_in_block_min' : 0,
                'Trialnumber_in_block_max' : 0,
                'block_start_with_bias_check' : False,
                'block_number' : 500,
                'difficulty_sum_reward_rate' : 1,
                'difficulty_ratio_pair_num' : 1,
                'delay' : 1,
                'delay_min' : .5,
                'delay_max' : 3.,
                'reward_rate_family' : 3,
                'response_time' : 1.,
                'auto_train_min_rewarded_trial_num' : 4,
                'early_lick_punishment' : True,
                }
        full_task_2_lickport = {
                'Trialnumber_in_block' : 30,
                'Trialnumber_in_block_min' : 50,
                'Trialnumber_in_block_max' : 200,
                'block_start_with_bias_check' : True,
                'block_number' : 100,
                'difficulty_sum_reward_rate' : .45,
                'difficulty_ratio_pair_num' : 3,
                'reward_rate_family' : 1,
                'delay' : 1,
                'delay_min' : .5,
                'delay_max' : 3.,
                'response_time' : .5,
                'iti' : 3, 
                'iti_min' : .5, # minimum ITI
                'iti_max': 10.,
                'increase_ITI_on_ignore_trials' : True,
                'auto_water' : False,
                'early_lick_punishment' : True,
                                     }
        full_task_3_lickport = {
                'Trialnumber_in_block' : 30,
                'Trialnumber_in_block_min' : 80,
                'Trialnumber_in_block_max' : 200,
                'block_start_with_bias_check' : True,
                'block_number' : 100,
                'difficulty_sum_reward_rate' : .75,
                'difficulty_ratio_pair_num' : 1,
                'reward_rate_family' : 1,
                'delay' : 1,
                'delay_min' : .5,
                'delay_max' : 3.,
                'response_time' : .5,
                'iti' : 3, 
                'iti_min' : .5, # minimum ITI
                'iti_max': 10.,
                'increase_ITI_on_ignore_trials' : True,
                'auto_water' : False,
                'early_lick_punishment' : True,
                                     }
        
        self.preset_variables = dict()
        self.preset_variables['0 - free water'] = free_water
        self.preset_variables['1 - pretraining'] = pretraining
        self.preset_variables['2 - pretraining + early lick punishment'] = pretraining_early_lick
        self.preset_variables['3 - full task (2 lickports)'] = full_task_2_lickport
        self.preset_variables['4 - full task (3 lickports)'] = full_task_3_lickport
        
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
        qApp.processEvents()
        selected = dict()
        filterorder = ['project','experiment','setup','subject']
        for filternow in filterorder:
            filterstring = str(self.handles['filter_'+filternow].currentText())
            if not re.findall('all',filterstring):
                selected[filternow] = filterstring
            else:
                selected[filternow] = None
        if self.pickle_write_thread == None or not self.pickle_write_thread.isAlive():
            self.pickle_write_thread = threading.Thread(target=behavior_rozmar.save_pickles_for_online_analysis, args=(self.dirs['projectdir'], selected['project'], selected['experiment'], selected['setup'], True))
            self.pickle_write_thread.daemon = True                            # Daemonize thread
            self.pickle_write_thread.start() 
# =============================================================================
#         behavior_rozmar.save_pickles_for_online_analysis(projectdir = self.dirs['projectdir'],
#                                                 projectnames_needed = selected['project'],
#                                                 experimentnames_needed = selected['experiment'],
#                                                 setupnames_needed = selected['setup'],
#                                                 load_only_last_day = True)
# =============================================================================
            try:
                self.data = behavior_rozmar.load_pickles_for_online_analysis(projectdir = self.dirs['projectdir'],
                                                        projectnames_needed = selected['project'],
                                                        experimentnames_needed = selected['experiment'],
                                                        setupnames_needed = selected['setup'],
                                                        subjectnames_needed = selected['subject'],
                                                        load_only_last_day = True)
                #Update motor position values from previous csv files
                rc_times  = self.data['times']['motor_position_rostrocaudal']
                order = np.argsort(rc_times)
                rc_times  = rc_times[order]
                #lat_times  = self.data['times']['motor_position_lateral'][order]
                lat_values = self.data['values']['motor_position_lateral'][order]
                rc_values = self.data['values']['motor_position_rostrocaudal'][order]
                
                bigdiff_idxes = np.concatenate([np.diff(rc_times)>np.timedelta64(6,'h'),[True]])
                uniquedays_str = np.asarray(np.asarray(rc_times[bigdiff_idxes],dtype = 'datetime64[D]'),dtype = str) 
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
                self.filterthedata()
            except:
                print('couldn\'t load the data..')
                self.handles['load_the_data'].setText('Load the data')
                self.handles['load_the_data'].setStyleSheet('QPushButton {color: black;}')
                self.updateUI()
        #print('data reloaded')
        #print(time.perf_counter())
    
    @pyqtSlot()    
    def reloadthedata(self):
        #self.data = behavior_rozmar.loadcsvdata(self.data, projectdir = self.dirs['projectdir'])
        self.loadthedata()
        #self.filterthedata()
        print('data reloaded')
        print(time.perf_counter())  
        
    def auto_load_data(self):
        if self.handles['plot_autorefresh'].isChecked():
            self.timer.start()
        else:
            self.timer.stop()
            
    def filterthedata(self,lastselected = ' '):
        if lastselected != ' ':
            print('filterthedata')
            print(lastselected)
            self.updateUI_dirstructure(lastselected)
        if type(self.data) == dict:
            self.data_now = self.data.copy()
            if len(self.data_now) > 0:
                endtime = max(self.data_now['times']['alltimes'])
                if  self.handles['plot_timeback'].text().isnumeric():
                    startime = pd.to_timedelta(int(self.handles['plot_timeback'].text()),'s')
                else:
                    startime = None#min(self.data_now['times']['alltimes'])
                if  self.handles['plot_timeback_runningwindow'].text().isnumeric(): # determining averaging window size
                    numberofpoints = int(self.handles['plot_timeback_runningwindow'].text())
                else:
                    numberofpoints = 10    
                self.handles['axes1'].plot_licks_and_rewards(self.data_now,startime,endtime,self.handles['select_session'].currentText())
                self.handles['axes2'].plot_bias(self.data_now,startime,endtime,numberofpoints,self.handles['select_session'].currentText())
                print('plotting done')
                
        if lastselected == 'filter_subject'  :
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
        
        self.handles['loadparams'] = QPushButton('Load parameters')
        self.handles['loadparams'].setFocusPolicy(Qt.NoFocus)
        self.handles['loadparams'].clicked.connect(self.load_parameters)
        
        
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
        layout.addWidget(self.handles['load_the_data'],0,4)
        #layout.addWidget(self.handles['filter_experimenter'],0,5)
        layout.addWidget(self.handles['select_session'],0,5)
        layout.addWidget(self.handles['loadparams'],0,6)
        layout.addWidget(self.handles['set_lickport_position'],0,7)
        self.horizontalGroupBox_filter.setLayout(layout)
        
        self.horizontalGroupBox_axes = QGroupBox("plots")
        layout_axes = QGridLayout()
        self.handles['axes1'] = PlotCanvas(self, width=5, height=4)
        self.handles['axes2'] = PlotCanvas(self, width=5, height=4)
        layout_axes.addWidget(self.handles['axes1'],0,0)
        layout_axes.addWidget(self.handles['axes2'],1,0)
        self.horizontalGroupBox_axes.setLayout(layout_axes)
        
        self.horizontalGroupBox_plot_settings = QGroupBox("Plot settings")
        layout_plot_settings = QGridLayout()
        self.handles['plot_timeback'] = QLineEdit(self)
        self.handles['plot_timeback'].setText('Time back to plot (seconds)')
        self.handles['plot_timeback'].returnPressed.connect(self.filterthedata)
        layout_plot_settings.addWidget(self.handles['plot_timeback'],0,0)
        
        self.handles['plot_timeback_runningwindow'] = QLineEdit(self)
        self.handles['plot_timeback_runningwindow'].setText('Number of segments in bias plot (integer)')
        self.handles['plot_timeback_runningwindow'].returnPressed.connect(self.filterthedata)
        layout_plot_settings.addWidget(self.handles['plot_timeback_runningwindow'],0,1)
        
        self.handles['plot_autorefresh'] = QCheckBox(self)
        self.handles['plot_autorefresh'].setText('auto refresh data')
        layout_plot_settings.addWidget(self.handles['plot_autorefresh'],0,2)
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

    def load_parameters(self):
        maxcol = 4 # number of columns
        project_now = self.handles['filter_project'].currentText()
        experiment_now = self.handles['filter_experiment'].currentText()
        setup_now = self.handles['filter_setup'].currentText()
        subject_now = self.handles['filter_subject'].currentText()
        if project_now != 'all projects' and experiment_now != 'all experiments' and setup_now != 'all setups' and subject_now != 'all subjects':
            subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,'variables.json')
            setup_var_file = os.path.join(defpath,project_now,'experiments',experiment_now,'setups',setup_now,'variables.json')
            with open(subject_var_file) as json_file:
                variables_subject = json.load(json_file)
            with open(setup_var_file) as json_file:
                variables_setup = json.load(json_file)
            if self.variables is None:
                layout = QGridLayout()
                self.horizontalGroupBox_preset_variables = QGroupBox("Preset variables")
                self.horizontalGroupBox_variables_setup = QGroupBox("Setup: "+setup_now)
                self.horizontalGroupBox_variables_subject = QGroupBox("Subject: "+subject_now)
                layout.addWidget(self.horizontalGroupBox_preset_variables ,0,0)
                layout.addWidget(self.horizontalGroupBox_variables_setup ,1,0)
                layout.addWidget(self.horizontalGroupBox_variables_subject ,2,0)
                self.horizontalGroupBox_variables.setLayout(layout)
                
                layout_preset = QGridLayout()
                self.handles['presetbuttons'] = dict()
                for idx,key in enumerate(self.preset_variables.keys()):
                    self.handles['presetbuttons'][key] = QPushButton(key)
                    self.handles['presetbuttons'][key].setFocusPolicy(Qt.NoFocus)
                    self.handles['presetbuttons'][key].clicked.connect(lambda state, x=key: self.preload_parameters(x))
                    layout_preset.addWidget(self.handles['presetbuttons'][key] ,0,idx)
                self.horizontalGroupBox_preset_variables.setLayout(layout_preset)    
                
                layout_setup = QGridLayout()
                row = 0
                col = -1
                self.handles['variables_setup']=dict()
                self.handles['variables_subject']=dict()
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
                layout_subject = QGridLayout()
                row = 0
                col = -1
                for idx,key in enumerate(variables_subject.keys()):
                    if key in self.variables_to_display:
                        col +=1
                        if col > maxcol*2:
                            col = 0
                            row += 1
                        layout_subject.addWidget(QLabel(key+':') ,row,col)
                        col +=1
                        self.handles['variables_subject'][key] =  QLineEdit(str(variables_subject[key]))
                        self.handles['variables_subject'][key].returnPressed.connect(self.save_parameters)
                        self.handles['variables_subject'][key].textChanged.connect(self.check_parameters)
                        layout_subject.addWidget(self.handles['variables_subject'][key] ,row,col)
                self.horizontalGroupBox_variables_subject.setLayout(layout_subject)
                self.variables=dict()
            else:
                self.horizontalGroupBox_variables_setup.setTitle("Setup: "+setup_now)
                self.horizontalGroupBox_variables_subject.setTitle("Subject: "+subject_now)
                for key in self.handles['variables_subject'].keys():
                    self.handles['variables_subject'][key].setText(str(variables_subject[key]))
                for key in self.handles['variables_setup'].keys():
                    self.handles['variables_setup'][key].setText(str(variables_setup[key]))
            self.variables['subject'] = variables_subject
            self.variables['setup'] = variables_setup
            self.variables['subject_file'] = subject_var_file
            self.variables['setup_file'] = setup_var_file
    def check_parameters(self):
        project_now = self.handles['filter_project'].currentText()
        experiment_now = self.handles['filter_experiment'].currentText()
        setup_now = self.handles['filter_setup'].currentText()
        subject_now = self.handles['filter_subject'].currentText()
        subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,'variables.json')
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
                if valuenow == self.variables[dicttext][key]:
                    self.handles['variables_'+dicttext][key].setStyleSheet('QLineEdit {color: black;}')
                else:
                    self.handles['variables_'+dicttext][key].setStyleSheet('QLineEdit {color: red;}')
        qApp.processEvents()
    def save_parameters(self):
        project_now = self.handles['filter_project'].currentText()
        experiment_now = self.handles['filter_experiment'].currentText()
        setup_now = self.handles['filter_setup'].currentText()
        subject_now = self.handles['filter_subject'].currentText()
        subject_var_file = os.path.join(defpath,project_now,'subjects',subject_now,'variables.json')
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
        with open(self.variables['setup_file'], 'w') as outfile:
            json.dump(self.variables['setup'], outfile)
        with open(self.variables['subject_file'], 'w') as outfile:
            json.dump(self.variables['subject'], outfile)
        self.load_parameters()
        self.check_parameters()
        
    def preload_parameters(self,key):
        presetvars = self.preset_variables[key]
        for dicttext in ['subject','setup']:
            for key in self.handles['variables_'+dicttext].keys():
                if key in presetvars.keys():
                    self.handles['variables_'+dicttext][key].setText(str(presetvars[key]))        
        self.check_parameters()
            
class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        #self.plot()

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
                needed = days[key] == np.datetime64(session)
            else:
                needed = []
            times[key] = times[key][needed]
            if key in values_old.keys():
                values_now = values_old[key]
                values[key] = values_now[order]
                values[key] = values[key][needed]
        
# =============================================================================
#         print(times_old)
#         print(times)
#         print(values_old)
#         print(values)
# =============================================================================
        print(days)
        return times, values
    
    def plot_licks_and_rewards(self,data = [],startime=None,endtime=None,session = None):
        self.axes.cla()
        if type(data) == dict and len(data) > 0:
            times, values = self.minethedata(data,session)
            if startime == None:
                startime = np.min(times['alltimes'])
            else:
                startime = np.max([np.datetime64(np.max(times['alltimes']) - startime),np.min(times['alltimes'])])
            endtime = np.max(times['alltimes'])
            for timeskey in times.keys():
            
                neededidx = (times[timeskey]>=startime) & (times[timeskey]<=endtime)
                times[timeskey]= times[timeskey][neededidx]
# =============================================================================
#             if  handles and handles['plot_timeback'].text().isnumeric():
#                 alltimes = []
#                 for timeskey in times.keys(): # finding endtime
#                    if len(alltimes) > 0:
#                        alltimes = pd.concat([alltimes,times[timeskey]])
#                    else:
#                        alltimes = times[timeskey]
#                 endtime = max(alltimes)
#                 #startime = endtime - int(handles['plot_timeback'].text())*np.timedelta64(1,'s')
#                 for timeskey in times.keys():
#                     timediffs = (times[timeskey] - endtime).to_numpy()
#                     neededidx = (timediffs/np.timedelta64(1,'s')+int(handles['plot_timeback'].text()))>0
#                     times[timeskey]= times[timeskey][neededidx]
#                   #  idxes[timeskey]= idxes[timeskey][neededidx]
#                 #print(neededidx )
# =============================================================================
            self.axes.cla()
            self.axes.plot(times['trialstart'], np.zeros(len(times['trialstart']))+.5, 'b|', markersize = 150)
            self.axes.plot(times['trialend'], np.zeros(len(times['trialend']))+.5, 'r|', markersize = 150)
            self.axes.plot(times['GoCue'], np.zeros(len(times['GoCue']))+.5, 'g|', markersize = 100)
            
            self.axes.plot(times['lick_L'], np.zeros(len(times['lick_L'])), 'k|')
            
            self.axes.plot(times['lick_R'], np.zeros(len(times['lick_R']))+1, 'k|')
            self.axes.plot(times['choice_L'], np.zeros(len(times['choice_L']))+.1, 'go', markerfacecolor = (1, 1, 1, 1))
            self.axes.plot(times['choice_R'], np.zeros(len(times['choice_R']))+.9, 'go',markerfacecolor = (1, 1, 1, 1))
            self.axes.plot(times['reward_L'], np.zeros(len(times['reward_L']))+.2, 'go', markerfacecolor = (0, 1, 0, 1))
            self.axes.plot(times['reward_R'], np.zeros(len(times['reward_R']))+.8, 'go',markerfacecolor = (0, 1, 0, 1))  
            self.axes.plot(times['autowater_L'], np.zeros(len(times['autowater_L']))+.7, 'go', markerfacecolor = (0, 0, 1, 1))
            #self.axes.plot(times['autowater_L'], np.zeros(len(times['autowater_L']))+.1, 'go', markerfacecolor = (0, 0, 1, 1))
            #self.axes.plot(times['autowater_R'], np.zeros(len(times['autowater_R']))+.9, 'go',markerfacecolor = (0, 0, 1, 1))
            if 'lick_M' in times.keys():
                self.axes.plot(times['lick_M'], np.zeros(len(times['lick_M']))+.5, 'k|')
                self.axes.plot(times['choice_M'], np.zeros(len(times['choice_M']))+.45, 'go',markerfacecolor = (1, 1, 1, 1))
                self.axes.plot(times['reward_M'], np.zeros(len(times['reward_M']))+.55, 'go', markerfacecolor = (0, 1, 0, 1))
                #self.axes.plot(times['autowater_M'], np.zeros(len(times['autowater_M']))+.45, 'go',markerfacecolor = (0, 0, 1, 1))
            self.axes.set_title('Lick and reward history')
            self.axes.set_yticks([0,1])
            self.axes.set_yticklabels(['Left', 'Right'])
            #if  handles and handles['plot_timeback'].text().isnumeric():
                #self.axes.set_xlim(startime,endtime)
            self.draw()
            
    def plot_bias(self,data = [],startime=None,endtime=None,numberofpoints = 10,session = None):
        self.axes.cla()
        if type(data) == dict and len(data) > 0:
            times, values = self.minethedata(data,session)
            if startime == None:
                startime = np.min(times['alltimes'])
            else:
                startime = np.max([np.datetime64(np.max(times['alltimes']) - startime),np.min(times['alltimes'])])
            endtime = np.max(times['alltimes'])
# =============================================================================
#             self.axes.cla()
#             print(times['motor_position_rostrocaudal'])
#             print(values['motor_position_rostrocaudal'])
#             self.axes.plot(times['motor_position_rostrocaudal'], values['motor_position_rostrocaudal'], 'ko',label = 'RC')
#             self.axes.plot(times['motor_position_lateral'], values['motor_position_lateral'], 'ro',label = 'Lat')
# =============================================================================
            steptime = (endtime-startime)/numberofpoints
            timerange = pd.date_range(start = startime, end = endtime, periods = numberofpoints*10) #freq = 's' *10
            #print(startime , endtime)
            #lick_left_num = np.zeros(len(timerange))
            #lick_right_num  = np.zeros(len(timerange))
            
            reward_left_num = np.zeros(len(timerange))
            reward_right_num = np.zeros(len(timerange))
            if 'lick_M' in times.keys():
                lick_middle_num  = np.zeros(len(timerange))
                reward_middle_num = np.zeros(len(timerange))
            for idx,timenow in enumerate(timerange):
                timenow = np.datetime64(timenow)
                #lick_left_num[idx] = sum((timenow+steptime > times['lick_L']) & (timenow-steptime<times['lick_L']))
                #lick_right_num[idx] = sum((timenow+steptime > times['lick_R']) & (timenow-steptime<times['lick_R']))
                
                reward_left_num[idx] = sum((timenow+steptime > times['choice_L']) & (timenow-steptime<times['choice_L']))
                reward_right_num[idx] = sum((timenow+steptime > times['choice_R']) & (timenow-steptime<times['choice_R']))
                if 'lick_M' in times.keys():
                    lick_middle_num[idx] = sum((timenow+steptime > times['lick_M']) & (timenow-steptime<times['lick_M']))
                    reward_middle_num[idx] = sum((timenow+steptime > times['choice_M']) & (timenow-steptime<times['choice_M']))

            
            self.axes.cla()
            if 'lick_M' in times.keys():
                idxes = np.where(times['p_reward_ratio'] > startime)
                golden_reward_R_1 = values['reward_p_L'][idxes]/(values['reward_p_L'][idxes]+values['reward_p_R'][idxes]+values['reward_p_M'][idxes])
                golden_reward_R_2 = (values['reward_p_L'][idxes]+values['reward_p_M'][idxes])/(values['reward_p_L'][idxes]+values['reward_p_R'][idxes]+values['reward_p_M'][idxes])
                
                reward_sum_num = reward_right_num+reward_left_num+reward_middle_num
                
                #self.axes.plot(timerange, bias_lick_R, 'k-',label = 'Lick bias')
                #self.axes.plot(timerange, bias_reward_R, 'g-',label = 'choice bias')
                self.axes.stackplot(timerange,  reward_left_num/reward_sum_num ,  reward_middle_num/reward_sum_num ,  reward_right_num/reward_sum_num ,colors=['r','g','b'], alpha=0.4 )
                #self.axes.plot(timerange, bias_reward_R_1, 'g-',label = 'choice bias')
                #self.axes.plot(timerange, bias_reward_R_2, 'g-',label = 'choice bias')
                
                
                self.axes.plot(times['reward_p_L'][idxes], values['reward_p_L'][idxes], 'r-',label = 'Reward probability Left')
                self.axes.plot(times['reward_p_R'][idxes], values['reward_p_R'][idxes], 'b-',label = 'Reward probability Right')
                self.axes.plot(times['reward_p_M'][idxes], values['reward_p_M'][idxes], 'g-',label = 'Reward probability Middle')
                self.axes.plot(times['p_reward_ratio'][idxes], golden_reward_R_1, 'y-',label = 'Reward ratio')
                self.axes.plot(times['p_reward_ratio'][idxes], golden_reward_R_2, 'y-',label = 'Reward ratio')
                #self.axes.plot(times['p_reward_ratio'][idxes], values['p_reward_ratio'][idxes], 'y-',label = 'Reward ratio')
                self.axes.set_ylim(0,1)
                vals = self.axes.get_yticks()
                self.axes.set_yticklabels(['{:,.0%}'.format(x) for x in vals])
            else:
                #bias_lick_R = lick_right_num/(lick_right_num+lick_left_num)
                bias_reward_R = reward_right_num/(reward_right_num+reward_left_num)
                #self.axes.plot(timerange, bias_lick_R, 'k-',label = 'Lick bias')
                self.axes.plot(timerange, bias_reward_R, 'g-',label = 'choice bias')
                idxes = times['p_reward_ratio'] > startime
                self.axes.plot(times['reward_p_L'][idxes], values['reward_p_L'][idxes], 'r-',label = 'Reward probability Left')
                self.axes.plot(times['reward_p_R'][idxes], values['reward_p_R'][idxes], 'b-',label = 'Reward probability Right')
                self.axes.plot(times['p_reward_ratio'][idxes], values['p_reward_ratio'][idxes], 'y-',label = 'Reward ratio')
                self.axes.set_yticks([0,1])
                self.axes.set_yticklabels(['Left', 'Right'])
                self.axes.set_ylim(-.1,1.1)
            self.axes.set_title('Lick and reward bias')
            self.draw()
            
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
