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

print('started')
paths = ['/home/rozmar/Data/Behavior/Behavior_room/Tower-2','C:\\Users\\labadmin\\Documents\\Pybpod\\Projects']
for defpath in paths:
    print(defpath)
    if os.path.exists(defpath):
        break
#defpath = '/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects'#'C:\\Users\\labadmin\\Documents\\Pybpod\\Projects'#'/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects'#

class App(QDialog):
    def __init__(self):
        super().__init__()
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
        self.initUI()
        
        self.timer  = QTimer(self)
        self.timer.setInterval(5000)          # Throw event timeout with an interval of 1000 milliseconds
        self.timer.timeout.connect(self.reloadthedata) # each time timer counts a second, call self.blink
        self.variables_to_display = ['ValveOpenTime_L',
                                     'ValveOpenTime_R',
                                     'Trialnumber_in_block',
                                     'Trialnumber_in_block_SD',
                                     'Trialnumber_in_block_min',
                                     'block_start_with_bias_check',
                                     'block_first_to_right',
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
                                     ]
        free_water = {
                      'Trialnumber_in_block' : 15,
                      'Trialnumber_in_block_SD': 5,
                      'Trialnumber_in_block_min': 10,
                      'block_start_with_bias_check' : False,
                      'block_first_to_right' : False,
                      'block_number' : 20,
                      'difficulty_sum_reward_rate' : 1.,
                      'difficulty_ratio_pair_num' : 0,
                      'delay' : 1.,
                      'delay_min' : .5,
                      'delay_max': 2.,
                      'response_time' : 2.,
                      'iti' : 3., 
                      'iti_min' : .5, # minimum ITI
                      'iti_max' : 2.,
                      'increase_ITI_on_ignore_trials' : False, 
                      'auto_water' : True,
                      'auto_water_min_unrewarder_trials_in_a_row' : 5,
                      'auto_water_min_ignored_trials_in_a_row' : 1,
                      'auto_train_min_rewarded_trial_num' : 10,
                      'early_lick_punishment' : False,
                }
        baptize = {
                'Trialnumber_in_block' : 15,
                'Trialnumber_in_block_SD' : 5,
                'Trialnumber_in_block_min' : 10,
                'block_start_with_bias_check' : True,
                'block_first_to_right' : True,
                'block_number' : 20,
                'difficulty_sum_reward_rate' : 1,
                'difficulty_ratio_pair_num' : 1,
                'delay' : 1.,
                'delay_min' : .5,
                'delay_max' : 2.,
                'response_time' : 2.,
                'iti' : 3., 
                'iti_min' : .5, # minimum ITI
                'iti_max': 5.,
                'increase_ITI_on_ignore_trials' : True,
                'auto_water' : False,
                'auto_train_min_rewarded_trial_num' : 10,
                'early_lick_punishment' : False,
                                     }
        baptize_early_lick = {
                'Trialnumber_in_block' : 15,
                'Trialnumber_in_block_SD' : 5,
                'Trialnumber_in_block_min' : 10,
                'block_start_with_bias_check' : True,
                'block_first_to_right' : True,
                'block_number' : 20,
                'difficulty_sum_reward_rate' : 1,
                'difficulty_ratio_pair_num' : 1,
                'delay' : 1.,
                'delay_min' : .5,
                'delay_max' : 2.,
                'response_time' : 1.,
                'iti' : 3., 
                'iti_min' : .5, # minimum ITI
                'iti_max': 15.,
                'increase_ITI_on_ignore_trials' : True,
                'auto_water' : False,
                'auto_train_min_rewarded_trial_num' : 10,
                'early_lick_punishment' : True,
                                     }
        baptize_low_probability = {
                'Trialnumber_in_block' : 50,
                'Trialnumber_in_block_SD' : 10,
                'Trialnumber_in_block_min' : 40,
                'block_start_with_bias_check' : True,
                'block_first_to_right' : True,
                'block_number' : 20,
                'difficulty_sum_reward_rate' : .45,
                'difficulty_ratio_pair_num' : 1,
                'delay' : 1.,
                'delay_min' : .5,
                'delay_max' : 3.,
                'response_time' : .5,
                'iti' : 3.5, 
                'iti_min' : .5, # minimum ITI
                'iti_max': 10.,
                'increase_ITI_on_ignore_trials' : True,
                'auto_water' : False,
                'auto_train_min_rewarded_trial_num' : 30,
                'early_lick_punishment' : True,
                                     }

        full_task = {
                'Trialnumber_in_block' : 50,
                'Trialnumber_in_block_SD' : 10,
                'Trialnumber_in_block_min' : 40,
                'block_start_with_bias_check' : True,
                'block_first_to_right' : True,
                'block_number' : 20,
                'difficulty_sum_reward_rate' : .45,
                'difficulty_ratio_pair_num' : 3,
                'delay' : 1.,
                'delay_min' : .5,
                'delay_max' : 3.,
                'response_time' : .5,
                'iti' : 3.5, 
                'iti_min' : .5, # minimum ITI
                'iti_max': 45.,
                'increase_ITI_on_ignore_trials' : True,
                'auto_water' : False,
                'auto_train_min_rewarded_trial_num' : 25,
                'early_lick_punishment' : True,
                                     }
        
        self.preset_variables = dict()
        self.preset_variables['free_water_0'] = free_water
        self.preset_variables['baptize_1'] = baptize
        self.preset_variables['baptize_low_probability_2'] = baptize_low_probability
        self.preset_variables['baptize_early_lick_3'] = baptize_early_lick
        self.preset_variables['full_task_4'] = full_task
        
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
        filterorder = ['project','experiment','setup','session']
        for filternow in filterorder:
            filterstring = str(self.handles['filter_'+filternow].currentText())
            if not re.findall('all',filterstring):
                selected[filternow] = filterstring
            else:
                selected[filternow] = None

        self.data = behavior_rozmar.loadcsvdata(self.data,
                                                projectdir = self.dirs['projectdir'],
                                                projectnames_needed = selected['project'],
                                                experimentnames_needed = selected['experiment'],
                                                setupnames_needed = selected['setup'],
                                                sessionnames_needed = selected['session'],
                                                load_only_last_day = True)
        self.handles['load_the_data'].setText('Load the data')
        self.handles['load_the_data'].setStyleSheet('QPushButton {color: black;}')
        self.updateUI()
        #print('data reloaded')
        #print(time.perf_counter())
    
    @pyqtSlot()    
    def reloadthedata(self):
        #self.data = behavior_rozmar.loadcsvdata(self.data, projectdir = self.dirs['projectdir'])
        self.loadthedata()
        self.filterthedata()
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
        filterorder = ['project','experiment','setup','session','subject','experimenter']
        
        if type(self.data) == pd.DataFrame:
            self.data_now = self.data 
            for filternow in filterorder:
                filterstring = str(self.handles['filter_'+filternow].currentText())
                if not re.findall('all',filterstring):
                    self.data_now = self.data_now[self.data_now[filternow] == filterstring]
            
            if len(self.data_now) > 0:
                endtime = max(self.data_now['PC-TIME'])
                if  self.handles['plot_timeback'].text().isnumeric():
                    startime = endtime - pd.to_timedelta(int(self.handles['plot_timeback'].text()),'s')
                else:
                    startime = min(self.data_now['PC-TIME'])
                if  self.handles['plot_timeback_runningwindow'].text().isnumeric(): # determining averaging window size
                    numberofpoints = int(self.handles['plot_timeback_runningwindow'].text())
                else:
                    numberofpoints = 10    
                self.handles['axes1'].plot_licks_and_rewards(self.data_now,startime,endtime)
                self.handles['axes2'].plot_bias(self.data_now,startime,endtime,numberofpoints)
                print('plotting done')
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
        self.handles['filter_session'] = QComboBox(self)
        self.handles['filter_session'].setFocusPolicy(Qt.NoFocus)
        self.handles['filter_session'].addItem('all sessions')
        self.handles['filter_session'].addItems(self.alldirs['sessionnames'])
        self.handles['filter_session'].currentIndexChanged.connect(lambda: self.filterthedata('filter_session'))
        
        self.handles['load_the_data'] = QPushButton('Load the data')
        self.handles['load_the_data'].setFocusPolicy(Qt.NoFocus)
        self.handles['load_the_data'].clicked.connect(self.loadthedata)
        
        self.handles['filter_subject'] = QComboBox(self)
        self.handles['filter_subject'].setFocusPolicy(Qt.NoFocus)
        self.handles['filter_subject'].addItem('all subjects')
        #self.handles['filter_subject'].addItems(self.data['subject'].unique())
        self.handles['filter_subject'].currentIndexChanged.connect(lambda: self.filterthedata('filter_subject'))
        self.handles['filter_experimenter'] = QComboBox(self)
        self.handles['filter_experimenter'].setFocusPolicy(Qt.NoFocus)
        self.handles['filter_experimenter'].addItem('all experimenters')
        #self.handles['filter_experimenter'].addItems(self.data['experimenter'].unique())
        self.handles['filter_experimenter'].currentIndexChanged.connect(lambda: self.filterthedata('filter_experimenter'))
        
        self.handles['loadparams'] = QPushButton('Load parameters')
        self.handles['loadparams'].setFocusPolicy(Qt.NoFocus)
        self.handles['loadparams'].clicked.connect(self.load_parameters)
        
        layout.addWidget(self.handles['filter_project'] ,0,0)
        layout.addWidget(self.handles['filter_experiment'],0,1)
        layout.addWidget(self.handles['filter_setup'],0,2)
        layout.addWidget(self.handles['filter_session'],0,3)
        layout.addWidget(self.handles['load_the_data'],0,4)
        layout.addWidget(self.handles['filter_subject'],0,5)
        layout.addWidget(self.handles['filter_experimenter'],0,6)
        layout.addWidget(self.handles['loadparams'],0,7)
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
        self.handles['filter_experimenter'].currentIndexChanged.disconnect()
        currtext = self.handles['filter_experimenter'].currentText()
        self.handles['filter_experimenter'].clear()
        self.handles['filter_experimenter'].addItem('all experimenters')
        if type(self.data) == pd.DataFrame:
            self.handles['filter_experimenter'].addItems(self.data['experimenter'].unique())
            idx = self.handles['filter_experimenter'].findText(currtext)
            if idx != -1:
                self.handles['filter_experimenter'].setCurrentIndex(idx)
        self.handles['filter_experimenter'].currentIndexChanged.connect(lambda: self.filterthedata('filter_experimenter'))
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
        if lastselected == 'filter_project' or lastselected == 'filter_setup':
            self.handles['filter_session'].currentIndexChanged.disconnect()
            self.handles['filter_session'].clear()
            self.handles['filter_session'].addItem('all sessions')
            self.handles['filter_session'].addItems(self.alldirs['sessionnames'])
            self.handles['filter_session'].currentIndexChanged.connect(lambda: self.filterthedata('filter_session'))
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

    def minethedata(self,data):
        idxes = dict()
        times = dict()
        values = dict()
        idxes['lick_L'] = data['var:WaterPort_L_ch_in'] == data['+INFO']
        times['lick_L'] = data['PC-TIME'][idxes['lick_L']]
        idxes['choice_L'] = (data['MSG'] == 'Choice_L') & (data['TYPE'] == 'TRANSITION')
        times['choice_L'] = data['PC-TIME'][idxes['choice_L']]
        idxes['reward_L'] = (data['MSG'] == 'Reward_L') & (data['TYPE'] == 'TRANSITION')
        times['reward_L'] = data['PC-TIME'][idxes['reward_L']]        
        idxes['autowater_L'] = (data['MSG'] == 'Auto_Water_L') & (data['TYPE'] == 'TRANSITION')
        times['autowater_L'] = data['PC-TIME'][idxes['autowater_L']]        
        idxes['autowater_R'] = (data['MSG'] == 'Auto_Water_R') & (data['TYPE'] == 'TRANSITION')
        times['autowater_R'] = data['PC-TIME'][idxes['autowater_R']]
        idxes['lick_R'] = data['var:WaterPort_R_ch_in'] == data['+INFO']
        times['lick_R'] = data['PC-TIME'][idxes['lick_R']]
        idxes['choice_R'] = (data['MSG'] == 'Choice_R') & (data['TYPE'] == 'TRANSITION')
        times['choice_R'] = data['PC-TIME'][idxes['choice_R']]
        idxes['reward_R'] = (data['MSG'] == 'Reward_R') & (data['TYPE'] == 'TRANSITION')
        times['reward_R'] = data['PC-TIME'][idxes['reward_R']]
        idxes['trialstart'] = data['TYPE'] == 'TRIAL'
        times['trialstart'] = data['PC-TIME'][idxes['trialstart']]
        idxes['trialend'] = data['TYPE'] == 'END-TRIAL'
        times['trialend'] = data['PC-TIME'][idxes['trialend']]
        idxes['GoCue'] = (data['MSG'] == 'GoCue') & (data['TYPE'] == 'TRANSITION')
        times['GoCue'] = data['PC-TIME'][idxes['GoCue']]
        
        idxes['reward_p_L'] = idxes['GoCue']
        times['reward_p_L'] = data['PC-TIME'][idxes['reward_p_L']]
        values['reward_p_L'] = data['reward_p_L'][idxes['reward_p_L']]
        
        idxes['reward_p_R'] = idxes['GoCue']
        times['reward_p_R'] = data['PC-TIME'][idxes['reward_p_R']]
        values['reward_p_R'] = data['reward_p_R'][idxes['reward_p_R']]
        
        idxes['p_reward_ratio'] = idxes['GoCue']
        times['p_reward_ratio'] = times['reward_p_R']
        values['p_reward_ratio'] = values['reward_p_R'] / (values['reward_p_R']+ values['reward_p_L'])
        
        return times, idxes, values
    
    def plot_licks_and_rewards(self,data = [],startime=None,endtime=None):
        self.axes.cla()
        if type(data) == pd.core.frame.DataFrame and len(data) > 0:
            times,idxes, values = self.minethedata(data)
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
            self.axes.plot(times['autowater_L'], np.zeros(len(times['autowater_L']))+.1, 'go', markerfacecolor = (0, 0, 1, 1))
            self.axes.plot(times['autowater_R'], np.zeros(len(times['autowater_R']))+.9, 'go',markerfacecolor = (0, 0, 1, 1))
            self.axes.set_title('Lick and reward history')
            self.axes.set_yticks([0,1])
            self.axes.set_yticklabels(['Left', 'Right'])
            #if  handles and handles['plot_timeback'].text().isnumeric():
                #self.axes.set_xlim(startime,endtime)
            self.draw()
            
    def plot_bias(self,data = [],startime=None,endtime=None,numberofpoints = 10):
        self.axes.cla()
        if type(data) == pd.core.frame.DataFrame and len(data) > 0:
            times,idxes, values = self.minethedata(data)
