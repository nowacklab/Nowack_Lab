'''
Instrument driver for E4402B spectrum analyzer
11/13/2019
'''

import time, numpy as np
from tabulate import tabulate
from .instrument import Instrument, VISAInstrument

import visa

class E4402B(VISAInstrument):
    '''
    Agilent 3 GHz spectrum analyzer
    '''
    _label = 'spectrumanalyzer'

    _output_state = None
    _output = None

    _continuous_state = None

    _bandwidth_state = None
    _bandwidth_result = None
    _bandwidth = None

    _averaging_state = None
    _averaging = None

    _demod_state = None
    _demodtype = None #AM or FM
    _demod_time = None

    _centfreq = None
    _freqspan = None
    _freqstart = None
    _freqstop = None

    _inatten = None
    _inpream_state = None

    _sweeppoints = None
    _sweeptime = None

    _smoothing = None

    def __init__(self, gpib_address = 18):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address
        self.device_id = 'E4402B_GPIB_' + str(self.gpib_address)

        self._visa_handle = visa.ResourceManager().open_resource(
                                        self.gpib_address, read_termination='a')
        self._visa_handle.read_termination = '\n'

        self._output_state = 0
        self._output = -66

        self._continuous_state = 0

        self._bandwidth_state = 0
        self._bandwidth_result = -100
        self._bandwidth = -80

        self._averaging_state = 0
        self._averaging = 100

        self._demod_state = 0
        self.write(':SENS:DEM AM')
        self._demodtype = 'AM'
        self._demod_time = 500

        self._centfreq = '1.5GHz'
        self._freqspan = '3.0GHz'
        self._freqstart = 1e9
        self._freqstop = 3e9

        self._inatten = 10
        self._inpream_state = 0

        self._sweeppoints = 401
        self._sweeptime = 5

        self._smoothing = 3 #minimum, range is 3-number of sweep points

        print('Successfully initialized E4402B')

    def init_visa(self):
        self._visa_handle = visa.ResourceManager().open_resource(
                                                            self.gpib_address)
        self._visa_handle.read_termination = '\n'
        self._visa_handle.write('OUTX 1') #1=GPIB

    def ask(self, cmd, timeout=3000):
        '''
        Default timeout 3000 ms. None for infinite timeout
        '''
        self._visa_handle.timeout = timeout
        return self._visa_handle.ask(cmd);

    def write(self, cmd):
        self._visa_handle.write(cmd)

    def __del__(self):
        '''
        destroy the object and close the visa handle
        '''
        self.close()

    def __getstate__(self):
        self._save_dict = {"center frequency": self._centfreq,
                          "output power": self._output,
                          "input attenuation": self._inatten,
                          "bandwidth": self._bandwidth,
                          "sweep points": self._sweeppoints,
                          "sweep time": self._sweeptime,
                          "smoothing": self._smoothing,
                          "gpib_address": self.gpib_address}
        return self._save_dict

    @property
    def outputstate(self):
        '''
        get whether output is on or off
        '''
        self._output_state = int(float(self.ask(':OUTP:STAT?')))
        return self._output_state

    @outputstate.setter
    def outputstate(self, value):
        '''
        set output on/off
        '''
        value = int(value)
        assert value is 1 or value is 0, "output state must be 1 or 0"
        if value == 1:
            self.write(':OUTP:STAT %i' %value)
            print('turning on source output')
        else:
            self.write(':OUTP:STAT %i' %value)
            print('turning off source output')
        self._output_state = value

    @property
    def output(self):
        '''
        get output power (dBm)
        '''
        self._output = int(float(self.ask(':SOUR:POW:LEV:IMM:AMPL?')))
        return self._output

    @output.setter
    def output(self,value):
        '''
        setting the output power level (dBm) from -66 to 3
        '''
        assert type(value) is int or float, "must be int or float"
        if value > 3:
            raise Exception('Power level can not exceed 3 dBm')
        print('power is currently '+self.ask(':SOUR:POW:LEV:IMM:AMPL?'))
        print('setting power to %i' %value)
        time.sleep(8)
        self.write(':SOUR:POW:LEV:IMM:AMPL %i' %value)
        self._output = value

    @property
    def continuousstate(self):
        '''
        whether continuous sweeps will be taken
        '''
        self._continuous_state = int(float(self.ask(':INIT:CONT?')))
        return self._continuous_state

    @continuousstate.setter
    def continuousstate(self,value):
        '''
        setting the continuous state
        '''
        value = int(value)
        assert value is 1 or value is 0, "state must be 1 or 0"
        if value == 1:
            self.write(':INIT:CONT %i' %value)
            print('turning on continuous state')
        else:
            self.write(':INIT:CONT %i' %value)
            print('turning off continuous state')
        self._continuous_state = value

    @property
    def bandwidthstate(self):
        '''
        get whether the bandwidth measurement function is on or off
        '''
        self._bandwidth_state = int(self.ask(':CALC:BAND:STAT?'))
        return self._bandwidth_state

    @bandwidthstate.setter
    def bandwidthstate(self,value):
        '''
        turn bandwidth measurement on or off
        '''
        value = int(value)
        assert value is 1 or value is 0, "bwidth state must be 1 or 0"
        if value == 1:
            self.write(':CALC:BAND:STAT %i' %value)
            print('turning on bwidth measurement')
        else:
            self.write(':CALC:BAND:STAT %i' %value)
            print('turning off bwidth measurement')
        self._bandwidth_state = value

    @property
    def bandwidth(self):
        '''
        getting the power level at which the signal bwidth will be measured
        '''
        self._bandwidth = self.ask(':CALC:BAND:NDB?')
        return self._bandwidth

    @bandwidth.setter
    def bandwidth(self, value):
        '''
        setting the power level at which the signal bwidth will be measured by
        the markers
        '''
        assert self._bandwidth_state == 1, "bandwidth measurement must be on"
        assert value >= -80 and value <= -1, "allowed range is -80dB to -1dB"
        self.write(':CALC:BAND:NDB %i' %value)
        self._bandwidth = value

    @property
    def bandwidthres(self):
        '''
        getting the value of the bwidth measurement at this pwr level
        '''
        if self._bandwidth_state == 0:
            print('bandwidth state == 0')
            return -100
        else:
            self._bandwidth_result = int(float(self.ask(':CALC:BAND:RES?')))
            return self._bandwidth_result

    @property
    def averagingstate(self):
        '''
        getting the averaging state
        '''
        self._averaging_state = int(float(self.ask(':SENS:AVER:STAT?')))
        return self._averaging_state

    @averagingstate.setter
    def averagingstate(self,value):
        '''
        setting the averaging state
        '''
        value = int(value)
        assert value is 1 or value is 0, "averaging state must be 1 or 0"
        if value == 1:
            self.write(':SENS:AVER:STAT %i' %value)
            print('turning on averaging')
        else:
            self.write(':SENS:AVER:STAT %i' %value)
            print('turning off averaging')
        self._averaging_state = value

    @property
    def averaging(self):
        '''
        getting the current number of averages
        '''
        assert self._bandwidth_state == 1, "bandwidth measurement must be on"
        self._averaging = int(float(self.ask(':SENS:AVER:COUN?')))
        return self._averaging

    @averaging.setter
    def averaging(self,value):
        '''
        setting the number of averages to be taken
        '''
        assert value >= 1 and value <= 8192, "allowed range is 1 to 8192"
        self.write(':SENS:AVER:COUN %i' %value)
        self._averaging = value

    @property
    def demodstate(self):
        '''
        getting whether demodulation is turned on
        '''
        self._demod_state = int(float(self.ask(':SENS:DEM:STAT?')))
        return self._demod_state

    @demodstate.setter
    def demodstate(self,value):
        '''
        setting whether demodulation is turned on or off
        '''
        value = int(value)
        assert value is 1 or value is 0, "demod state must be 1 or 0"
        if value == 1:
            self.write(':SENS:DEM:STAT %i' %value)
            print('turning on demodulation')
        else:
            self.write(':SENS:DEM:STAT %i' %value)
            print('turning off demodulation')
        self._demod_state = value

    @property
    def demodtype(self):
        '''
        getting whether demodulation is AM or FM
        '''
        self._demodtype = self.ask(':SENS:DEM?')
        return self._demodtype

    @demodtype.setter
    def demodtype(self,value):
        '''
        setting the demodulation type
        '''
        self.write(':SENS:DEM %s' %value)
        self._demodtype = value

    @property
    def demodtime(self):
        '''
        getting the demod time
        '''
        self._demod_time = int(float(self.ask(':SENS:DEM:TIME?')))
        return self._demod_time

    @demodtime.setter
    def demodtime(self,value):
        '''
        setting the demod time
        '''
        self.write(':SENS:DEM:TIME %i' %value)
        self._demod_time = value

    @property
    def centerfreq(self):
        '''
        getting the center frequency value
        '''
        self._centfreq = int(float(self.ask(':SENS:FREQ:CENT?')))
        return str(self._centfreq)+'Hz'

    @centerfreq.setter
    def centerfreq(self,value):
        '''
        setting the center frequency
        '''
        self.write(':SENS:FREQ:CENT %i' %value)
        self._centfreq = value

    @property
    def freqspan(self):
        '''
        getting the frequncy span
        '''
        self._freqspan = float(self.ask(':SENS:FREQ:SPAN?'))
        return self._freqspan

    @freqspan.setter
    def freqspan(self,value):
        '''
        setting the frequency span (default unit is Hz)
        '''
        assert value is 0 or value >= 100 and value <= 1.58e9,"invalid span"
        self.write(':SENS:FREQ:SPAN %i' %value)
        self._freqspan = value

    @property
    def freqstart(self):
        '''
        getting the starting frequency
        '''
        self._freqstart = int(float(self.ask(':SENS:FREQ:STAR?')))
        return self._freqstart

    @freqstart.setter
    def freqstart(self,value):
        '''
        setting the starting frequency
        '''
        assert value >= -80e6 and value <= 1.58e9, "value outside range"
        self.write(':SENS:FREQ:STAR %f' %value)
        self._freqstart = value

    @property
    def freqstop(self):
        '''
        getting the stopping frequency
        '''
        self._freqstop = int(float(self.ask(':SENS:FREQ:STOP?')))
        return self._freqstop

    @freqstop.setter
    def freqstop(self,value):
        '''
        setting the stopping frequency
        '''
        assert value >= -80e6 and value <= 3.1e9, "value outside range"
        self.write(':SENS:FREQ:STOP %i' %value)
        self._freqstop = value

    @property
    def inputatten(self):
        '''
        getting input attenuation level
        '''
        pass

    @inputatten.setter
    def inputatten(self,value):
        '''
        setting input attenuation level
        '''
        pass

    @property
    def intpreamp(self):
        '''
        getting whether the internal preamp is on or off
        '''
        pass

    @intpreamp.setter
    def intpreamp(self,value):
        '''
        setting whether the internal preamp is on or off
        '''
        pass

    @property
    def sweeppoints(self):
        '''
        getting number of sweeping points
        '''
        self._sweeppoints = int(float(self.ask(':SENS:SWE:POIN?')))
        return self._sweeppoints

    @sweeppoints.setter
    def sweeppoints(self,value):
        '''
        setting number of sweep points
        '''
        assert value >= 101 and value <= 8192, "invalid sweep range"
        self.write(':SENS:SWE:POIN %i' %value)
        self._sweeppoints = value

    @property
    def sweeptime(self):
        '''
        getting the sweep time
        '''
        self._sweeptime = int(float(self.ask(':SENS:SWE:TIME?')))
        return self._sweeptime

    @sweeptime.setter
    def sweeptime(self,time):
        '''
        setting the sweep time
        '''
        self.write(':SENS:SWE:TIME %i' %time)
        self._sweeptime = time

    @property
    def smoothpoints(self):
        '''
        getting number of points for smoothing
        '''
        self._smoothing = int(float(self.ask(':TRAC:MATH:SMO:POIN?')))
        return self._smoothing

    @smoothpoints.setter
    def smoothpoints(self,value):
        '''
        setting the number of points for smoothing (must be within 3 to the
        current number of sweep points)
        '''
        self.write(':TRAC:MATH:SMO:POIN %i' %value)
        self._smoothing = value

    @property
    def takesweep(self):
        '''
        tells the instrument to take another single sweep, waits for the sweep
        to finish, then retrieves the data from the trace and puts it into a
        list of floats
        '''
        assert self._continuous_state == 0, 'continuous state must be off'
        self.write(':INIT:IMM')
        #self.write('*OPC?')
        time.sleep(self._sweeptime)
        string = self.ask(':TRAC:DATA? TRACE1')
        split = string.split(',')
        tracedata = [float(s) for s in split]
        tracedata = np.array(tracedata)
        start = self._freqstart
        stop = self._freqstop
        freqlist = np.linspace(start,stop,self._sweeppoints)
        final = [tracedata,freqlist]
        return final
