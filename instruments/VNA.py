import visa
import numpy as np
import time
from .instrument import Instrument

class VNA8722ES(Instrument):
    _label = 'VNA_ES'
    '''
    Instrument driver for HP 8722ES Vector Network Analyzer
    '''

    _power_state = None
    _power = None

    _networkparam = None  # which network parameter: 'S11' 'S21' 'S12' 'S22'
    _savemode = None  # e.g. FORM5
    _sweepmode = None
    _freqmin = None
    _freqmax = None
    _numpoints = None

    _averaging_state = None
    _averaging_factor = None

    # TODO: stuff for marker positions? or might not need
    # TODO: averaging factor (AVERFACT) and on/off AVERO and restart AVERREST
    # TODO: just keep one active channel for now
    # TODO: should not need to explicitly set power range other than init

    def checkup(self):
        print("aaa")

    def __init__(self, gpib_address=16):
        # FIXME: is gpib_address always going to be 16?
        # FIXME: need to initialize other attributes too
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
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

        self.write('FORM5')
        self._savemode = 'FORM5'

        print ("init: power off and at -75dB. all other settings factory preset")

    def __getstate__(self):
        self._save_dict = {
        'power state': self._power_state,
        'power': self._power,
        'sweep mode': self._sweepmode,
        'min of frequency sweep': self._freqmin,
        'max of frequency sweep': self._freqmax,
        'number of frequency points': self._numpoints,
        }
        return self._save_dict

        # TODO: should something else be implemented?
    def __setstate__(self, state):
        pass

    # TODO: might want to figure out exactly what this does
    def ask(self, msg, tryagain=True):
        try:
            return self._visa_handle.ask(msg)
        except:
            print('Communication error with VNA')
            self.close()
            self.__init__(self.gpib_address)
            if tryagain:
                self.ask(msg, False)

    @property
    def power(self):
        '''
        Get the power (dBm)
        '''
        return float(self.ask('POWE?'))

    @power.setter
    def power(self, value):
        '''
        Set the power (dBm)
        '''
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
        # TODO: Need to actually set this attribute
    @sweep.setter
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
    def avgstate(self):
        '''Get averaging state (on/off 1/0)'''
        return int(self.ask('AVERO?'))

    @avgstate.setter
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

    def respond(self):
        print("response")
    def write(self, msg):
        self._visa_handle.write(msg)
