# !/usr/bin/python3
# -*- coding: utf-8 -*-

import logging

from confapp import conf as settings
from pybpodapi.bpod.bpod_base import BpodBase
from pybpodapi.bpod.hardware.channels import ChannelType
from pybpodapi.bpod_modules.bpod_module import BpodModule
from pybpodapi.com.arcom import ArCOM, ArduinoTypes
from pybpodapi.com.protocol.recv_msg_headers import ReceiveMessageHeader
from pybpodapi.com.protocol.send_msg_headers import SendMessageHeader
from pybpodapi.exceptions.bpod_error import BpodErrorException

logger = logging.getLogger(__name__)


class BpodCOMProtocol(BpodBase):
    """
    Define command actions that can be requested to Bpod device.

    **Private attributes**

        _arcom
            :class:`pybpodapi.com.arcom.ArCOM`

            ArCOM object that performs serial communication.

    **Methods**

    """

    def __init__(self, serial_port=None, sync_channel=None, sync_mode=None):
        super(BpodCOMProtocol, self).__init__(serial_port, sync_channel, sync_mode)

        self._arcom = None  # type: ArCOM
        self.bpod_com_ready = False

        # used to keep the list of msg ids sent using the load_serial_message function
        self.msg_id_list = [False for i in range(255)]

        if self.serial_port:
            self.open()

    def open(self):
        super(BpodCOMProtocol, self).open()
        self.bpod_com_ready = True

    def close(self):
        if self.bpod_com_ready:
            super(BpodCOMProtocol, self).close()
            self._arcom.close()
            self.bpod_com_ready = False

    def manual_override(self, channel_type, channel_name, channel_number, value):
        """
        Manually override a Bpod channel

        :param ChannelType channel_type: channel type input or output
        :param ChannelName channel_name: channel name like PWM, Valve, etc.
        :param channel_number:
        :param int value: value to write on channel
        """
        if channel_type == ChannelType.INPUT:
            input_channel_name = channel_name + str(channel_number)
            channel_number = self.hardware.channels.input_channel_names.index(input_channel_name)
            try:
                self._bpodcom_override_input_state(channel_number, value)
            except:
                raise BpodErrorException(
                    'Error using manual_override: {name} is not a valid channel name.'.format(name=channel_name))

        elif channel_type == ChannelType.OUTPUT:
            if channel_name == 'Serial':
                self._bpodcom_send_byte_to_hardware_serial(channel_number, value)

            else:
                try:
                    output_channel_name = channel_name + str(channel_number)
                    channel_number = self.hardware.channels.output_channel_names.index(output_channel_name)
                    self._bpodcom_override_digital_hardware_state(channel_number, value)
                except:
                    raise BpodErrorException('Error using manual_override: {name} is not a valid channel name.'.format(
                        name=output_channel_name))
        else:
            raise BpodErrorException('Error using manualOverride: first argument must be "Input" or "Output".')

    def _bpodcom_connect(self, serial_port, baudrate=115200, timeout=1):
        """
        Connect to Bpod using serial connection

        :param str serial_port: serial port to connect
        :param int baudrate: baudrate for serial connection
        :param float timeout: timeout which controls the behavior of read()
        """
        logger.debug("Connecting on port: %s", serial_port)
        self._arcom = ArCOM().open(serial_port, baudrate, timeout)

    def _bpodcom_disconnect(self):
        """
        Signal Bpod device to disconnect now
        """
        logger.debug("Requesting disconnect (%s)", SendMessageHeader.DISCONNECT)

        self._arcom.write_char(SendMessageHeader.DISCONNECT)

        res = self._arcom.read_byte() == b'1'

        logger.debug("Disconnect result (%s)", str(res))
        return res

    # def __bpodcom_check_com_ready(self):
    #    if not self.bpod_com_ready: self.open()

    def _bpodcom_handshake(self):
        """
        Test connectivity by doing an handshake

        :return: True if handshake received, False otherwise
        :rtype: bool
        """

        logger.debug("Requesting handshake (%s)", SendMessageHeader.HANDSHAKE)

        self._arcom.write_char(SendMessageHeader.HANDSHAKE)

        response = self._arcom.read_char()  # Receive response

        logger.debug("Response command is: %s", response)

        return True if response == ReceiveMessageHeader.HANDSHAKE_OK else False

    def _bpodcom_firmware_version(self):
        """
        Request firmware and machine type from Bpod

        :return: firmware and machine type versions
        :rtype: int, int
        """

        logger.debug("Requesting firmware version (%s)", SendMessageHeader.FIRMWARE_VERSION)

        self._arcom.write_char(SendMessageHeader.FIRMWARE_VERSION)

        fw_version = self._arcom.read_uint16()  # type: int
        machine_type = self._arcom.read_uint16()  # type: int

        logger.debug("Firmware version: %s", fw_version)
        logger.debug("Machine type: %s", machine_type)

        return fw_version, machine_type

    def _bpodcom_reset_clock(self):
        """
        Reset session clock
        """
        logger.debug("Resetting clock")

        self._arcom.write_char(SendMessageHeader.RESET_CLOCK)
        return self._arcom.read_byte() == bytes(1)

    def _bpodcom_stop_trial(self):
        """
        Stops ongoing trial (We recommend using computer-side pauses between trials, to keep data uniform)
        """
        logger.debug("Pausing trial")
        self._arcom.write_char(SendMessageHeader.EXIT_AND_RETURN)

    def _bpodcom_pause_trial(self):
        """
        Pause ongoing trial (We recommend using computer-side pauses between trials, to keep data uniform)
        """
        logger.debug("Pausing trial")
        bytes2send = ArduinoTypes.get_uint8_array([ord(SendMessageHeader.PAUSE_TRIAL), 0])
        self._arcom.write_array(bytes2send)

    def _bpodcom_resume_trial(self):
        """
        Resumes ongoing trial (We recommend using computer-side pauses between trials, to keep data uniform)
        """
        logger.debug("Resume trial")
        bytes2send = ArduinoTypes.get_uint8_array([ord(SendMessageHeader.PAUSE_TRIAL), 1])
        self._arcom.write_array(bytes2send)

    def _bpodcom_get_timestamp_transmission(self):
        """
        Return timestamp transmission scheme
        """
        logger.debug("Get timestamp transmission")

        self._arcom.write_char(SendMessageHeader.GET_TIMESTAMP_TRANSMISSION)
        return self._arcom.read_byte()

    def _bpodcom_hardware_description(self, hardware):
        """
        Request hardware description from Bpod

        :param Hardware hardware: hardware
        """

        logger.debug("Requesting hardware description (%s)...", SendMessageHeader.HARDWARE_DESCRIPTION)
        self._arcom.write_char(SendMessageHeader.HARDWARE_DESCRIPTION)

        max_states = self._arcom.read_uint16()  # type: int
        logger.debug("Read max states: %s", max_states)

        cycle_period = self._arcom.read_uint16()  # type: int
        logger.debug("Read cycle period: %s", cycle_period)

        max_serial_events = self._arcom.read_uint8()  # type: int
        logger.debug("Read number of events per serial channel: %s", max_serial_events)

        n_global_timers = self._arcom.read_uint8()  # type: int
        logger.debug("Read number of global timers: %s", n_global_timers)

        n_global_counters = self._arcom.read_uint8()  # type: int
        logger.debug("Read number of global counters: %s", n_global_counters)

        n_conditions = self._arcom.read_uint8()  # type: int
        logger.debug("Read number of conditions: %s", n_conditions)

        n_inputs = self._arcom.read_uint8()  # type: int
        logger.debug("Read number of inputs: %s", n_inputs)

        inputs = self._arcom.read_char_array(array_len=n_inputs)  # type: list(str)
        logger.debug("Read inputs: %s", inputs)

        n_outputs = self._arcom.read_uint8()  # type: int
        logger.debug("Read number of outputs: %s", n_outputs)

        outputs = self._arcom.read_char_array(array_len=n_outputs)  # type: list(str)
        logger.debug("Read outputs: %s", outputs)

        hardware.max_states = max_states
        hardware.cycle_period = cycle_period
        hardware.max_serial_events = max_serial_events
        hardware.n_global_timers = n_global_timers
        hardware.n_global_counters = n_global_counters
        hardware.n_conditions = n_conditions
        hardware.inputs = inputs
        hardware.outputs = outputs  # + ['G', 'G', 'G']

        hardware.live_timestamps = self._bpodcom_get_timestamp_transmission()

    def _bpodcom_enable_ports(self, hardware):
        """
        Enable input ports on Bpod device

        :param list[int] inputs_enabled: list of inputs to be enabled (0 = disabled, 1 = enabled)
        :rtype: bool
        """

        ###### set inputs enabled or disabled #######################################################
        hardware.inputs_enabled = [0] * len(hardware.inputs)

        for j, i in enumerate(hardware.bnc_inputports_indexes):
            hardware.inputs_enabled[i] = settings.BPOD_BNC_PORTS_ENABLED[j]

        for j, i in enumerate(hardware.wired_inputports_indexes):
            hardware.inputs_enabled[i] = settings.BPOD_WIRED_PORTS_ENABLED[j]

        for j, i in enumerate(hardware.behavior_inputports_indexes):
            hardware.inputs_enabled[i] = settings.BPOD_BEHAVIOR_PORTS_ENABLED[j]
        #############################################################################################

        logger.debug("Requesting ports enabling (%s)", SendMessageHeader.ENABLE_PORTS)
        logger.debug("Inputs enabled (%s): %s", len(hardware.inputs_enabled), hardware.inputs_enabled)

        bytes2send = ArduinoTypes.get_uint8_array([ord(SendMessageHeader.ENABLE_PORTS)] + hardware.inputs_enabled)

        self._arcom.write_array(bytes2send)

        response = self._arcom.read_uint8()  # type: int

        logger.debug("Response: %s", response)

        return True if response == ReceiveMessageHeader.ENABLE_PORTS_OK else False

    def _bpodcom_set_sync_channel_and_mode(self, sync_channel, sync_mode):
        """
        Request sync channel and sync mode configuration

        :param int sync_channel: 255 = no sync, otherwise set to a hardware channel number
        :param int sync_mode: 0 = flip logic every trial, 1 = every state
        :rtype: bool
        """

        logger.debug("Requesting sync channel and mode (%s)", SendMessageHeader.SYNC_CHANNEL_MODE)

        bytes2send = ArduinoTypes.get_uint8_array([ord(SendMessageHeader.SYNC_CHANNEL_MODE), sync_channel, sync_mode])

        self._arcom.write_array(bytes2send)

        response = self._arcom.read_uint8()  # type: int

        logger.debug("Response: %s", response)

        return True if response == ReceiveMessageHeader.SYNC_CHANNEL_MODE_OK else False

    def _bpodcom_echo_softcode(self, softcode):
        """
        Send soft code
        """
        logger.debug("Echo softcode")
        self._arcom.write_char(SendMessageHeader.ECHO_SOFTCODE)
        self._arcom.write_char(softcode)

        bytes2send = ArduinoTypes.get_uint8_array([ord(SendMessageHeader.ECHO_SOFTCODE), softcode])
        self._arcom.write_array(bytes2send)

    def _bpodcom_manual_override_exec_event(self, event_index, event_data):
        """
        Send soft code
        """
        logger.debug("Manual override execute virtual event")
        bytes2send = ArduinoTypes.get_uint8_array([ord(SendMessageHeader.MANUAL_OVERRIDE_EXEC_EVENT), event_index, event_data])
        self._arcom.write_array(bytes2send)

    def _bpodcom_override_input_state(self, channel_number, value):
        """
        Manually set digital value on channel

        :param int channel_number: number of Bpod port
        :param int value: value to be written
        """
        logger.debug("Override input state")

        bytes2send = ArduinoTypes.get_uint8_array(
            [ord(SendMessageHeader.MANUAL_OVERRIDE_EXEC_EVENT), channel_number, value])
        self._arcom.write_array(bytes2send)

    def _bpodcom_send_softcode(self, softcode):
        """
        Send soft code
        """
        logger.debug("Send softcode")
        bytes2send = ArduinoTypes.get_uint8_array([ord(SendMessageHeader.TRIGGER_SOFTCODE), softcode])
        self._arcom.write_array(bytes2send)

    def _bpodcom_send_state_machine(self, message):
        """
        Sends state machine to Bpod

        :param list(int) message: TODO
        :param list(int) ThirtyTwoBitMessage: TODO
        """
        # self.__bpodcom_check_com_ready()

        self._arcom.write_array(message)

    def _bpodcom_run_state_machine(self):
        """
        Request to run state machine now
        """
        # self.__bpodcom_check_com_ready()

        logger.debug("Requesting state machine run (%s)", SendMessageHeader.RUN_STATE_MACHINE)

        self._arcom.write_char(SendMessageHeader.RUN_STATE_MACHINE)

    def _bpodcom_get_trial_timestamp_start(self):
        data = self._arcom.read_bytes_array(8)
        self.trial_start_micros = ArduinoTypes.cvt_uint64(b''.join(data))
        return self.trial_start_micros / float(self.hardware.DEFAULT_FREQUENCY_DIVIDER)

    def _bpodcom_read_trial_start_timestamp_seconds(self):
        """
        A new incoming timestamp message is available. Read trial start timestamp in millseconds and convert to seconds.

        :return: trial start timestamp in milliseconds
        :rtype: float
        """
        response = self._arcom.read_uint32()  # type: int

        # print('response', response)
        # logger.debug("Received start trial timestamp in millseconds: %s", response)

        # trial_start_timestamp = response / 1000.0

        return response * self.hardware.times_scale_factor

    def _bpodcom_read_timestamps(self):

        data = self._arcom.read_bytes_array(12)

        n_hw_timer_cyles = ArduinoTypes.cvt_uint32(b''.join(data[:4]))
        trial_end_micros = ArduinoTypes.cvt_uint64(b''.join(data[4:12]))  # / float(self.hardware.DEFAULT_FREQUENCY_DIVIDER)
        trial_end_timestamp = trial_end_micros / float(self.hardware.DEFAULT_FREQUENCY_DIVIDER)
        trial_time_from_micros = trial_end_timestamp - self.trial_start_timestamp
        trial_time_from_cycles = n_hw_timer_cyles/self.hardware.cycle_frequency
        discrepancy = abs(trial_time_from_micros - trial_time_from_cycles)*1000

        return trial_end_timestamp, discrepancy

    def _bpodcom_state_machine_installation_status(self):
        """
        Confirm if new state machine was correctly installed

        :rtype: bool
        """
        # self.__bpodcom_check_com_ready()

        response = self._arcom.read_uint8()  # type: int

        logger.debug("Read state machine installation status: %s", response)

        return True if response == ReceiveMessageHeader.STATE_MACHINE_INSTALLATION_STATUS else False

    def data_available(self):
        """
        Finds out if there is data received from Bpod

        :rtype: bool
        """
        return self._arcom.bytes_available() > 0

    def _bpodcom_read_opcode_message(self):
        """
        A new incoming opcode message is available. Read opcode code and data.

        :return: opcode and data
        :rtype: tuple(int, int)
        """
        response = self._arcom.read_uint8_array(array_len=2)
        opcode = response[0]
        data = response[1]

        logger.debug("Received opcode message: opcode=%s, data=%s", opcode, data)

        return opcode, data

    def _bpodcom_read_alltimestamps(self):
        """
        A new incoming timestamps message is available.
        Read number of timestamps to be sent and then read timestamps array.

        :return: timestamps array
        :rtype: list(float)
        """
        n_timestamps = self._arcom.read_uint16()  # type: int

        timestamps = self._arcom.read_uint32_array(array_len=n_timestamps)

        logger.debug("Received timestamps: %s", timestamps)

        return timestamps

    def _bpodcom_read_current_events(self, n_events):
        """
        A new incoming events message is available.
        Read number of timestamps to be sent and then read timestamps array.

        :param int n_events: number of events to read
        :return: a list with events
        :rtype: list(int)
        """
        current_events = self._arcom.read_uint8_array(array_len=n_events)

        logger.debug("Received current events: %s", current_events)

        return current_events

    def _bpodcom_read_event_timestamp(self):
        v = self._arcom.read_uint32()
        return float(v) * self.hardware.times_scale_factor

    def _bpodcom_load_serial_message(self, serial_channel, message_id, serial_message, n_messages):
        """
        Load serial message on channel

        :param TODO
        :rtype: bool
        """
        # self.__bpodcom_check_com_ready()

        if isinstance(serial_channel, BpodModule):
            serial_channel = serial_channel.serial_port

        self.msg_id_list[message_id] = True

        if len(serial_message) > 3:
            raise BpodErrorException('Error: Serial messages cannot be more than 3 bytes in length.')

        if not (1 <= message_id <= 255):
            raise BpodErrorException('Error: Bpod can only store 255 serial messages (indexed 1-255). You used the message_id {0}'.format(message_id))

        message_container = [serial_channel-1, n_messages, message_id, len(serial_message)] + serial_message

        logger.debug("Requesting load serial message (%s)", SendMessageHeader.LOAD_SERIAL_MESSAGE)
        logger.debug("Message: %s", message_container)

        bytes2send = ArduinoTypes.get_uint8_array([ord(SendMessageHeader.LOAD_SERIAL_MESSAGE)] + message_container)

        self._arcom.write_array(bytes2send)

        response = self._arcom.read_uint8()  # type: int

        logger.debug("Confirmation: %s", response)

        return True if response == ReceiveMessageHeader.LOAD_SERIAL_MESSAGE_OK else False

    def _bpodcom_reset_serial_messages(self):
        """
        Reset serial messages on Bpod device

        :rtype: bool
        """
        logger.debug("Requesting serial messages reset (%s)", SendMessageHeader.RESET_SERIAL_MESSAGES)

        self._arcom.write_char(SendMessageHeader.RESET_SERIAL_MESSAGES)

        response = self._arcom.read_uint8()  # type: int

        logger.debug("Confirmation: %s", response)

        return True if response == ReceiveMessageHeader.RESET_SERIAL_MESSAGES else False

    def _bpodcom_override_digital_hardware_state(self, channel_number, value):
        """
        Manually set digital value on channel

        :param int channel_number: number of Bpod port
        :param int value: value to be written
        """

        bytes2send = ArduinoTypes.get_uint8_array(
            [ord(SendMessageHeader.OVERRIDE_DIGITAL_HW_STATE), channel_number, value])
        self._arcom.write_array(bytes2send)

    def _bpodcom_send_byte_to_hardware_serial(self, channel_number, value):
        """
        Send byte to hardware serial channel 1-3

        :param int channel_number:
        :param int value: value to be written
        """
        bytes2send = ArduinoTypes.get_uint8_array(
            [ord(SendMessageHeader.SEND_TO_HW_SERIAL), channel_number, value]
        )
        self._arcom.write_array(bytes2send)

    @property
    def hardware(self):
        # self.__bpodcom_check_com_ready()
        return BpodBase.hardware.fget(self)  # type: Hardware

    @property
    def modules(self):
        # self.__bpodcom_check_com_ready()
        return BpodBase.modules.fget(self)

    # @property
    # def inputs(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.inputs.fget(self)

    # @property
    # def outputs(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.outputs.fget(self)

    # @property
    # def channels(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.channels.fget(self)

    # @property
    # def max_states(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.max_states.fget(self)

    # @property
    # def max_serial_events(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.max_serial_events.fget(self)

    # @property
    # def inputs_enabled(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.inputs_enabled.fget(self)

    # @property
    # def cycle_period(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.cycle_period.fget(self)

    # @property
    # def n_global_timers(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.n_global_timers.fget(self)

    # @property
    # def n_global_counters(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.n_global_counters.fget(self)

    # @property
    # def n_conditions(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.n_conditions.fget(self)

    # @property
    # def n_uart_channels(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.n_uart_channels.fget(self)

    # @property
    # def firmware_version(self):
    #   return BpodBase.firmware_version.fget(self)

    # @property
    # def machine_type(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.machine_type.fget(self)

    # @property
    # def cycle_frequency(self):
    #   self.__bpodcom_check_com_ready()
    #   return BpodBase.cycle_frequency.fget(self)