# =============================================================================
#             alltimes = []       
#             for timeskey in times.keys(): # finding endtime and starttime
#                if len(alltimes) > 0:
#                    alltimes = pd.concat([alltimes,times[timeskey]])
#                else:
#                    alltimes = times[timeskey]
#             startime = min(alltimes) 
#             endtime = max(alltimes)
#             if  handles and handles['plot_timeback'].text().isnumeric():
#                 startime = endtime - pd.to_timedelta(int(handles['plot_timeback'].text()),'s')
# =============================================================================
# =============================================================================
#                 print(startime)
#                 for timeskey in times.keys():
#                     timediffs = (times[timeskey] - endtime).to_numpy()
#                     neededidx = (timediffs/np.timedelta64(1,'s'))>0
#                     times[timeskey]= times[timeskey][neededidx]
#                 alltimes = []       
#                 for timeskey in times.keys(): # finding endtime and starttime
#                    if len(alltimes) > 0:
#                        alltimes.append(times[timeskey])
#                    else:
#                        alltimes = times[timeskey]
#                 startime = min(alltimes) 
#                 endtime = max(alltimes)    
# =============================================================================
            
            
            steptime = (endtime-startime)/numberofpoints
            timerange = pd.date_range(start = startime, end = endtime, periods = numberofpoints*10) #freq = 's' *10
            #print(startime , endtime)
            lick_left_num = np.zeros(len(timerange))
            lick_right_num  = np.zeros(len(timerange))
            reward_left_num = np.zeros(len(timerange))
            reward_right_num = np.zeros(len(timerange))
            for idx,timenow in enumerate(timerange):
                lick_left_num[idx] = sum((timenow+steptime > times['lick_L']) & (timenow-steptime<times['lick_L']))
                lick_right_num[idx] = sum((timenow+steptime > times['lick_R']) & (timenow-steptime<times['lick_R']))
                reward_left_num[idx] = sum((timenow+steptime > times['choice_L']) & (timenow-steptime<times['choice_L']))
                reward_right_num[idx] = sum((timenow+steptime > times['choice_R']) & (timenow-steptime<times['choice_R']))

            bias_lick_R = lick_right_num/(lick_right_num+lick_left_num)
            bias_reward_R = reward_right_num/(reward_right_num+reward_left_num)
            self.axes.cla()
            self.axes.plot(timerange, bias_lick_R, 'k-',label = 'Lick bias')
            self.axes.plot(timerange, bias_reward_R, 'g-',label = 'choice bias')
            idxes = times['p_reward_ratio'] > startime
            self.axes.plot(times['reward_p_L'][idxes], values['reward_p_L'][idxes], 'r-',label = 'Reward probability Left')
            self.axes.plot(times['reward_p_R'][idxes], values['reward_p_R'][idxes], 'b-',label = 'Reward probability Right')
            self.axes.plot(times['p_reward_ratio'][idxes], values['p_reward_ratio'][idxes], 'y-',label = 'Reward ratio')
            
            self.axes.set_ylim(-.1,1.1)
            #self.axes.set_xlim(startime,endtime)
            self.axes.set_yticks([0,1])
            self.axes.set_yticklabels(['Left', 'Right'])
            #self.axes.legend()
# =============================================================================
#             self.axes.plot(timerange, lick_left_num, 'b-')
#             self.axes.plot(timerange, lick_right_num, 'r-')
# =============================================================================
            self.axes.set_title('Lick and reward bias')
            self.draw()
            
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
