import visa
import numpy as np
import time
from .instrument import Instrument
import math
import matplotlib.pyplot

class VNA8722ES(Instrument):
    _label = 'VNA_ES'
    '''
    Instrument driver for HP 8722ES Vector Network Analyzer
    '''

    _power_state = None
    _power = None

    _networkparam = None  # which network parameter: 'S11' 'S21' 'S12' 'S22'
    _savemode = None  # e.g. FORM4
    _sweepmode = None
    _freqmin = None
    _freqmax = None
    _numpoints = None

    _averaging_state = None
    _averaging_factor = None

    # TODO: stuff for marker positions? or might not need
    # TODO: just keep one active channel for now
    # TODO: should not need to explicitly set power range other than init

    def __init__(self, gpib_address=16):
        # FIXME: is gpib_address always going to be 16?
        # FIXME: need to initialize other attributes too
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address, read_termination='a')
        self._visa_handle.read_termination = '\n'

        self.write('OPC?;PRES;')  # first, factory preset. Know what some attributes are:
        self._networkparam = 'S11'
        self._sweepmode = 'LINFREQ'
        self._freqmin = .05
        self._freqmax = 40.05
        self._numpoints = 201
        self._averaging_state = 0
        self._averaging_factor = 16

        self.write('SOUP OFF;')  # immediately turn power off and set to -75
        self._power_state = 0

        self.write('PWRRPMAN')  # power range manual
        self.write('POWR11')  # manually change to power range 11
        self.write('POWE -75')
        self._power = -75

        self.write('S21')  # set to transmission forward
        self._networkparam = 'S21'

        self.write('FORM4')
        self._savemode = 'FORM4'

        print ("init: power off and at -75dB. all other settings factory preset")

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
    def power(self):
        '''
        Get the power (dBm)
        '''
        return float(self.ask('POWE?'))

    @power.setter
    def power(self, value):
        '''Set the power (dBm)'''
        assert type(value) is float or int
        if value > -10 or value < -80:
            raise Exception('Power should be between -10 and -80 dBm')
        rangenum = min(floor((-value + 5)/5), 11)
        self.write('POWR%d' %rangenum)  # first change power range
        self.write('POWE %f' % value)  # then can change power
        self._power = value

    @property
    def sweepmode(self):
        '''
        Get the sweep mode
        '''
        options = {
        "": "LIN",
        "": "LOG",
        "": "LIST",
        "": "POWER",
        "": "CW"
        }
        if self.ask('LINFREQ?') == str(1):
            return "LIN"
        elif self.ask('LOGFREQ?') == str(1):
            return "LOG"
        elif self.ask('LISFREQ?') == str(1):
            return "LIST"
        else:
            raise Exception('Driver can only handle linear, log, list sweeps')

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
        else:
            raise Exception('Driver currently only handles linear, log, list')
        self.write(value)
        self._sweepmode = value
        # Check stuff here

    @property
    def minfreq(self):
        '''
        Get the min frequency
        '''
        return float(self.ask('STAR?'))

    @minfreq.setter
    def minfreq(self, value):
        '''
        Set min frequency
        '''
        assert type(value) is float or int, "frequency must be float or int"
        if value > maxfreq(self):
            raise Exception('Min frequency cannot be greater than stop frequency')
        self.write('STAR %f' % value)
        self._minfreq = value

    @property
    def maxfreq(self):
        '''
        Get the stop frequency
        '''
        return float(self.ask('STOP?'))

    @maxfreq.setter
    def maxfreq(self, value):
        '''
        Set max frequency
        '''
        assert type(value) is float or int, "frequency must be float or int"
        if value < minfreq(self):
            raise Exception('Max frequency cannot be smaller than min frequency')
        self._maxfreq = value
        self.write('STOP %f' % value)

    @property
    def numpoints(self):
        '''
        Get the number of points in sweep
        '''
        return float(self.ask('POIN?'))

    @numpoints.setter
    def numpoints(self, value):
        '''
        Set the number of points in sweep (and wait for clean sweep)
        '''
        vals = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert value in vals, "must be in " + str(vals)
        self.write('OPC?;POIN %f;' %value)
        self._numpoints = value

    @property
    def averaging_state(self):
        '''Get averaging state (on/off 1/0)'''
        return int(self.ask('AVERO?'))

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

    @property
    def averaging_factor(self):
        '''Get averaging factor'''
        return int(self.ask('AVERFACT?'))

    @averaging_factor.setter
    def averaging_factor(self, value):
        '''Set averaging factor, in [0, 999]'''
        assert isinstance(value, int) and value >= 0 and value <= 999, "Averaging factor should be int in [0, 999]"
        self.write('AVERFACT%s' % value)

    def averaging_restart(self):
        '''Restart the measurement averaging'''
        self.write('AVERREST')

    @property
    def networkparam(self):
        '''Get which network parameter is being measured'''
        if self.ask('S11') == '1':
            return 'S11'
        elif self.ask('S21') == '1':
            return 'S21'
        elif self.ask('S12') == '1':
            return 'S12'
        elif self.ask('S22') == '1':
            return 'S22'

    @networkparam.setter
    def networkparam(self, value):
        nplist = ['S11', 'S21', 'S12', 'S22']
        assert value in nplist, "Network parameter should be one of " + str(nplist)
        if value == 'S12' or value == 'S22':
            raise Exception('Don\'t send current thru amplifer the backwards (just for cold amplifer testing, remove this in code if needed)')
        self.write(value)

    def save(self):
        '''Save data as array'''
        self.write('FORM4')  # Prepare to output correct data format
        self.write('SMIC')  # Use this format so can get both real and imaginary
        rm = visa.ResourceManager()
        secondary = rm.get_instrument('GPIB0::16')
        secondary.write('OUTPFORM')
        s = secondary.read(termination='~')
        s = s.split('\n')
        n_ar = np.empty((self._numpoints, 2))
        for i in range(len(s)):
            splot = s[i].split(',')
            Re = float(splot[0])
            Im = float(splot[1])
            dB = 20*math.log10(math.sqrt(Re**2+Im**2))
            try:
                phase = math.atan(Im/Re)
            except ZeroDivisionError:
                phase = math.pi/2
            n_ar[i][0] = dB
            n_ar[i][1] = phase
        self.write('LOGM')  # switch back to log magnitude format
        return n_ar

    def rfsquid_sweep(self, k_Istart, k_Istop, k_Isteps, v_freqmin, v_freqmax, v_power):
        import .keithley
        k = Keithley2400(23)
        v2 = VNA8722ES(16)

        assert k_Istart < k_Istop, "stop current should be greater than start current"

        # Set up current source
        k.source = 'I'
        k.Iout_range = 2e-6
        k.Iout = k_Istart  # was 1e-6
        k.V_compliance = 20
        k.output= 'on'

        # Set up VNA
        v2.networkparam('S21')  # Set to measure forward transmission
        v2.write('POWE')
        stepsize = (float(k_Istop-k_Istart))/k_Isteps
        for i in range(0, k_Isteps):
            k.Iout = k.Iout + i*stepsize  # increment current

    def ask(self, msg, tryagain=True):
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
        del(self._visa_handle)
