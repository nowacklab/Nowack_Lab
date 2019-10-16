import visa
import numpy as np
import time
from .instrument import Instrument, VISAInstrument

class powersupply(VISAInstrument):
    _label = 'B&K Precision Model 9201'
    '''
    Instrument driver for B&K Precision Model 9201
    '''
    _Iout = None
    _Iout_range = None
    _I_compliance = None
    _Vout = None
    _Vout_min = None
    _Vout_max = None
    _V_compliance = None

    def __init__(self, usb_address):
        self._init_visa(usb_address, termination='\n')
        self.address = usb_address

    def __getstate__(self):
        self._save_dict = {
            'output current': self.I,
            'output voltage': self.V,
        }
        return self._save_dict

    @property
    def I(self):
        '''
        Get the input current.
        '''
        return float(self.ask(':FETC:CURR?'))

    @property
    def Iout(self):
        '''
        Get the output current.
        '''
        self._Iout = float(self.ask(':SOUR:CURR:LEV:IMM:AMPL?'))

        return self._Iout


    @Iout.setter
    def Iout(self, value):
        '''
        Set the output current (if in current source mode).
        '''
        self.write(':SOUR:CURR:LEV:IMM:AMPL %s' %value)
        self._Iout = value

        self.V # trigger a reading to update the screen, assuming we measure V

    @property
    def V(self):
        '''
        Get the input voltage.
        '''
        return float(self.ask('FETC:VOLT?'))

    @property
    def Vout(self):
        '''
        Get the output voltage (if in voltage source mode).
        '''
        self._Vout = float(self.ask(':SOUR:VOLT:LEV:IMM:AMPL?'))
        return self._Vout

    @Vout.setter
    def Vout(self, value):
        '''
        Set the output voltage (if in voltage source mode).
        '''
        self.write(":SOUR:VOLT:LEV:IMM:AMPL %s" %value)
        self._Vout = value
        self.I # trigger a reading to update the screen, assuming we measure I


    @property
    def Vout_range(self):
        '''
        Get the output max.
        '''
        self._Vout_min = float(self.ask('VOLT:LIMI?'))
        return self._Vout_max

    @Vout_range.setter
    def Vout_range(self, maxvolts):
        '''
        Set the output voltage range.
        '''
        self.write('VOLT:LIMI %s' % maxvolts)
        self._Vout_max = maxvolts

    @property
    def output(self):
        '''
        Check whether or not output is enabled
        '''
        self._output = {0: 'off', 1:'on'}[int(self.ask('OUTP?'))]
        return self._output

    @output.setter
    def output(self, value):
        '''
        Enable or disable output.
        '''
        status = 'ON' if value in (True, 1, 'on') else 'OFF'
        self.write('OUTP %s' %status)
        self._output = value
