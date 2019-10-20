import visa
import numpy as np
import time
import math
from .instrument import Instrument, VISAInstrument
from .keithley import Keithley2400
import matplotlib.pyplot as plt

class VNA8753D(Instrument):
    """Instrument driver for HP 87353D Vector Network Analyzer
    In programming guide: starting from ~ page 174
    Key Select Codes"""
    _label = 'VNA_D'

    _power_state = None
    _power = None

    _networkparam = None  # which network parameter: 'S11' 'S21' 'S12' 'S22'
    _savemode = None  # e.g. FORM4
    _sweepmode = None
    _minfreq = None
    _maxfreq = None
    _numpoints = None
    _sweeptime = None

    _cw_freq = None     # for continuous wave time trace

    _averaging_state = None
    _averaging_factor = None

    _smoothing_state = None
    _smoothing_factor = None

    _visa_handle = None

    _minfreq = None
    _maxfreq = None

    def __int__(self, gpib_address=16):
        # TODO gpib address may not always be 16, may need to adjust manually
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        else:
            print("invalid GPIB address")
        self.gpib_address = gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address,
            read_termination='a')
        self._visa_handle.read_termination = '\n'

        # TODO: following stuff
        # TODO: should these all use the getter/setters?
        self.write('SOUPOFF') # immediately turn power off
        self._power_state = 0
        self.write('POWE -75') # set to -75 dbm
        self._power = -75
        self.write('PWR PMAN')# set power range to manual
        self.write('PRAN11') # manually change to power range 11
        # From here: continue setting things

    # writing all getters/setters first

    @property
    def powerstate(self):
        """Get whter power is on/off, i.e. 1/0"""
        self._power_state = int(self.ask('SOUP?'))
        return self._power_state

    @powerstate.setter
    def powerstate(self, value):
        """Set power to on/off, i.e. 1/0"""
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

    @power.setter # TODO assuming power ranges same; check this!
    def power(self, value):
        """Set the power (dBm)"""
        assert type(value) is float or int
        if value > -5 or value < -80:
            raise Exception('Power should be between -10 and -80 dBm')
        rangenum = min(math.floor((-value + 5)/5)-1, 11)
        print(self.ask('POWE?'))
        print("float val", str(float(value)))
        self.write('POWR%02d' %rangenum)  # first change power range
        print("Setting power range to %d..." % rangenum)
        time.sleep(8)
        self.write('POWE%f' %value)  # then can change power
        print("Setting power to ", value)
        print(self.ask('POWE?'))
        self._power = value

    @property
    def sweepmode(self):
        """Get the sweep mode"""
        if self.ask('LINFREQ?') == '1':
            self._sweepmode = "LIN"
        elif self.ask('LOGFREQ?') == '1':
            self._sweepmode = "LOG"
        elif self.ask('LISFREQ?') == '1':
            self._sweepmode = "LIST"
        elif self.ask('CWTIME?') == '1':
            self._sweepmode = "CW"
        else:
            print(''' This driver can only handle linear, log, list sweeps.
            If need to use other sweep modes, will have to write the code
            for it''')
        return self._sweepmode

    @sweepmode.setter
    def sweepmode(self, value):
        '''
        Set the sweep mode
        '''
        if value == 'LIN':
            value = 'LINFREQ'
            self._sweeptime = 1 # setting sweep time to 1 second by default
        elif value == 'LOG':
            value = 'LOGFREQ'
            self._sweeptime = 1
        elif value == 'LIST':
            value = 'LISTFREQ'
            self._sweeptime = 1
        elif value == 'CW':
            value = 'CWTIME'
        else:
            print('Driver currently only handles linear, log, list, wave (CW)')
        self._sweepmode = value

    @property
    def minfreq(self):
        """
        Get the min/start frequency of the sweep
        """
        self._minfreq = float(self.ask('STAR?'))
        return self._minfreq

    @minfreq.setter
    def minfreq(self, value):
        '''
        Set min frequency
        '''
        if type(value) is float or int: # frequency must be float or int
            self._minfreq = value
            self.write('STAR %f' % value)
        else:
            print("invalid frequency value, not changing anything")

    @property
    def maxfreq(self):
        """Get the stop frequency"""
        self._maxfreq = float(self.ask('STOP?'))
        return self._maxfreq

    @maxfreq.setter
    def maxfreq(self, value):
        """Set max frequency"""
        if type(value) is float or int: # frequency must be float or int
            self._maxfreq = value
            self.write('STOP %f' % value)
        else:
            print("invalid frequency value, not changing anything")

    @property
    def numpoints(self):
        """Get the number of points in sweep"""
        self._numpoints = int(self.ask('POIN?'))
        return self._numpoints

    @numpoints.setter
    def numpoints(self, value):
        '''Set the number of points in sweep (and wait for clean sweep)'''
        vals = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        if value in vals:
            self.write('OPC?;POIN %f;' % value)
            self._numpoints = value
            if self._sweepmode != "CW":
                self.write('SWET 1')  # set sweep time to 1 second; slower causes problems
                time.sleep(2)
                print("Setting manual sweep time to 1 second")
        else:
            print("invalid number of points, not doing anything")

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
        """
        Get averaging state (on/off 1/0)
        """
        self._averaging_state = int(self.ask('AVERO?'))
        return self._averaging_state

    @averaging_state.setter
    def averaging_state(self, value):
        '''Set averaging to on/off 1/0'''
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
        '''Get averaging factor'''
        self._averaging_factor = int(float(self.ask('AVERFACT?')))
        return self._averaging_factor

    @averaging_factor.setter
    def averaging_factor(self, value):
        '''Set averaging factor, in [0, 999]'''
        assert isinstance(value, int) and value >= 0 and value <= 999, "Averaging factor should be int in [0, 999]"
        self.write('AVERFACT%s' % value)

    def averaging_restart(self):
        """Restart the measurement averaging"""
        self.write('AVERREST')

    @property
    def smoothing_state(self):
        """Get smoothing state"""
        self._smoothing_state = int(self.ask('SMOOO?'))
        return self._smoothing_state

    @smoothing_state.setter
    def smoothing_state(self, value):
        '''Set smoothing to on/off 1/0'''
        val = int(value)
        assert val in [1, 0], "smoothing state should be 1 or 0 on/off"
        self.write('SMOOO%d' %val)
        self._smoothing_state = val

    @property
    def smoothing_factor(self):
        """Get smoothing factor"""
        self._smoothing_factor = float(self.ask('SMOOAPER?'))
        return self._smoothing_factor

    @smoothing_factor.setter
    def smoothing_factor(self, value):
        '''Set smoothing factor'''
        assert value >=.05 and value <20, "value must be between .05 and 20 (%)"
        self.write('SMOOAPER %f' %value)
        self._smoothing_factor = value

    @property
    def networkparam(self):
        """Get which network parameter is being measured"""
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
            raise Exception('''Don\'t send current thru amplifer backwards
            (just for cold amplifer testing, remove this in code if
            situation changes)''')
        self.write(value)



    def save_dB(self):
        """
        Return attenuation data (units are dB) in 1D np array by querying VNA
        through GPIB commands shape of array: 1x(number of frequency
        sweep points)
        """

        self.write('FORM4')  # Prepare to output correct data format
            # TODO description from programming guide
        self.write('LOGM')  # Temporarily set VNA to log magnitude display
        # to enable saving log magnitude

        self.averaging_restart()
        self.sleep_until_finish_averaging()

        rm = visa.ResourceManager()
        '''Important:not actually initializing another instance of this class
        (i.e. VNA class) because that would temporarily
        set power too high when factory resets.'''
        instrument_for_saving = rm.get_instrument('GPIB0::16')
        instrument_for_saving.write('OUTPFORM')
        # todo description from programming guide
        rawdata = instrument_for_saving.read(termination='~')
        # i.e. character that will never be found in the raw data
        split_rawdata = rawdata.split('\n')
        # split into lines, with two values
        # programming guide shows which display format allows
        # which data type read

        dB_array = np.empty((1, self._numpoints))
        # 1xn empty array (row vector)

        for i in range(len(split_rawdata)):
            split_line = split_rawdata[i].split(',')
            dB_array[0, i] = float(split_line[0])
            # split_line[1] not used in dB case
        return dB_array

    def savePhase(self):
        """Not yet implemented; see save_phase in VNA8722ES"""
        pass

    def saveReIm(self):
        """Not yet implemented; see save_Re_Im in VNA8722ES"""

    @staticmethod
    def Re_Im_to_dB(self):
        """not yet implemented"""
        pass

    @staticmethod
    def Re_Im_to_phase(self):
        """not yet implemented"""
        pass

    def factory_preset(self):
        """
        Set VNA to factory preset. Dangerous to do w/ squid because default
        power too high; do not call unnecessarily
        """
        self.write('OPC?;PRES;')
        print("VNA set to factory preset")

    def sleep_until_finish_averaging(self):
        """Sleeps for number of seconds <VNA sweep time>*<averaging factor+2>
        (2 extra sweeps for safety)"""
        sleep_length = float(self.ask('SWET?'))*(self.averaging_factor + 2)
        time.sleep(sleep_length)

    def ask(self, msg, tryagain=True):
        """
        Send GIPB ask command
        """
        '''commented-out; was only applicable to 8722ES, I believe; check
        programming guides if interested
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
        '''

    def write(self, msg):
        '''write the gpib command "msg" to the VNA'''
        self._visa_handle.write(msg)

    def close(self):
        self._visa_handle.close()
        del(self._visa_handle)
