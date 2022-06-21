import visa
import numpy as np
import time
import math
from .instrument import Instrument


class VNA8722ES(Instrument):
    _label = 'VNA_ES'
    """Instrument driver for HP 8722ES Vector Network Analyzer"""
# TODO: more safety precautions re: VNA source power and amplifier/squid limitations
    _power_state = None
    _power = None

    _networkparam = None  # which network parameter: 'S11' 'S21' 'S12' 'S22'
    _savemode = None  # e.g. FORM4
    _sweepmode = None
    _freqmin = None
    _freqmax = None
    _numpoints = None
    _sweeptime = None

    _cw_freq = None     # for continuous wave time trace

    _averaging_state = None
    _averaging_factor = None

    _smoothing_state = None
    _smoothing_factor = None

    _if_bandwidth = None

    # TODO: fix all @property things: should query then set and return etc.
    # TODO: need to change preset: dangerous to have it jump to -10dB with source power with preset command
    def __init__(self, gpib_address=16):
        # FIXME: is gpib_address always going to be 16?
        # FIXME: need to initialize other attributes too
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address, read_termination='a')
        self._visa_handle.read_termination = '\n'

        self.write('SOUP OFF;')  # immediately turn power off and set to -75
        self._power_state = 0
        self.write('PWRRPMAN')  # power range manual
        self.write('POWR11')  # manually change to power range 11
        self.write('POWE -75')
        self._power = -75

        self.write('S21')  # set to measure transmission forward
        self._networkparam = 'S21'
        self._sweepmode = 'LINFREQ' # mode is linear frequency sweep
        self._freqmin = .05e9   # set to max range
        self._freqmax = 40.05e9
        self._numpoints = int(float(self.ask('POIN?')))  # necessary because number of points doesn't reset
        self._sweeptime = 1  # sweep time to 1 second
        self._sweeptime = float(self.ask('SWET?'))
        self._averaging_state = 0
        self._averaging_factor = 16

        self._cw_freq = 1e9

        self._smoothing_state = 1 # smoothing on
        self._smoothing_factor = 3  # 3% smoothing '

        self.write('FORM4')
        self._savemode = 'FORM4'
        self.write('SWET 1')
        print("init: power off and at -75dB. Measuring S21. Manual sweep time 1s. Most other settings factory preset.")
        time.sleep(3)

    def factory_preset(self):
        """
        Set vna to factory preset. Dangerous because default is -10dBm with power on; do not call unnecessarily
        """
        self.write('OPC?;PRES;')
        print('Set to factory preset')

    def __getstate__(self):
        self._save_dict = {
                'power state': self._power_state,
                'power': self._power,
                'sweep mode': self._sweepmode,
                'min of frequency sweep': self._freqmin,
                'max of frequency sweep': self._freqmax,
                'number of frequency points': self._numpoints,
                'averaging state': self._averaging_state,
                'averaging factor': self._averaging_factor
        }
        return self._save_dict

        # TODO: should something else be implemented?
    def __setstate__(self, state):
        pass

    @property
    def powerstate(self):
        """Get whether power is on/off 1/0"""
        self._power_state = int(float(self.ask('SOUP?')))
        return self._power_state

    @powerstate.setter
    def powerstate(self, value):
        """Set power to on/off 1/0"""
        val = int(value)
        assert val in [1, 0], "powerstate must be 1 or 0"
        if val == 1:
            self.write('SOUP1')
            print('Turning on VNA source power')
        else:
            self.write('SOUP0')
            print('Powering down VNA')
        self._power_state = val

    @property
    def power(self):
        """Get the power (dBm)"""
        self._power = float(self.ask('POWE?'))
        return self._power

    @power.setter
    def power(self, value):
        """Set the power (dBm)"""
        if value >= -20:
            rangenum = 0
        else:
            rangenum = min(math.floor((-value + 5)/5)-1, 11)
        # print(self.ask('POWE?'))
        self.write('POWR%02d' % rangenum)  # first change power range
        print("Setting power range to %d..." % rangenum)
        time.sleep(8)
        self.write('POWE%f' % value)  # then can change power
        print("Setting power to ", value)
        # print(self.ask('POWE?'))
        self._power = value

    @property
    def sweepmode(self):
        """
        Get the sweep mode
        """
        if self.ask('LINFREQ?') == '1':
            self._sweepmode = "LIN"
        elif self.ask('LOGFREQ?') == '1':
            self._sweepmode = "LOG"
        elif self.ask('LISFREQ?') == '1':
            self._sweepmode = "LIST"
        elif self.ask('CWTIME?') == '1':
            self._sweepmode = "CW"
        else:
            print('Driver can only handle linear, log, list sweeps')
        return self._sweepmode

    @sweepmode.setter
    def sweepmode(self, value):
        """
        Set the sweep mode
        """
        if value == 'LIN':
            value = 'LINFREQ'
            self._sweeptime = 1
        elif value == 'LOG':
            value = 'LOGFREQ'
            self._sweeptime = 1
        elif value == 'LIST':
            value = 'LISTFREQ'
            self._sweeptime = 1
        elif value == 'CW':
            value == 'CWTIME'
        else:
            print('Driver currently only handles linear, log, list, continuous wave (CW)')
        self._sweepmode = value

        # Check stuff here

    @property
    def freqmin(self):
        """
        Get the min frequency
        """
        self._freqmin = float(self.ask('STAR?'))
        return self._freqmin

    @freqmin.setter
    def freqmin(self, value):
        """
        Set min frequency
        """
        assert type(value) is float or int, "frequency must be float or int"
        self.write('STAR %f' % value)
        self._freqmin = value

    @property
    def freqmax(self):
        """Get the stop frequency"""
        self._freqmax = float(self.ask('STOP?'))
        return self._freqmax

    @freqmax.setter
    def freqmax(self, value):
        """Set max frequency"""
        assert type(value) is float or int, "frequency must be float or int"    # TODO replace assert
        self._freqmax = value
        self.write('STOP %f' % value)

    @property
    def numpoints(self):
        """Get the number of points in sweep"""
        self._numpoints = int(float(self.ask('POIN?')))
        return self._numpoints

    @numpoints.setter
    def numpoints(self, value):
        """Set the number of points in sweep (and wait for clean sweep)"""
        vals = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert value in vals, "must be in " + str(vals)
        self.write('OPC?;POIN %f;' % value)
        self._numpoints = value
        if self._sweepmode != "CW":
            self.write('SWET 1')  # set sweep time to 1 second; slower causes problems
        time.sleep(2)
        print("Setting manual sweep time to 1 second")

    @property
    def sweeptime(self):
        self._sweeptime = float(self.ask('SWET?'))
        return self._sweeptime

    @sweeptime.setter
    def sweeptime(self, value):
        """Set sweep time"""
        if self._sweepmode != "CW" and value < 1:
            print("Setting sweep time to 1")
            self.write('SWET 1')
            self._sweeptime = 1
        else:
            self.write('SWET %f' % value)
            self._sweeptime = value

    @property
    def cw_freq(self):
        """Get the frequency used for cw mode"""
        self._cw_freq = float(self.ask('CWFREQ?'))
        return self._cw_freq

    @cw_freq.setter
    def cw_freq(self, value):
        """Set cw frequency"""
        self.write('CWFREQ %f' % value)
        self._cw_freq = value

    @property
    def averaging_state(self):
        """Get averaging state (on/off 1/0)"""
        self._averaging_state = int(float(self.ask('AVERO?')))
        return self._averaging_state

    @averaging_state.setter
    def averaging_state(self, value):
        """Set averaging to on/off 1/0"""
        val = int(value)
        if val == 1:
            self.write('AVEROON')
        elif val == 0:
            self.write('AVEROOFF')
        else:
            print('Must set to on/off 1/0')
        self._averaging_state = value

    @property
    def averaging_factor(self):
        """Get averaging factor"""
        self._averaging_factor = int(float(self.ask('AVERFACT?')))
        return self._averaging_factor

    @averaging_factor.setter
    def averaging_factor(self, value):
        """Set averaging factor, in [0, 999]"""
        assert isinstance(value, int) and 0 <= value <= 999, "Averaging factor should be int in [0, 999]"
        self.write('AVERFACT%s' % value)

    def averaging_restart(self):
        """Restart the measurement averaging"""
        self.write('AVERREST')

    @property
    def smoothing_state(self):
        """Get smoothing state"""
        self._smoothing_state = int(float(self.ask('SMOOO?')))
        return self._smoothing_state

    @smoothing_state.setter
    def smoothing_state(self, value):
        """Set smoothing to on/off 1/0"""
        val = int(value)
        assert val in [1, 0], "smoothing state should be 1 or 0 on/off"
        self.write('SMOOO%d' % val)
        self._smoothing_state = val

    @property
    def smoothing_factor(self):
        """Get smoothing factor"""
        self._smoothing_factor = float(self.ask('SMOOAPER?'))
        return self._smoothing_factor

    @smoothing_factor.setter
    def smoothing_factor(self, value):
        """Set smoothing factor"""
        assert .05 <= value < 20, "value must be between .05 and 20 (%)"
        self.write('SMOOAPER %f' % value)
        self._smoothing_factor = value

    @property
    def networkparam(self):
        """Get which network parameter is being measured"""
        #
        if self.ask('S11') == '1':
            self._networkparam = 'S11'
        elif self.ask('S21') == '1':
            self._networkparam = 'S21'
        elif self.ask('S12') == '1':
            self._networkparam = 'S12'
        elif self.ask('S22') == '1':
            self._networkparam = 'S22'
        return self._networkparam

    @networkparam.setter
    def networkparam(self, value):
        nplist = ['S11', 'S21', 'S12', 'S22']
        assert value in nplist, "Network parameter should be one of " + str(nplist)
        if value == 'S12' or value == 'S22':
            print("Note: sending power out of VNA port 2")
        self.write(value)

    @property
    def if_bandwidth(self):
        """Get the IF bandwidth"""
        self._if_bandwidth = int(self.ask('IFBW?'))
        return self._if_bandwidth

    @if_bandwidth.setter
    def if_bandwidth(self, value):
        """Set the IF bandwidth"""
        self.write('IFBW %d' % value)

    def save_dB(self):
        """Return attenuation data (units are dB) in 1D np array by querying VNA through GPIB commands
        shape of array: 1x(number of frequency sweep points)
        """
        self.write('FORM4')  # Prepare to output correct data format TODO description from programming guide
        self.write('LOGM')  # Temporarily set VNA to log magnitude display to enable saving log magnitude

        self.averaging_restart()
        self.sleep_until_finish_averaging()

        rm = visa.ResourceManager()
        """Important:not actually initializing another instance of this class (i.e. VNA class) because that would temporarily
        set power too high when factory resets."""
        instrument_for_saving = rm.get_instrument('GPIB0::16')
        instrument_for_saving.write('OUTPFORM')  # todo description from programming guide
        rawdata = instrument_for_saving.read(termination='~')  # i.e. character that will never be found in the raw data
        split_rawdata = rawdata.split('\n')     # split into lines, with two values each
        # programming guide says which display format allows which data type read

        dB_array = np.empty((1, self._numpoints))  # 1xn empty array (row vector)

        for i in range(len(split_rawdata)):
            split_line = split_rawdata[i].split(',')
            dB_array[0, i] = float(split_line[0])  # split_line[1] not used in dB case
        return dB_array

    def save_phase(self):
        """Return phase data (units are degrees) in 1D np array by querying VNA through GPIB commands
        shape of array: 1x(number of frequency sweep points)
        """
        self.write('FORM4')
        self.write('PHASE')

        self.averaging_restart()
        self.sleep_until_finish_averaging()

        rm = visa.ResourceManager()
        instrument_for_saving = rm.get_instrument('GPIB0::16')
        instrument_for_saving.write('OUTPFORM')
        rawdata = instrument_for_saving.read('OUTPFORM')
        split_rawdata = rawdata.split('\n')

        phase_array = np.empty((1, self._numpoints))  # 1xn empty array (row vector)
        for i in range(len(split_rawdata)):
            split_line = split_rawdata[i].split(',')
            phase_array[0, i] = float(split_line[0])  # split_line[1] not used in phase case
        return phase_array

    def save_re_im(self):
        """Return real and imaginary parts of VNA response in (2D) np array by querying VNA through GPIB commands
        shape of array: 2x(number of frequency sweep points)
        first row: real parts
        second row: imaginary parts
        """
        self.write('FORM4')  # Prepare the instrument for saving
        self.write('SMIC')

        self.averaging_restart()  # restart the measurement averaging
        self.sleep_until_finish_averaging()  # wait until measurement averaging finished

        # temporary VNA object only for saving
        rm = visa.ResourceManager()
        instrument_for_saving = rm.get_instrument('GPIB0::16')
        instrument_for_saving.write('OUTPFORM')
        rawdata = instrument_for_saving.read('OUTPFORM')
        split_rawdata = rawdata.split('\n')

        Re_Im_array = np.empty((2, self._numpoints))

        for i in range(len(split_rawdata)):
            split_line = split_rawdata[i].split(',')
            Re_Im_array[0, i] = float(split_line[0])  # Real part (first row)
            Re_Im_array[1, i] = float(split_line[1])  # Imaginary part (second row)
        return Re_Im_array

    @staticmethod
    def Re_Im_to_dB(Re_Im_array):
        """Return 1xn np array of attenuation data (units are dB) from 2xn array of Re, Im data"""
        input_shape = np.shape(Re_Im_array)
        assert len(input_shape) == 2 and input_shape[0] == 2, "input should be 2xn array of Re, Im data"
        # assert abs(np.amax(Re_Im_array)) <= 1, "This does not look like Re, Im data (entries should be between -1, 1)"

        dB_array = np.empty((1, input_shape[1]))

        for i in range(input_shape[1]):  # for each frequency point
            # calculate dB from Re, Im
            dB_array[0, i] = 20 * math.log(math.sqrt(Re_Im_array[0, i]**2 + Re_Im_array[1, i]**2), 10)
        return dB_array

    @staticmethod
    def Re_Im_to_phase(Re_Im_array):
        """Return 1xn np array of phase shift data (units are degrees) from 2xn array of Re, Im data
        (use degrees because VNA phase output uses degrees)"""
        input_shape = np.shape(Re_Im_array)
        assert len(input_shape) == 2 and input_shape[0] == 2, "input should be 2xn array of Re, Im data"

        phase_array = np.empty((1, input_shape[1]))

        for i in range(input_shape[1]):  # for each frequency point
            Re = Re_Im_array[0, i]
            Im = Re_Im_array[1, i]
            try:
                phase_radians = math.atan(Im/Re)
            except ZeroDivisionError:
                phase_radians = math.pi/2
            phase_array[0, i] = phase_radians * (180/math.pi)
        return phase_array

    def sleep_until_finish_averaging(self):
        """Sleeps for number of seconds <VNA sweep time>*<averaging factor+2>
        (2 extra sweeps for safety)"""
        sleep_length = float(self.ask('SWET?'))*(self.averaging_factor + 2)
        time.sleep(sleep_length)

    def ask(self, msg, tryagain=True):
        if msg == 'POWR?' or msg == 'PRAN?':
            print("Note: POWR and PRAN do not have query response (i.e. will return 0)")
        try:
            return self._visa_handle.query(msg)  # changed from .ask to .query
        except Exception as e:
            print('Communication error with VNA: ')
            print(e)
            self.close()
            self.__init__(self.gpib_address)
            if tryagain:
                self.ask(msg, False)

    def write(self, msg):
        self._visa_handle.write(msg)

    def close(self):
        self._visa_handle.close()
        del self._visa_handle
