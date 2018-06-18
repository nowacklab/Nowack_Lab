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

    _measuremode = None
    _displaymode = None

    _sweepmode = None
    _freqmin = None
    _freqmax = None
    _numpoints = None

    _averaging_factor = None
    _averaging_state = None
    # TODO: stuff for marker positions? or might not need
    # TODO: averaging factor (AVERFACT) and on/off AVERO and restart AVERREST
    # TODO: just keep one active channel for now
    # TODO: should not need to explicitly set power range other than init

    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'

        self.write('OPC?;PRES;')  # first, factory preset for convenience
        self.write('SOUP OFF;')  # immediately turn power off and set to -75
        self._power_state = 0
        self.write('PWRRPMAN')  # power range manual
        self.write('POWR11')  # manually change to power range 11
        self.write('POWE -75')
        self._power = -75


    def __getstate__(self):
        self._save_dict = {
        'power state': self._power_state
        'power': self._power
        'sweep mode': self._sweepmode
        'min of frequency sweep': self._freqmin
        'max of frequency sweep': self._freqmax
        'number of frequency points': self._numpoints
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
    def sweep(self, value):
        '''
        Get the sweep mode
        '''
        options = {
        "": "LIN"
        "": "LOG"
        "": "LIST"
        "": "POWER"
        "": "CW"
        }
        if self.ask('LINFREQ?') == 1:
            return "LIN"
        elif self.ask('LOGFREQ?') == 1:
            return "LOG"
        elif self.ask('LISTFREQ?') == 1:
            return "LIST"
        else:
            raise Exception('Driver can only handle linear, log, list sweeps')

    @sweep.setter
    def sweep(self, value):
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
        return float(self.ask('POIN?')

    @numpoints.setter(self, value):
        '''
        Set the number of points in sweep (and wait for clean sweep)
        '''
        vals = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert value in vals, "must be in " + str(vals)
        self.write('OPC?;POIN %f;' %value)
        self._numpoints = value

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

    def respond(self):
        print("response")
    def write(self, msg):
        self._visa_handle.write(msg)
