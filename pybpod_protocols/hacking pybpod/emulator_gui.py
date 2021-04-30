import pyforms
import os
from pybpodapi.bpod import Bpod
from pybpodgui_api.exceptions.run_setup import RunSetupError
from pybpodgui_plugin.utils import make_lambda_func
from pyforms.basewidget import BaseWidget
from pyforms_gui.controls.control_button import ControlButton
from confapp import conf
from pyforms_gui.controls.control_label import ControlLabel
from pyforms_gui.controls.control_text import ControlText
from serial import SerialException
import time


class EmulatorGUI(BaseWidget):
    """
    Main GUI for the Emulator module. This GUI window adapts automatically to the different Bpod versions that are
    connected to the computer to present correctly the number of Ports available as well as the connected modules to the
    Bpod modules ports.

    :param parent_win: The Setup object reference that this Emulator will be associated.
    """

    def __init__(self, parent_win=None):
        self.setup = parent_win
        self.started_correctly = False

        title = 'Emulator for setup: ' + self.setup.name

        BaseWidget.__init__(self, title, parent_win=parent_win)

        self.CHECKED_ICON = conf.EMULATOR_CHECKED_ICON
        self.UNCHECKED_ICON = conf.EMULATOR_UNCHECKED_ICON

        self._currentSetup = ControlLabel(self.setup.name)
        self._selectedBoard = ControlLabel(self.setup.board.name)
        self._selectedProtocol = ControlLabel(self.setup.task.name)

        self._run_task_btn = ControlButton('Run protocol',
                                           default=self.__run_protocol_btn_evt,
                                           checkable=True,
                                           helptext="When a task is running, you can skip all remaining trials by pressing this button. <br/> <b>NOTE:</b> This means that you will need to break the cycle in your task code when the run_state_machine method returns False.")
        self._kill_task_btn = ControlButton('Kill',
                                            default=self.__kill_btn_evt,
                                            style="background-color:rgb(255,0,0);font-weight:bold;",
                                            helptext="<b>NOTE:</b>This will exit the task process abruptly. The code you might have after the trial loop won't execute.")

        self._kill_task_btn.enabled = False

        self._stop_trial_btn = ControlButton('Skip trial',
                                             default=self.__stop_trial_btn_evt,
                                             enabled=False)
        self._pause_btn = ControlButton('Pause',
                                        default=self.__pause_btn_evt,
                                        checkable=True,
                                        enabled=False)

        try:
            bpod = Bpod(self.setup.board.serial_port)
        except SerialException:
            self.critical('No Bpod device connected, cannot continue until one is connected.', 'Bpod not connected')
            return
        except Exception:
            # NOTE: try again in case of the first connection attempt where we always get the utf-8 exception
            bpod = Bpod(self.setup.board.serial_port)

        number_ports = bpod.hardware.inputs.count('P')
        number_bnc = bpod.hardware.outputs.count('B')
        number_wire_in = bpod.hardware.inputs.count('W')
        number_wire_out = bpod.hardware.outputs.count('W')

        self._valve_buttons = []
        self._valve_label = ControlLabel("Valve")
        self._led_buttons = []
        self._led_label = ControlLabel("LED")
        self._poke_buttons = []
        self._poke_label = ControlLabel("Poke")
        
        self._time_control = ControlText()   # HH

        for n in range(1, number_ports + 1):
            btn_valve = ControlButton(str(n), icon=self.UNCHECKED_ICON, checkable=True)
            btn_led = ControlButton(str(n), icon=self.UNCHECKED_ICON, checkable=True)
            btn_poke = ControlButton(str(n), icon=self.UNCHECKED_ICON, checkable=True)

            btn_valve.value = make_lambda_func(self.__button_on_click_evt, btn=btn_valve)
            btn_led.value = make_lambda_func(self.__button_on_click_evt, btn=btn_led)
            btn_poke.value = make_lambda_func(self.__button_on_click_evt, btn=btn_poke)

            setattr(self, f'_btn_Valve{n}', btn_valve)
            setattr(self, f'_btn_PWM{n}', btn_led)
            setattr(self, f'_btn_Port{n}', btn_poke)
            self._valve_buttons.append(btn_valve)
            self._led_buttons.append(btn_led)
            self._poke_buttons.append(btn_poke)

        self._bnc_in_buttons = []
        self._bnc_in_label = ControlLabel("BNC In")
        self._bnc_out_buttons = []
        self._bnc_out_label = ControlLabel("BNC Out")

        for n in range(1, number_bnc + 1):
            btn_bnc_in = ControlButton(str(n), icon=self.UNCHECKED_ICON, checkable=True)
            btn_bnc_out = ControlButton(str(n), icon=self.UNCHECKED_ICON, checkable=True)

            btn_bnc_in.value = make_lambda_func(self.__button_on_click_evt, btn=btn_bnc_in)
            btn_bnc_out.value = make_lambda_func(self.__button_on_click_evt, btn=btn_bnc_out)

            setattr(self, f'_btn_BNC_in{n}', btn_bnc_in)
            setattr(self, f'_btn_BNC_out{n}', btn_bnc_out)
            self._bnc_in_buttons.append(btn_bnc_in)
            self._bnc_out_buttons.append(btn_bnc_out)

        self._wire_in_buttons = []
        self._wire_in_label = ControlLabel("Wire In")
        self._wire_out_buttons = []
        self._wire_out_label = ControlLabel("Wire Out")

        for n in range(1, number_wire_in + 1):
            btn_wire_in = ControlButton(str(n), icon=self.UNCHECKED_ICON, checkable=True)
            btn_wire_in.value = make_lambda_func(self.__button_on_click_evt, btn=btn_wire_in)

            setattr(self, f'_btn_Wire_in{n}', btn_wire_in)
            self._wire_in_buttons.append(btn_wire_in)

        for n in range(1, number_wire_out + 1):
            btn_wire_out = ControlButton(str(n), icon=self.UNCHECKED_ICON, checkable=True)
            btn_wire_out.value = make_lambda_func(self.__button_on_click_evt, btn=btn_wire_out)

            setattr(self, f'_btn_Wire_out{n}', btn_wire_out)
            self._wire_out_buttons.append(btn_wire_out)

        self._modules_indexes_loaded = []

        for idx, mod in enumerate(bpod.modules):
            n = mod.serial_port
            self._modules_indexes_loaded.append(n)
            module_label = ControlLabel(f'{mod.name}')
            control_text_bytes_msg = ControlText()

            btn_send_msg_module = ControlButton(f'Send bytes')
            btn_send_msg_module.value = make_lambda_func(self.__send_msg_btn_evt,
                                                         btn=btn_send_msg_module,
                                                         control_text=control_text_bytes_msg)

            setattr(self, f'_module_label{n}', module_label)
            setattr(self, f'_control_text_bytes_msg{n}', control_text_bytes_msg)
            setattr(self, f'_btn_send_msg_module{n}', btn_send_msg_module)

        if bpod:
            bpod.close()

        self.formset = [
            ([('Current setup:', '_currentSetup'),
              ('Selected board:', '_selectedBoard'),
              ('Selected protocol:', '_selectedProtocol')],
             '',
             ['_run_task_btn', '_kill_task_btn', '_stop_trial_btn', '_pause_btn']),
            '',
            'Behaviour Ports',
            ('_valve_label', tuple([f'_btn_Valve{n.label}' for n in self._valve_buttons])),
            ('_led_label', tuple([f'_btn_PWM{n.label}' for n in self._led_buttons])),
            ('_poke_label', tuple([f'_btn_Port{n.label}' for n in self._poke_buttons])),
            '',
            ('Time Control (sec)', '_time_control'),
            '',
            'BNC',
            ('_bnc_in_label',
             tuple([f'_btn_BNC_in{n.label}' for n in self._bnc_in_buttons]),
             '_bnc_out_label',
             tuple([f'_btn_BNC_out{n.label}' for n in self._bnc_out_buttons])
             ),
            'Wire' if number_wire_in != 0 else '',
            ('_wire_in_label' if number_wire_in != 0 else '',
             tuple([f'_btn_Wire_in{n.label}' for n in self._wire_in_buttons]),
             '_wire_out_label' if number_wire_out != 0 else '',
             tuple([f'_btn_Wire_out{n.label}' for n in self._wire_out_buttons])
             ),
            '',
            'Send bytes to modules' if self._modules_indexes_loaded else '',
            [(f'_module_label{n}', f'_control_text_bytes_msg{n}', f'_btn_send_msg_module{n}') for n in self._modules_indexes_loaded]
        ]

        self.set_margin(10)
        self.started_correctly = True

    def show(self):
        """
        Overrides the BaseWidget implementation of the show method in order to update the textual information of the
        board and protocol used, in case of being updated in the main window after creation of this EmulatorGUI window.
        :return:
        """
        # update names on labels
        self._currentSetup.value = self.setup.name
        self._selectedBoard.value = self.setup.board.name
        self._selectedProtocol.value = self.setup.task.name

        self.init_form()
        super(BaseWidget, self).show()

    def update_task(self, task):
        """
        Method to update the task name
        :param task: The Task to be used to update the information in the UI, if available.
        :return:
        """
        self._selectedProtocol.value = task.name if task is not 0 else ''

    def update_board(self, board):
        """
        Method to update the board name
        :param board: The Board to be used to update the information in the UI, if available.
        :return:
        """
        self._selectedBoard.value = board.name if board is not 0 else ''

    def __send_msg_btn_evt(self, btn=None, control_text=None):
        # get message from textbox
        if btn is None or control_text is None:
            return
        module_index = btn.name[-1]
        message = f'message:{module_index}:{control_text.value}{os.linesep}'

        # send msg through stdin to bpod (we need to create a command first in the other side)
        self.setup.board.proc.stdin.write(message.encode('utf-8'))
        self.setup.board.proc.stdin.flush()

    def __button_on_click_evt(self, btn=None):   # Function that handles time control, if any. HH
        if btn is None:
            return

        if self.setup.status is not self.setup.STATUS_RUNNING_TASK:
            return

        try:      # Click twice, spaced by time_duration
            time_duration = float(self._time_control.value)  # Try this
            
            self.__button_on_click_evt_real(btn)
            time.sleep(time_duration)  # This is not accurate, but good enough 
            btn.checked = not btn.checked  # Update the states
            self.__button_on_click_evt_real(btn)
            
        except:   # Click once
            self.__button_on_click_evt_real(btn)

    def __button_on_click_evt_real(self, btn=None):
        # if btn is None:
        #     return

        # if self.setup.status is not self.setup.STATUS_RUNNING_TASK:
        #     return
        
        name = btn.name.split('_')
        port_name = name[2]
        is_pwm = port_name.startswith('PWM')
        is_valve = port_name.startswith('Valve')
        is_output = is_pwm or is_valve
        if len(name) > 3:
            port_number = name[3][-1]
            is_output = name[3].startswith('out')
        else:
            port_number = ''

        if btn.checked:
            val = 1
            if is_pwm:
                val = 255
            btn.icon = self.CHECKED_ICON
        else:
            val = 0
            btn.icon = self.UNCHECKED_ICON

        if is_output:
            message = f'trigger_output:{port_name}{port_number}:{val}{os.linesep}'
        else:
            message = f'trigger_input:{port_name}{port_number}:{val}{os.linesep}'

        self.setup.board.proc.stdin.write(message.encode('utf-8'))
        self.setup.board.proc.stdin.flush()

    def __run_protocol_btn_evt(self):
        try:
            if self.setup.status == self.setup.STATUS_RUNNING_TASK:
                self.setup.stop_task()
            elif self.setup.status == self.setup.STATUS_READY:
                self.setup.run_task()
        except RunSetupError as err:
            self.warning(str(err), "Warning")
        except Exception as err:
            self.alert(str(err), "Unexpected Error")

    def __kill_btn_evt(self):
        if self.setup.status == self.setup.STATUS_RUNNING_TASK:
            self.setup.kill_task()

    def __stop_trial_btn_evt(self):
        setup = self.setup
        if setup:
            setup._stop_trial_evt()
        else:
            self.critical("There isn't any setup selected. Please select one before continuing.", "No setup selected")

    def __pause_btn_evt(self):
        setup = self.setup
        if self._pause_btn.checked:
            self._pause_btn.label = 'Resume'
            setup.pause_trial()
        else:
            setup.resume_trial()
            self._pause_btn.label = 'Pause'


if __name__ == '__main__':
    pyforms.start_app(EmulatorGUI, geometry=(0, 0, 300, 300))
