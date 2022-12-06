import visa
import numpy as np
import time
from .instrument import Instrument, VISAInstrument

class Keysight34461A(VISAInstrument):
    _label = 'keysight'
    '''
    Instrument driver for Keithley 2400 Source Meter
    '''
    Irange = 'AUTO'
    Vrange = 'AUTO'

    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address
        self._init_visa(gpib_address, termination='\n')

    def __getstate__(self):
        self._save_dict = {
            'current range': self.I_range,
            'voltage range': self.V_range,
            'trigger type': self.trigger
        }
        return self._save_dict


    def __setstate__(self, state):
        pass

    @property
    def abort(self):
        '''
        Abort the measurement
        '''
        self.write('ABOR')

    @property
    def initiate(self):
        '''
        Put the instrument in 'wait-for-trigger' state
        '''
        self.write('INIT')

    @property
    def fetch(self):
        '''
        Get the data in the memory without deleting them, after the current measurement is finished
        '''
        return self.ask('FETC?')

    @property
    def r(self, readingsnumber = 2e6):
        '''
        Reads and erases all measurements from reading memory up to the specified number.
        The measurements are read and erased from the reading memory starting with the oldest measurement first.
        '''
        return self.ask('R? '+str(readingsnumber))

    @property
    def read(self):
        '''
        Starts a new set of measurements, waits for all measurements to complete, and transfers all available measurements.
        '''
        return self.ask('READ?')

    @property
    def terminal(self):
        '''
        Ask the instrument which termnial is selected
        '''
        return self.ask('ROUT:TERM?')

    @property
    def trigger(self):
        '''
        Get the trigger type
        '''
        return self.ask('TRIG:SOUR?')


    @trigger.setter
    def trigger(self, triggertype):
        '''
        Set the trigger type
        IMM: trigger immediately once the instrument is put in 'wait-for-trigger' state
        BUS: triggered when sending '*TRG' over the interface after the instrument is put in 'wait-for-trigger' state
        EXT: triggered by external trigger. If a trigger is sent to the instrument before it is ready, it buffers a trigger.
        '''
        self.write('TRIG:SOUR '+triggertype)

    @property
    def triggerdelay(self):
        '''
        Get the trigger delay value in seconds
        '''
        return (self.ask('TRIG:DEL?'))

    @triggerdelay.setter
    def triggerdelay(self, delay):
        '''
        Set the trigger delay time in seconds
        '''
        self.write('TRIG:DEL '+str(delay))

    @property
    def triggerslope(self):
        '''
        Get the trigger slope
        '''
        return self.ask('TRIG:SLOP?')

    @triggerslope.setter
    def triggerslope(self, slope):
        '''
        Set the trigger slope.
        slope = 'POS', 'NEG'
        '''
        self.write('TRIG:SLOP '+slope)

    @property
    def triggercount(self):
        '''
        Get the trigger count. This is how many triggers are taken before returning to 'idle' state.
        '''
        return float(self.ask('TRIG:COUN?'))

    @triggercount.setter
    def triggercount(self, countnumber):
        '''
        Set the trigger count. This is how many triggers are taken before returning to 'idle' state.
        '''
        self.write('TRIG:COUN '+str(countnumber))

    @property
    def samplecount(self):
        '''
        Get the sample count. This indicates how many samples are taken when triggered.
        '''
        return self.ask('SAMP:COUN?')

    @samplecount.setter
    def samplecount(self, samples):
        '''
        Set how many samples are taken when triggered
        '''
        self.write('SAMP:COUN '+str(samples))

    @property
    def samplesource(self):
        '''
        Get the sample timing. Immediate means take a sample after trigger delay time for all samples.
        Timer means take the first sample after trigger delay time and every other sample in an interval defined by sample timer.
        '''
        return self.ask('SAMP:SOUR?')

    @samplesource.setter
    def samplesource(self, source):
        '''
        Set the sample timing. IMM means take a sample after trigger delay time for all samples.
        TIM means take the first sample after trigger delay time and every other sample in an interval defined by sample timer.
        '''
        self.write('SAMP:SOUR '+source)

    @property
    def sampletimer(self):
        '''
        Get a sample interval for timed sampling when the sample count is greater than one.
        '''
        return self.ask('SAMP:TIM?')

    @sampletimer.setter
    def sampletimer(self, timer):
        '''
        Set a sample interval for timed sampling when the sample count is greater than one.
        '''
        self.write('SAMP:TIM '+str(timer))

    @property
    def measurement(self):
        '''
        Get the measurement configuration of function, range, resolution
        '''
        return self.ask('CONF?')

    @measurement.setter
    def measurement(self, function, range = 'DEF', resolution = 'DEF'):
        '''
        Set the measurement configuration
        function = CAP, CURR:AC/DC, RES/FRES, VOLT:AC/DC, VOLT:DC:RATio
        '''
        towrite = 'CONF:'+function+' '+str(range)+' '+str(resolution)
        self.write(towrite)

    @property
    def I(self, type = 'DC', range = Irange, resolution = 'none'):
        '''
        Measure current.
        '''
        self.Irange = range
        towrite = 'MEAS:CURR:'+type+' '+str(range)
        if resolution != 'none':
            towrite = towrite+' '+str(resolution)
        return float(self.ask(towrite))

    @property
    def I_range(self):
        '''
        Get the current range
        '''
        return self.Irange

    @I_range.setter
    def I_range(self, value):
        '''
        Set the current range
        '''
        self.Irange = value

    @property
    def V(self, type = 'DC', range = Vrange, resolution = 'none'):
        '''
        Measure current.
        '''
        self.Vrange = range
        towrite = 'MEAS:VOLT:'+type+' '+str(range)
        if resolution != 'none':
            towrite = towrite+' '+str(resolution)
        return float(self.ask(towrite))

    @property
    def V_range(self):
        '''
        Get the voltage range
        '''
        return self.Vrange

    @V_range.setter
    def V_range(self, value):
        '''
        Set the current range
        '''
        self.Vrange = value

    def reset(self):
        '''
        Reset GPIB comms.
        '''
        self.write('status:queue:clear;*RST;:stat:pres;:*CLS;')
