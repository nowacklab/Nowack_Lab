import visa
import numpy as np
import time
import re
from .instrument import Instrument, VISAInstrument

class AH2700A(VISAInstrument):
    '''
    For controlling the Razorbill RP100 power souce, which provides power to the Razorbill strain cell.
    '''
    _label = 'AH2700A'

    def __init__(self, montana=None, gpib_address=''):
        '''
        Pass montana = montana.Montana().
        This will check the temperature to see what voltage we can go.
        If montana is not available, we stay at room temperature limit.
        '''
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address
        self._init_visa(gpib_address, termination='\n')

    def __getstate__(self):
        self._save_dict = {
            'highest voltage': self.voltage,
            'frequency': self.frequency,
            'average time': self.average
        }
        return self._save_dict

    @property
    def voltage(self):
        '''
        Get the highest voltage of the excitation voltage.
        '''
        return float(re.findall("\d+\.\d+", self.ask('SH VO'))[0])

    @voltage.setter
    def voltage(self, V):
        '''
        Set the highest voltage of the excitation voltage.
        '''
        self.write('VO %s' %V)

    @property
    def frequency(self):
        '''
        Get the frequency of the excitation voltage.
        '''
        return float(re.findall("\d+\.\d+", self.ask('SH FR'))[0])

    @frequency.setter
    def frequency(self, f):
        '''
        Set the highest frequency of the excitation voltage.
        '''
        self.write('FR %s' %f)

    @property
    def average(self):
        '''
        Get the average time exponent.
        '''
        return float(re.findall("\d+", self.ask('SH AV'))[0])

    @average.setter
    def average(self, ave):
        '''
        Set the average time exponent.
        '''
        self.write('AV %s' %ave)
    
    @property
    def single(self):
        '''
        Perform a single measurement.
        '''
        return float(re.findall("\d+\.\d+", self.ask('SI'))[1])