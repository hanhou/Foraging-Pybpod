import behavior_rozmar as behavior_rozmar
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton,  QLineEdit, QCheckBox, QHBoxLayout, QGroupBox, QDialog, QVBoxLayout, QGridLayout, QComboBox, QSizePolicy
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QTimer

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import numpy as np
import pandas as pd
import re
import time as time
from datetime import datetime


defpath = '/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects'# '/home/rozmar/Data/Behavior/Projects'#'/home/rozmar/Data/Behavior/Projects'#'C:\\Users\\labadmin\\Documents\\Pybpod\\Projects'#'/home/rozmar/Network/BehaviorRig/Behavroom-Stacked-2/labadmin/Documents/Pybpod/Projects'#
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
        self.initUI()
        
        self.timer  = QTimer(self)
        self.timer.setInterval(3000)          # Throw event timeout with an interval of 1000 milliseconds
        self.timer.timeout.connect(self.reloadthedata) # each time timer counts a second, call self.blink
        
    def loaddirectorystructure(self):
        dirstructure, projectnames, experimentnames, setupnames, sessionnames = behavior_rozmar.loaddirstucture(defpath)
        self.dirstruct = dirstructure
        self.alldirs = dict()
        self.alldirs['projectnames'] = projectnames
        self.alldirs['experimentnames'] = experimentnames
        self.alldirs['setupnames'] = setupnames
        self.alldirs['sessionnames'] = sessionnames
        
        print('directory structure reloaded')
        
    def loadthedata(self):
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
                                                sessionnames_needed = selected['session'])
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
        filterorder = ['project','experiment','setup','session','subject','experimenter']
        if type(self.data) == pd.DataFrame:
            self.data_now = self.data 
            for filternow in filterorder:
                filterstring = str(self.handles['filter_'+filternow].currentText())
                if not re.findall('all',filterstring):
                    self.data_now = self.data_now[self.data_now[filternow] == filterstring]
            self.handles['axes1'].plot_licks_and_rewards(self.data_now,self.handles)
            self.handles['axes2'].plot_bias(self.data_now,self.handles)
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
        self.setLayout(windowLayout)
        
        self.show()
    
    def createGridLayout(self):
        self.horizontalGroupBox_filter = QGroupBox("Filter")
        layout = QGridLayout()
        self.handles['filter_project'] = QComboBox(self)
        self.handles['filter_project'].addItem('all projects')
        #print(self.alldirs['projectnames'])
        self.handles['filter_project'].addItems(self.alldirs['projectnames'])
        self.handles['filter_project'].currentIndexChanged.connect(lambda: self.filterthedata('filter_project'))
        self.handles['filter_experiment'] = QComboBox(self)
        self.handles['filter_experiment'].addItem('all experiments')
        self.handles['filter_experiment'].addItems(self.alldirs['experimentnames'])
        self.handles['filter_experiment'].currentIndexChanged.connect(lambda: self.filterthedata('filter_experiment'))
        self.handles['filter_setup'] = QComboBox(self)
        self.handles['filter_setup'].addItem('all setups')
        self.handles['filter_setup'].addItems(self.alldirs['setupnames'])
        self.handles['filter_setup'].currentIndexChanged.connect(lambda: self.filterthedata('filter_setup'))
        self.handles['filter_session'] = QComboBox(self)
        self.handles['filter_session'].addItem('all sessions')
        self.handles['filter_session'].addItems(self.alldirs['sessionnames'])
        self.handles['filter_session'].currentIndexChanged.connect(lambda: self.filterthedata('filter_session'))
        
        self.handles['load_the_data'] = QPushButton('Load the data')
        self.handles['load_the_data'].clicked.connect(self.loadthedata)
        
        self.handles['filter_subject'] = QComboBox(self)
        self.handles['filter_subject'].addItem('all subjects')
        #self.handles['filter_subject'].addItems(self.data['subject'].unique())
        self.handles['filter_subject'].currentIndexChanged.connect(lambda: self.filterthedata('filter_subject'))
        self.handles['filter_experimenter'] = QComboBox(self)
        self.handles['filter_experimenter'].addItem('all experimenters')
        #self.handles['filter_experimenter'].addItems(self.data['experimenter'].unique())
        self.handles['filter_experimenter'].currentIndexChanged.connect(lambda: self.filterthedata('filter_experimenter'))
        
        layout.addWidget(self.handles['filter_project'] ,0,0)
        layout.addWidget(self.handles['filter_experiment'],0,1)
        layout.addWidget(self.handles['filter_setup'],0,2)
        layout.addWidget(self.handles['filter_session'],0,3)
        layout.addWidget(self.handles['load_the_data'],0,4)
        layout.addWidget(self.handles['filter_subject'],0,5)
        layout.addWidget(self.handles['filter_experimenter'],0,6)
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
    
    def updateUI(self): # update the other qcomboboxes as well!!!
        currtext = self.handles['filter_subject'].currentText()
        self.handles['filter_subject'].clear()
        self.handles['filter_subject'].addItem('all subjects')
        if type(self.data) == pd.DataFrame:
            self.handles['filter_subject'].addItems(self.data['subject'].unique())
            
            idx = self.handles['filter_subject'].findText(currtext)
            if idx != -1:
                self.handles['filter_subject'].setCurrentIndex(idx)
                
        currtext = self.handles['filter_subject'].currentText()
        self.handles['filter_experimenter'].clear()
        self.handles['filter_experimenter'].addItem('all experimenters')
        if type(self.data) == pd.DataFrame:
            self.handles['filter_experimenter'].addItems(self.data['experimenter'].unique())
            idx = self.handles['filter_experimenter'].findText(currtext)
            if idx != -1:
                self.handles['filter_experimenter'].setCurrentIndex(idx)
        
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
    
    def plot_licks_and_rewards(self,data = [],handles = []):
        self.axes.cla()
        if type(data) == pd.core.frame.DataFrame and len(data) > 0:
            times,idxes, values = self.minethedata(data)
            if  handles and handles['plot_timeback'].text().isnumeric():
                alltimes = []
                for timeskey in times.keys(): # finding endtime
                   if len(alltimes) > 0:
                       alltimes.append(times[timeskey])
                   else:
                       alltimes = times[timeskey]
                endtime = max(alltimes)
                #startime = endtime - int(handles['plot_timeback'].text())*np.timedelta64(1,'s')
                for timeskey in times.keys():
                    timediffs = (times[timeskey] - endtime).to_numpy()
                    neededidx = (timediffs/np.timedelta64(1,'s')+int(handles['plot_timeback'].text()))>0
                    times[timeskey]= times[timeskey][neededidx]
                  #  idxes[timeskey]= idxes[timeskey][neededidx]
                #print(neededidx )
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
            self.axes.set_title('Lick and reward history')
            self.axes.set_yticks([0,1])
            self.axes.set_yticklabels(['Left', 'Right'])
            #if  handles and handles['plot_timeback'].text().isnumeric():
                #self.axes.set_xlim(startime,endtime)
            self.draw()
            
    def plot_bias(self,data = [],handles = []):
        self.axes.cla()
        if type(data) == pd.core.frame.DataFrame and len(data) > 0:
            times,idxes, values = self.minethedata(data)
            alltimes = []       
            for timeskey in times.keys(): # finding endtime and starttime
               if len(alltimes) > 0:
                   alltimes.append(times[timeskey])
               else:
                   alltimes = times[timeskey]
            startime = min(alltimes) 
            endtime = max(alltimes)
            if  handles and handles['plot_timeback'].text().isnumeric():
                startime = endtime - pd.to_timedelta(int(handles['plot_timeback'].text()),'s')
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
            if  handles and handles['plot_timeback_runningwindow'].text().isnumeric(): # determining averaging window size
                numerofpoints = int(handles['plot_timeback_runningwindow'].text())
            else:
                numerofpoints = 10
            
            steptime = (endtime-startime)/numerofpoints
            timerange = pd.date_range(start = startime, end = endtime, periods = numerofpoints*10) #freq = 's' *10
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
            self.axes.plot(times['p_reward_ratio'][idxes], values['p_reward_ratio'][idxes], 'y-',label = 'Reward ratio')
            self.axes.plot(times['reward_p_L'][idxes], values['reward_p_L'][idxes], 'b-',label = 'Reward probability Left')
            self.axes.plot(times['reward_p_R'][idxes], values['reward_p_R'][idxes], 'r-',label = 'Reward probability Right')
            
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

