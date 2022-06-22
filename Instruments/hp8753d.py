import visa
import numpy as np
import time
import math
from .instrument import Instrument, VISAInstrument
import warnings

class VNA8753D(VISAInstrument):
    '''
    Instrument driver for HP 87353D Vector Network Analyzer
    In programming guide: starting from ~ page 174
    Key Select Codes
    '''
    _label = 'HP_8753D_VNA'

    # Higher ranges span lower powers, so look at higher ranges first
    ranges = [r for r in reversed(range(8))]
    range_powers = {r: (-15 - 10*r, +10 - 10*r) for r in ranges}

    def __init__(self, gpib_address = 16):
        self._gpib_address = gpib_address
        self._init_visa('GPIB::%02i::INSTR' %gpib_address)
        self.source_power_on = False

    @property
    def power_range_auto(self):
        q = self.query('PWRR?')
        if q == '0':
            self._power_range_auto = False
        elif q == '1':
            self._power_range_auto = True
        else:
            raise RuntimeError('Unexpected response for power range (auto / manual)')
        return self._power_range_auto

    @power_range_auto.setter
    def power_range_auto(self, isauto):
        if isauto == True:
            self.write('PWRR PAUTO')
        elif isauto == False:
            self.write('PWRR PMAN')
        else:
            raise TypeError('Expected isauto to be a bool')
        self._power_range_auto = isauto

    @property
    def power_range(self):
        for r in self.ranges:
            q = self.query('PRAN%d?' %r) 
            if q == '1':
                self._power_range = r
                return r
        raise RuntimeError('No power range was set (invalid instrument state)')

    @power_range.setter
    def power_range(self, value):
        assert value in self.ranges, "Power range must in " + str(self.ranges)
        self.write('PRAN%d' %value)
        self._power_range = value

    @property
    def source_power_on(self):
        '''
        Source power state.
          1: on
          0: off
        '''
        state = self.query('SOUP?')
        if state == '0':
            self._source_power_on = False
        elif state == '1':
            self._source_power_on = True
        else:
            raise RuntimeError('Invalid source power state')
        return self._source_power_on

    @source_power_on.setter
    def source_power_on(self, value):
        """Set power to on/off, i.e. True/False"""
        if type(value) != bool:
            raise TypeError('Source power must be on (True) or off (False)')
        if value:
            self.write('SOUP1')
        else:
            self.write('SOUP0')
        self._source_power_on = value

    @property
    def power(self):
        """Get the power (dBm)"""
        self._power = float(self.query('POWE?'))
        return self._power

    @power.setter
    def power(self, value):
        """Set the power (dBm)"""
        assert type(value) is float or int
        if value < -80.0 or -10.0 < value:
            raise ValueError('Power should be between -10 and -80 dBm')

        r = self.power_range
        Pmin, Pmax = self.range_powers[r]
        if self.power_range_auto or (Pmin <= value and value <= Pmax):
            self.write('POWE %f' %value)
            self._power = value
        else:
            raise ValueError('Cannot set power to {} dBm with range {} ({} to {} dBm)' \
                    .format(value, r, Pmin, Pmax))

    @property
    def sweepmode(self):
        """Get the sweep mode"""
        if self.query('LINFREQ?') == '1':
            self._sweepmode = "LIN"
        elif self.query('LOGFREQ?') == '1':
            self._sweepmode = "LOG"
        elif self.query('LISFREQ?') == '1':
            self._sweepmode = "LIST"
        elif self.query('CWTIME?') == '1':
            self._sweepmode = "CW"
        else:
            raise NotImplementedError('''
            This driver can only handle linear, log, list sweeps.
            If need to use other sweep modes, will have to write the code
            for it.
            ''')
        return self._sweepmode

    @sweepmode.setter
    def sweepmode(self, value):
        '''
        Set the sweep mode
        '''
        if value == 'LIN':
            value = 'LINFREQ'
        elif value == 'LOG':
            value = 'LOGFREQ'
        elif value == 'LIST':
            value = 'LISTFREQ'
        elif value == 'CW':
            value = 'CWTIME'
        else:
            raise NotImplementedError('''
            Driver currently only handles linear, log, list, wave (CW).
            ''')
        self._sweepmode = value

    @property
    def minfreq(self):
        """
        Get the min/start frequency of the sweep
        """
        self._minfreq = float(self.query('STAR?'))
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
        self._maxfreq = float(self.query('STOP?'))
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
        self._numpoints = int(float(self.query('POIN?')))
        return self._numpoints

    @numpoints.setter
    def numpoints(self, value):
        '''Set the number of points in sweep (and wait for clean sweep)'''
        vals = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        if value in vals:
            self.write('OPC?;POIN %f;' % value)
            self._numpoints = value
            if self.sweepmode != "CW" and self.sweeptime < 1.0:
                self.write('SWET 1')  # set sweep time to 1 second; slower causes problems
                print("Setting manual sweep time to 1 second")
        else:
            raise ValueError('numpoints {} not in {}'.format(value, vals))

    @property
    def sweeptime(self):
        self._sweeptime = float(self.query('SWET?'))
        return self._sweeptime

    @sweeptime.setter
    def sweeptime(self, value):
        """Set sweep time"""
        if self.sweepmode != "CW" and value < 1:
            print("Setting sweep time to 1")
            self.write('SWET 1')
            self._sweeptime = 1
        else:
            self.write('SWET %f' % value)
            self._sweeptime = value

    @property
    def cw_freq(self):
        """Get the frequency used for cw mode"""
        self._cw_freq = float(self.query('CWFREQ?'))
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
        self._averaging_state = int(self.query('AVERO?'))
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
        self._averaging_factor = int(float(self.query('AVERFACT?')))
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
        self._smoothing_state = int(self.query('SMOOO?'))
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
        self._smoothing_factor = float(self.query('SMOOAPER?'))
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
        networkparams = ['S11', 'S21', 'S12', 'S22']
        for param in networkparams:
            if self.query('{}?'.format(param)) == '1':
                self._networkparam = param
                return self._networkparam
        raise RuntimeError('No network parameters are being measured')

    @networkparam.setter
    def networkparam(self, value):
        networkparams = ['S11', 'S21', 'S12', 'S22']
        assert value in networkparams, "Network parameter should be one of " + str(networkparams)
        if value == 'S12' or value == 'S22':
            raise ValueError('''
            Don't send current thru amplifer backwards.
            (For cold amplifer testing, remove this in code if situation changes.)
            ''')
        self.write(value)

    @property
    def IF_bandwidth(self):
        'The IF bandwidth in Hz.'
        return float(self.query('IFBW?')) #Hz

    @IF_bandwidth.setter
    def IF_bandwidth(self, value):
        v = int(value) # So the user can say 3e3 instead of 3000
        bandwidths = [10, 30, 100, 300, 1000, 3000]
        assert v in bandwidths, "IF bandwidth should be one of " + str(bandwidths)
        self.write('IFBW %dHZ' %v)

    def frequencies(self):
        return np.linspace(self.minfreq, self.maxfreq, num=self.numpoints)

    def log_magnitude(self):
        '''
        Return attenuation data (units are dB) in 1D np array by querying VNA
        through GPIB commands shape of array: 1x(number of frequency
        sweep points)
        '''

        self.write('FORM4')  # Prepare to output correct data format
            # TODO description from programming guide
        self.write('LOGM')  # Temporarily set VNA to log magnitude display
        # to enable saving log magnitude

        if self.averaging_state == 1:
            self.write('NUMG %d' %self.averaging_factor)
        else:
            self.write('SING')
        while self.query('HOLD?') != '1':
            pass

        self.write('OUTPFORM')
        # todo description from programming guide
        rawdata = None
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category = UserWarning)
            rawdata = self.read(termination='~')
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
        return dB_array[0]

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

    def sleep_until_finish_averaging(self, extra = 0.0):
        """Sleeps for number of seconds <VNA sweep time>*<averaging factor+extra>
        (<extra> extra sweep for safety)"""
        sleep_length = self.sweeptime * (self.averaging_factor + extra)
        time.sleep(sleep_length) #s

