import visa
import numpy as np
import time
from .instrument import Instrument, VISAInstrument

class MDO3024(VISAInstrument):
    _label = 'tek3024'
    '''
    Instrument Driver for MDO3024
    '''
    def __init__(self, usb_address=False):
        if usb_address:
            self.usb_address = usb_address
        else:
            self.usb_address = 'USB0::0x0699::0x0408::C030594::INSTR'
        self._init_visa(self.usb_address, termination='\n')
        self.numpoints =  (float(self.ask('DATA:STOP?')) -
                                        float(self.ask('DATA:START?')))
        self.write('DATA:ENCDG ASCII')
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
        if value not in ['CH1', 'CH2', 'CH3', 'CH4', 'MATH']:
            raise Exception('Must be in the format CH# or MATH!')
        self.write(':DATA:SOURCE ' + value)
    @property
    def tracerange(self):
        '''
        Gets the portion of the waveform to be acquired
        '''
        return [int(self.ask('DATA:START?')), int(self.ask('DATA:STOP?'))]

    @tracerange.setter
    def tracerange(self,value):
        '''
        Sets the portion of the waveform to be transferred
        '''
        self.numpoints = int(value[1])-int(value[0])
        self.write('DATA:START ' + str(value[0]))
        self.write('DATA:STOP ' + str(value[1]))

    @property
    def math_type(self):
        '''
        Gets the current MATH definition
        '''
        return self.ask('MATH:TYPE?')

    @math_type.setter
    def math_type(self, value):
        '''
        Sets the current MATH definition
        '''
        if value not in ["DUAL","FFT","ADV","SPECTRUM"]:
            raise Exception('Must be DUAL, FFT, ADV, or SPECTRUM')
        else:
            self.write('MATH:TYPE' + value)

    @property
    def math_define(self):
        '''
        Gets the math definition.
        '''
        return self.ask('MATH:DEF?')
    @math_define.setter
    def math_define(self, value):
        '''
        Sets the math definition, using the Tek string notation
        '''
        self.write('MATH:DEF \'%s \'' % value)

    @property
    def ch1(self):
        '''
        Gets whether channel 1 is on or off
        '''
        return self.ask('SELECT:CH1?')

    @ch1.setter
    def ch1(self, value):
        '''
        Sets whether channel 1 is on or off
        '''
        if value not in ['ON', 'OFF']:
            raise Exception('Must be ON or OFF')
        self.write('SELECT:CH1 '+value)

    @property
    def ch1scale(self):
        '''
        Gets the scale of channel 1
        '''
        return self.ask('CH1:SCALE?')

    @ch1scale.setter
    def ch1scale(self,value):
        '''
        Sets the scale of channel 1 in volts
        '''
        self.write('CH1:SCALE ' + str(value))
    @property
    def ch2(self):
        '''
        Gets whether channel 2 is on or off
        '''
        return self.ask('SELECT:CH2?')

    @ch2.setter
    def ch2(self, value):
        '''
        Sets whether channel 2 is on or off
        '''
        if value not in ['ON', 'OFF']:
            raise Exception('Must be ON or OFF')
        self.write('SELECT:CH2 '+value)

    @property
    def ch2scale(self):
        '''
        Gets the scale of channel 21
        '''
        return self.ask('CH2:SCALE?')

    @ch2scale.setter
    def ch2scale(self,value):
        '''
        Sets the scale of channel 2 in volts
        '''
        self.write('CH2:SCALE ' + str(value))

    @property
    def ch3(self):
        '''
        Gets whether channel 3 is on or off
        '''
        return self.ask('SELECT:CH3?')

    @ch3.setter
    def ch3(self, value):
        '''
        Sets whether channel 3 is on or off
        '''
        if value not in ['ON', 'OFF']:
            raise Exception('Must be ON or OFF')
        self.write('SELECT:CH3 '+value)

    @property
    def ch3scale(self):
        '''
        Gets the scale of channel 3
        '''
        return self.ask('CH3:SCALE?')

    @ch3scale.setter
    def ch3scale(self,value):
        '''
        Sets the scale of channel 3 in volts
        '''
        self.write('CH3:SCALE ' + str(value))

    @property
    def ch4(self):
        '''
        Gets whether channel 4 is on or off
        '''
        return self.ask('SELECT:CH4?')

    @ch4.setter
    def ch4(self, value):
        '''
        Sets whether channel 4 is on or off
        '''
        if value not in ['ON', 'OFF']:
            raise Exception('Must be ON or OFF')
        self.write('SELECT:CH4 '+value)

    @property
    def ch4scale(self):
        '''
        Gets the scale of channel 4
        '''
        return self.ask('CH4:SCALE?')

    @ch4scale.setter
    def ch4scale(self,value):
        '''
        Sets the scale of channel 4 in volts
        '''
        self.write('CH4:SCALE ' + str(value))

    @property
    def chmath(self):
        '''
        Gets whether channel MATH is on or off
        '''
        return self.ask('SELECT:MATH?')

    @chmath.setter
    def chmath(self, value):
        '''
        Sets whether channel MATH is on or off
        '''
        if value not in ['ON', 'OFF']:
            raise Exception('Must be ON or OFF')
        self.write('SELECT:MATH '+value)

    @property
    def chmathscale(self):
        '''
        Gets the scale of math
        '''
        return self.ask('MATH:SCALE?')

    @chmathscale.setter
    def chmathscale(self,value):
        '''
        Sets the scale of MATH in volts
        '''
        self.ask('MATH:SCALE ' + str(value))

    @property
    def hscale(self):
        '''
        Gets the horizontal scale of the axes
        '''
        return self.ask('HORIZONTAL:SCALE?')

    @hscale.setter
    def hscale(self,value):
        '''
        Sets the horizontal scale of the axes
        '''
        return self.write('HORIZONTAL:SCALE ' + str(value))

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
        self.write('BYT_NR ' + str(value))
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
