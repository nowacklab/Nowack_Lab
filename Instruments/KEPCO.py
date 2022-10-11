import visa
import numpy as np
import time
from .instrument import Instrument, VISAInstrument

class kepcoBOP(VISAInstrument):
    _label = 'kepcoBOP'
    '''
    Instrument driver for KEPCO BOP
    '''


    def __init__(self, address = ''):
        if address == '':
            self.address = 'TCPIP0::192.168.69.191::5025::SOCKET'
        self._init_visa(self.address, termination='\r\n')
        #self._inst.timeout = 10000


    def __getstate__(self):
        return {
                'current setpoint': self.Iout,
                'voltage setpoint': self.Vout,
                'actual voltage output': self.V,
                'actual current output': self.I,
                'output':self.output,
                'source mode': self.source
            }
        return self._save_dict


    def __setstate__(self, state):
        pass

    @property
    def source(self):
        '''
        Get the source mode.
        '''
        options = {
            '0': "V",
            '1': "I",
        }
        return options[self.ask('SOUR:FUNC:MODE?', timeout = 10000)]

    @source.setter
    def source(self, value):
        '''
        Set the source mode.
        '''
        if value in [1, 'current', 'I']:
            value = 'CURR'
        elif value == [0,'voltage', 'V']:
            value = 'VOLT'
        else:
            raise Exception('Command not understood')
        self.write('SOUR:FUNC:MODE %s' %value)

    @property
    def I(self):
        '''
        Get the actual current.
        '''
        return float(self.ask('MEAS:CURR?', timeout = 10000))

    @property
    def Iout(self):
        '''
        Get the current setpoint.
        '''
        self._Iout = float(self.ask('CURR?', timeout = 10000))
        return self._Iout


    @Iout.setter
    def Iout(self, value):
        '''
        Set the current setpoint.
        '''
        self.write('CURR %.4E' %value)
        self._Iout = value

    @property
    def V(self):
        '''
        Get the actual voltage.
        '''
        return float(self.ask('MEAS:VOLT?', timeout = 10000))

    @property
    def Vout(self):
        '''
        Get the output voltage (if in voltage source mode).
        '''
        self._Vout = float(self.ask('VOLT?', timeout = 10000))
        return self._Vout

    @Vout.setter
    def Vout(self, value):
        '''
        Set the output voltage (if in voltage source mode).
        '''
        self.write('VOLT %.4E' %value)
        self._Vout = value


    @property
    def output(self):
        '''
        Check whether or not output is enabled
        '''
        self._output = {0: 'off', 1:'on'}[int(self.ask('OUTP?', timeout = 10000))]
        return self._output

    @output.setter
    def output(self, value):
        '''
        Enable or disable output.
        '''
        status = 1 if value in (True, 1, 'on') else 0
        self.write('OUTP %s' %status)
        self._output = value
