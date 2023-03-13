import pyforms, numpy as np, traceback, math
from pyforms.basewidget import BaseWidget
from pyforms.controls import ControlLabel
from pyforms.controls import ControlText
from pyforms.controls import ControlButton
from pyforms.controls import ControlCombo
from pyforms.controls import ControlCheckBox
from pyforms.controls import ControlFile
from pyforms.controls import ControlList
from pyforms.controls import ControlTextArea
from pyforms.controls import ControlNumber
from pyforms.controls import ControlMatplotlib


from .module_api import WavePlayerModule


class OutputChannelGUI(BaseWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.api = kwargs.get('api', None)
        self.channel_index = kwargs.get('channel_index', None)
    
        self.set_margin(10)
        self.setMinimumHeight(60)

        self._evt_report    = ControlCheckBox('Event report', changed_event=self.__event_report_changed_event, default=kwargs.get('event_report',False) )
        self._loop_mode     = ControlCheckBox('Loop mode', changed_event=self.__loop_mode_changed_event, default=kwargs.get('loop_mode',False) )
        self._loop_duration = ControlText('Loop duration', changed_event=self.__loop_duration_changed_event, default=kwargs.get('loop_duration',False) )

        self.formset = [('_evt_report', ' ', '_loop_duration', '_loop_mode')]

    def __event_report_changed_event(self):
        value = self._evt_report.value
        channel_index = self.channel_index-1

        data = self.api.bpod_events
        data[channel_index] = value
        if not self.api.set_bpod_events(data):
            self.alert( 'Not able to set bpod events: {0}'.format(data) )


    def __loop_mode_changed_event(self):
        value = self._loop_mode.value
        channel_index = self.channel_index-1

        data = self.api.loop_mode
        data[channel_index] = value
        try:
            if not self.api.set_loop_mode(data):
                self.alert( 'Not able to set loop mode: {0}'.format(data) )
        except Exception:
            self.critical( traceback.format_exc(), 'An error occurred')


    def __loop_duration_changed_event(self):
        value = self._loop_duration.value
        channel_index = self.channel_index-1

        data = self.api.loop_duration
        data[channel_index] = value
        if not self.api.set_loop_duration(data):
            self.alert( 'Not able to set loop duration: {0}'.format(data) )






class WavePlayerModuleGUI(WavePlayerModule, BaseWidget):

    TITLE = 'Analog Output Module'

    def __init__(self, parent_win = None):
        BaseWidget.__init__(self, self.TITLE, parent_win = parent_win)
        WavePlayerModule.__init__(self)

        self.set_margin(10)

        self._port 			= ControlText('Serial port', default = '/dev/ttyACM0')
        self._connect_btn   = ControlButton('Connect', checkable=True, default = self.__connect_btn_evt)
        self._getparams_btn = ControlButton('Get Parameters', default=self.get_parameters, enabled=False)
        self._info          = ControlTextArea('Information', enabled=False)
        self._channels      = ControlList('Channels', readonly=True, enabled=False)


        self._triggermode = ControlCombo('Channel Select', changed_event=self.__set_trigger_mode_evt, enabled=False)
        self._outputrange = ControlCombo('Output range', changed_event=self.__set_output_range_evt, enabled=False)
        
        self._triggermode.add_item('Normal',0)
        self._triggermode.add_item('Master',1)
        self._triggermode.add_item('Toggle',2)

        self._outputrange.add_item('0V to +5V',0)
        self._outputrange.add_item('0V to +10V',1)
        self._outputrange.add_item('0V to +12V',2)
        self._outputrange.add_item('-5V to +5V',3)
        self._outputrange.add_item('-10V to +10V',4)
        self._outputrange.add_item('-12V to +12V',5)
        
        self._wavegraph  = ControlMatplotlib('Waveform', on_draw=self.__on_draw_evt)
        self._amplitude  = ControlNumber('Amplitude',   default=1.0, minimum=0, maximum=1000, changed_event=self._wavegraph.draw, enabled=False)
        self._duration   = ControlNumber('Duration',    default=3.0, minimum=0, maximum=100, changed_event=self._wavegraph.draw, enabled=False)
        self._frequency  = ControlNumber('Frequency',   default=1000.0, minimum=1, maximum=10000, changed_event=self._wavegraph.draw, enabled=False)
        self._samplerate = ControlNumber('Sample rate', default=96000,  minimum=1, maximum=100000, changed_event=self._wavegraph.draw, enabled=False)
        
        self._wave_index        = ControlNumber('Waveform', enabled=False)
        self._channel_index     = ControlNumber('Channel', minimum=1, default=1, enabled=False)
        self._load_waveform_btn = ControlButton('Load waveform', default=self.__load_waveform_btn_evt, enabled=False)
        self._play_waveform_btn = ControlButton('Play', default=self.__play_btn_evt, enabled=False)
        self._stop_waveform_btn = ControlButton('Stop', default=self.__stop_btn_evt, enabled=False)

        self.formset = [
            {
                'a:Connection' :[
                    ('_port','_connect_btn'), 
                    ('_triggermode', '_outputrange'),
                    ('_amplitude', '_duration', '_frequency', '_samplerate'),
                    '_wavegraph',
                    ('_wave_index','_load_waveform_btn', '_channel_index', '_play_waveform_btn', '_stop_waveform_btn')
                ],
                'c: Channels': ['_channels'],
                'd:Information': ['_getparams_btn','_info']
            }
        ]



    ##########################################################################
    ## EVENTS ################################################################
    ##########################################################################

    def __set_output_range_evt(self):
        if not self.form_has_loaded: return
        self.set_output_range(self._outputrange.value)

    def __set_trigger_mode_evt(self):
        if not self.form_has_loaded: return
        self.set_trigger_mode(self._triggermode.value)

    def __set_trigger_profiles_evt(self):
        self.set_trigger_profiles(self._triggerprofiles.value)



    def __play_btn_evt(self):
        self.play( int(self._channel_index.value), int(self._wave_index.value) )

    def __stop_btn_evt(self):
        self.stop()

    def __on_draw_evt(self, figure):
        try:
            axes = figure.add_subplot(111)
            axes.clear()

            samples = np.arange(0.0, self._duration.value, 1.0/self._samplerate.value)
            wave    = self._amplitude.value * np.sin(2.0*math.pi*self._frequency.value*samples)

            axes.plot(wave)

            y = self._amplitude.value
            x = math.asin( y/self._amplitude.value )/(2.0*math.pi*self._frequency.value)
            
            axes.set_xlim(0, x/(1/self._samplerate.value)*8 )
            axes.set_ylim( np.min(wave), np.max(wave) )
    
            self._wavegraph.repaint()
        except:
            self.critical( traceback.format_exc(), 'An error occurred')

    def __connect_btn_evt(self):
        if self._connect_btn.checked:
            self.open(self._port.value)
        else:
            self.disconnect()

    def __load_waveform_btn_evt(self):
        samples = np.arange(0.0, self._duration.value, 1.0/self._samplerate.value)
        wave    = self._amplitude.value * np.sin(2.0*math.pi*self._frequency.value*samples)
        self.set_sampling_period(self._samplerate.value)
        res = self.load_waveform( int(self._wave_index.value) , wave)
        if not res:
            self.alert('Failed to load the waveform')
    

    ##########################################################################
    ## OVERRIDE FUNCTIONS ####################################################
    ##########################################################################

    def open(self, port):
        res = super().open(port)
        if res:
            self._connect_btn.label = 'Disconnect'
            
            self._channels.enabled = True
            self._getparams_btn.enabled = True
            self._info.enabled = True
            self._channels.enabled = True

            self._outputrange.enabled = True
            self._triggermode.enabled = True

            self._wavegraph.enabled = True
            self._amplitude.enabled = True
            self._duration.enabled = True
            self._frequency.enabled = True
            self._samplerate.enabled = True
            
            self._wave_index.enabled = True
            self._channel_index.enabled = True
            self._load_waveform_btn.enabled = True
            self._play_waveform_btn.enabled = True
            self._stop_waveform_btn.enabled = True

            for i in range(self.n_channels):
                self._channels += ('({0})'.format(i+1), 
                    OutputChannelGUI(
                        api=self,
                        channel_index=i+1,
                        event_report=bool(self.bpod_events[i]),
                        loop_mode=bool(self.loop_mode[i]),
                        loop_duration=str(self.loop_duration[i]),
                    )
                )

            self._wavegraph.draw()
        else:
            self._connect_btn.checked = False
            

    def disconnect(self):
        super().disconnect()

        self._connect_btn.label = 'Connect'

        self._channels.clear()
        self._info.value = ''

        self._channels.enabled = False
        self._getparams_btn.enabled = False
        self._info.enabled = False
        self._channels.enabled = False

        self._outputrange.enabled = False
        self._triggermode.enabled = False

        self._wavegraph.enabled = False
        self._amplitude.enabled = False
        self._duration.enabled = False
        self._frequency.enabled = False
        self._samplerate.enabled = False
        
        self._wave_index.enabled = False
        self._channel_index.enabled = False
        self._load_waveform_btn.enabled = False
        self._play_waveform_btn.enabled = False
        self._stop_waveform_btn.enabled = False


    def get_parameters(self):
        super().get_parameters()

        self._wave_index.max    = self.max_waves-1
        self._channel_index.max = self.n_channels

        text  = ''
        text += 'Number of channels: {0}\n'.format(self.n_channels)
        text += 'Max waves: {0}\n'.format(self.max_waves)
        text += 'Trigger mode: {0}\n'.format(self.trigger_mode)
        text += 'Trigger profile enabled: {0}\n'.format(self.trigger_profile_enable)
        text += 'Number of trigger profiles: {0}\n'.format(self.n_trigger_profiles)
        text += 'Output range: {0}\n'.format(self.output_range)
        text += 'Bpod events: {0}\n'.format(self.bpod_events)
        text += 'Loop mode {0}\n'.format(self.loop_mode)
        text += 'Sampling rates: {0}\n'.format(self.sampling_rate)
        text += 'Loop durations: {0}\n'.format(self.loop_duration)

        self._info.value = text

        self._outputrange.value = self.output_range
        self._triggermode.value = self.trigger_mode


        windows = self._channels.value
        for i in range( len(windows) ):
            windows[i][1]._evt_report.value = self.bpod_events[i]
            windows[i][1]._loop_mode.value = self.loop_mode[i]
            windows[i][1]._loop_duration.value = str(self.loop_duration[i])

    def _stop(self):
        self.stop()

    def before_close_event(self):
        self.close()
        super().before_close_event()



if __name__=='__main__':
    pyforms.start_app( WavePlayerModuleGUI, geometry=(2000,0,600,500) )