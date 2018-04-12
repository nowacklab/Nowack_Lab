import visa
import numpy as np
import time
from .instrument import Instrument, VISAInstrument

class MDO3024(VISAInstrument):
    _label = 'tek3024'
    '''
    Instrument Driver for MDO3024
    '''
    def __init__(self, gpib_address=False):
        if gpib_address:
            self.gpib_address = gpib_address
        else:
            self.gpib_address = r'USB0::0x0699::0x0408::C030594::INSTR'
        self._init_visa(self.gpib_address, termination='\n')
        self.numpoints =  (float(self.ask('DATA:STOP?')) -
                                        float(self.ask('DATA:START?')))
    @property
    def activechannel(self):
        '''
        Get the active channel
        '''
        return self.ask(':DATA:SOURCE?')

    @activechannel.setter
    def activechannel(self, value):
        '''
        Set the active channel
        '''
        if value not in ['CH1', 'CH2', 'CH3', 'CH4']:
            raise Exception('Must be in the format CH# !')
        self.write(':DATA:SOURCE ' + value)
    @property
    def tracerange(self):
        '''
        Gets the portion of the waveform to be acquired
        '''
        return [self.ask('DATA:START?'), self.ask('DATA:STOP?')]

    @tracerange.setter
    def tracerange(self,value):
        '''
        Sets the portion of the waveform to be transferred
        '''
        self.numpoints = int(value[1])-int(value[0])
        self.write('DATA:START ' + str(value[0]))
        self.write('DATA:STOP ' + str(value[1]))
    @property
    def bytedepth(self):
        '''
        Gets the byte depth of each sample
        '''
        return  self.ask('BYT_NR?')
    @bytedepth.setter
    def bytedepth(self,value):
        '''
        Sets the byte depth
        '''
        self.write('BYT_NR ' + int(value))
    @property
    def encoding(self):
        '''
        Get the encoding
        '''
        return self.ask('DATA:ENC?')
    @encoding.setter
    def encoding(self,value):
        '''
        Sets the encoding. Options are ASCII or BINARY
        '''
        self.write('DATA:ENC ' + value)
    @property
    def waveformsettings(self):
        '''
        Gets the waveform settings string
        '''
        return self.ask('WFMOUTPRE?')
    @property
    def getdata(self):
        '''
        Gets the curve data
        '''
        self.write('HEADER 0')
        ymult = float(self.ask('WFMPRE:YMULT?'))
        yzero = float(self.ask('WFMPRE:YZERO?'))
        yoff = float(self.ask('WFMPRE:YOFF?'))
        xincrt = float(self.ask('WFMPRE:XINCR?'))
        response = self.ask(':CURVE?')
        volts = ymult*(np.array([int(num) for num in response.split(',')])
                        - yoff) + yzero
        return np.array([np.arange(0,(self.numpoints + 1)*xincrt, xincrt),
                                                                        volts])
