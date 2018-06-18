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
    _freqmin = None
    _freqmax = None
    _numpoints = None
    # TODO: stuff for marker positions? or might not need


    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'

        # Immediately set power to off

        # TODO: set up to sense amplitude, phase, etc.?

        self.write('')  # start with RF power off
        def __getstate__(self):
            self._save_dict = {
            'power state': self._power_state
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
            raise Exception('Driver can only handle linear, log, list sweeps.')
        self.write(value)
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
        if value > maxfreq(self):
            raise Exception('Min frequency cannot be greater than stop frequency')
        self._minfreq = value
        self.write('STAR %f' % value)

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
        Set the number of points in sweep (and wait 2 sweep times)
        '''
        self.write('OPC?;POIN %f;' %value)

    @property
    def power(self):
        '''
        Get the power (dBm)
        '''
        return float(self.ask('POWE?'))

    @power.setter(self, value):
        '''
        Set the power (dBm)
        '''
        if power > -10:
            raise Exception('Power should not be greater than -10dBm')
        if power > -60:
            print("Warning: do not send too much to SQUID")
            if (input("continue? (y/n): ")[0]).lower() == "y"
            self.write('POWE %f' % power)
