import visa
import numpy as np
import time
from .instrument import Instrument, VISAInstrument

class Keithley2400(VISAInstrument):
    _label = 'keithley'
    _idn = 'MODEL 2400'

    '''
    Instrument driver for Keithley 2400 Source Meter
    '''
    _Iout = None
    _Iout_range = None
    _I_compliance = None
    _Vout = None
    _Vout_range = None
    _V_compliance = None
    _rel = None

    def __init__(self, gpib_address='', max_step=0.1, max_sweep=1):
        '''
        Parameters affect sweeps and zeroing
        Max step: maximum sweep step size (V)
        Max sweep: maximum sweep rate (V/s)
        '''
        self.max_step = max_step
        self.max_sweep = max_sweep

        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address

        self._init_visa(gpib_address, termination='\n')

        self.setup()


    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        self._save_dict = {
            'output_current': self._Iout,
            'output_current_range': self._Iout_range,
            'current_compliance': self._I_compliance,
            'output_voltage': self._Vout,
            'output_voltage_range': self._Vout_range,
            'voltage_compliance': self._V_compliance,
        }
        try:
            self._save_dict['input_current'] = self.I
            self._save_dict['input_voltage'] = self.V
        except:
            pass
        return self._save_dict


    @property
    def source(self):
        '''
        Get the source mode.
        '''
        options = {
            "VOLT": "V",
            "CURR": "I",
            "MEM": "memory"
        }
        return options[self.query(':SOUR:FUNC:MODE?')]

    @source.setter
    def source(self, value):
        '''
        Set the source mode.
        '''
        if value == 'current':
            value = 'I'
        elif value == 'voltage':
            value = 'V'
        options = {
            "V": "VOLT",
            "I": "CURR",
            "memory": "MEM"
        }
        self.write(':SOUR:FUNC:MODE %s' %options[value])
        if value == 'V':
            self._Iout = None # just to make it clear that there is no output current
            self._Iout_range = None
            self._V_compliance = None
        elif value == 'I':
            self._Vout = None # just to make it clear that there is no output voltage
            self._Vout_range = None
            self._I_compliance = None
        self._output = 'off'

    @property
    def I(self):
        '''
        Get the input current.
        '''
        if self.output == 'off':
            raise Exception('Need to turn output on to read current!')
        self.write(':FORM:ELEM CURR') # get current reading
        return float(self.query(':READ?'))

    @property
    def Iout(self):
        '''
        Get the output current (if in current source mode).
        '''
        if self.source != 'I':
            raise Exception('Cannot read source current if sourcing voltage!')
        self._Iout = float(self.query(':SOUR:CURR:LEV:AMPL?'))

        return self._Iout


    @Iout.setter
    def Iout(self, value):
        '''
        Set the output current (if in current source mode).
        '''
        if self.output != 'on':
            raise Exception('Output is off, cannot set current!')
        if self.source != 'I':
            raise Exception('Cannot set source current if sourcing voltage!')
        if abs(value) > self.Iout_range:
            raise Exception('Output current %s too large for range of %s' %(value, self.Iout_range))
        self.write(':SOUR:CURR:LEV %s' %value)
        self._Iout = value

        self.V # trigger a reading to update the screen, assuming we measure V

    @property
    def Iout_range(self):
        '''
        Get the output current range (if in current source mode).
        '''
        if self.source != 'I':
            raise Exception('Cannot get source current range if sourcing voltage!')
        self._Iout_range = float(self.query(':SOUR:CURR:RANGE?'))
        return self._Iout_range

    @Iout_range.setter
    def Iout_range(self, value):
        '''
        Set the output current range (if in current source mode).
        '''
        if self.source != 'I':
            raise Exception('Cannot set source current range if sourcing voltage!')
        if value == 'auto':
            self.write(':SOUR:CURR:RANG:AUTO 1')
        else:
            self.write(':SOUR:CURR:RANG:AUTO 0')
            self.write(':SOUR:CURR:RANG %g' %value)
        self._Iout_range = value

    @property
    def I_compliance(self):
        '''
        Get the compliance current (if in voltage source mode).
        '''
        if self.source != 'V':
            raise Exception('Cannot get current compliance if sourcing current!')
        self._I_compliance = float(self.query(':SENS:CURR:PROT?'))
        return self._I_compliance

    @I_compliance.setter
    def I_compliance(self, value):
        '''
        Set the compliance current (if in voltage source mode).
        '''
        if self.source != 'V':
            raise Exception('Cannot set current compliance if sourcing current!')
        self.write(':SENS:CURR:PROT %s' %value)
        self._I_compliance = value

    @property
    def V(self):
        '''
        Get the input voltage.
        '''
        if self.output == 'off':
            raise Exception('Need to turn output on to read voltage!')
        self.write(':FORM:ELEM VOLT') # get voltage reading
        return float(self.query(':READ?'))

    @property
    def Vout(self):
        '''
        Get the output voltage (if in voltage source mode).
        '''
        if self.source != 'V':
            raise Exception('Cannot read source voltage if sourcing current!')
        self._Vout = float(self.query(':SOUR:VOLT:LEV:AMPL?'))
        return self._Vout

    @Vout.setter
    def Vout(self, value):
        '''
        Set the output voltage (if in voltage source mode).
        '''
        if self.output != 'on':
            raise Exception('Output is off, cannot set voltage!')
        if self.source != 'V':
            raise Exception('Cannot set source voltage if sourcing current!')
        if abs(value) > self.Vout_range:
            self.Vout_range *= 1.1  # move up to the next voltage range.
            # raise Exception('Output voltage %s too large for range of %s' %(value, self.Vout_range))
        self.write(':SOUR:VOLT:LEV %s' %value)
        self._Vout = value
        self.I # trigger a reading to update the screen, assuming we measure I


    @property
    def Vout_range(self):
        '''
        Get the output voltage range (if in voltage source mode).
        '''
        if self.source != 'V':
            raise Exception('Cannot get source voltage range if sourcing current!')
        self._Vout_range = float(self.query(':SOUR:VOLT:RANGE?'))
        return self._Vout_range

    @Vout_range.setter
    def Vout_range(self, value):
        '''
        Set the output voltage range (if in voltage source mode).
        '''
        if self.source != 'V':
            raise Exception('Cannot set source voltage range if sourcing current!')
        if value == 'auto':
            self.write(':SOUR:VOLT:RANG:AUTO 1')
        else:
            # if abs(value) > 210: # max voltage output range # better to hear the beep
            #     value = 210
            self.write(':SOUR:VOLT:RANG:AUTO 0')
            self.write(':SOUR:VOLT:RANG %g' %value)
        self._Vout_range = value

    @property
    def V_compliance(self):
        '''
        Get the compliance voltage (if in current source mode).
        '''
        if self.source != 'I':
            raise Exception('Cannot get voltage compliance if sourcing voltage!')
        self._V_compliance = float(self.query(':SENS:VOLT:PROT?'))
        return self._V_compliance

    @V_compliance.setter
    def V_compliance(self, value):
        '''
        Set the compliance voltage (if in current source mode).
        '''
        if self.source != 'I':
            raise Exception('Cannot set voltage compliance if sourcing voltage!')
        self.write(':SENS:VOLT:PROT %s' %value)
        self._V_compliance = value

    @property
    def output(self):
        '''
        Check whether or not output is enabled
        '''
        self._output = {0: 'off', 1:'on'}[int(self.query('OUTP?'))]
        return self._output

    @output.setter
    def output(self, value):
        '''
        Enable or disable output.
        '''
        status = 'ON' if value in (True, 1, 'on') else 'OFF'
        self.write('OUTP %s' %status)
        self._output = value


    def beep(self, frequency, duration):
        """ Sounds a system beep.
        :param frequency: A frequency in Hz between 65 Hz and 2 MHz
        :param duration: A time in seconds between 0 and 7.9 seconds
        """
        self.write(":SYST:BEEP %g, %g" % (frequency, duration))


    def setup(self):
        self.write(':SENS:FUNC \"VOLT\"')
        self.write(':SENS:FUNC \"CURR\"') # set up to sense voltage and current


    @property
    def rel(self):
        '''
        Check whether REL is enabled.
        '''
        self._rel = bool(int(self.query(':CALC2:NULL:STAT?')))
        return self._rel

    @rel.setter
    def rel(self, value):
        '''
        Set value to True to take an offset measurement and enable REL mode.
        Set value to False to disable REL mode.
        '''
        if value == True:
            self.write(':CALC2:NULL:ACQ')
            self.write(':CALC2:NULL:STAT ON')
            self._rel = True
        else:
            self.write(':CALC2:NULL:STAT OFF')
            self._rel = False


    def reset(self):
        '''
        Reset GPIB comms.
        '''
        self.write('status:queue:clear;*RST;:stat:pres;:*CLS;')


    def sweep_V(self, Vstart, Vend, Vstep=None, sweep_rate=None):
        '''
        Uses the Keithley's internal sweep function to sweep from Vstart to Vend
         with a step size of Vstep and sweep rate of sweep_rate volts/second.
        If Vstep and sweep_rate are None, use maxes set in init
        '''
        if Vstep is None:
            Vstep = self.max_step
        if sweep_rate is None:
            sweep_rate = self.max_sweep

        # if within step size of the starting value
        if round(abs(Vstart - Vend), 6) <= Vstep:  # avoid floating point error
            self.Vout = Vend
            return
        self.Vout = Vstart

        print('Sweeping Keithley! %s V to %s V at %s V/s' %(Vstart, Vend, sweep_rate))

        self.write(':SENS:FUNC:CONC OFF') # turn off concurrent functions - so you can't measure both voltage and current simultaneously??
        self.write(':SOUR:VOLT:START %s' %Vstart)
        self.write(':SOUR:VOLT:STOP %s' %Vend)
        self.write(':SOUR:VOLT:STEP %s' %(np.sign(Vend-Vstart)*Vstep)) # need to specify negative step if going backwards
        self.write(':SOUR:VOLT:MODE SWE')
        self.write(':SOUR:SWE:SPAC LIN') # set linear staircase sweep
        numsteps = abs(Vstart-Vend)/Vstep
        delay = Vstep/sweep_rate
        self.write(':TRIG:COUN %s' %numsteps) # number of sweep points
        self.write(':SOUR:DEL %s' %delay) # sleep time between steps

        # Fix timeout issue due to unknown time of sweep
        old_timeout = self._visa_handle.timeout
        self._visa_handle.timeout = None # infinite timeout

        a = self.query(':READ?', timeout=None) # starts the sweep
        self.write(':SOUR:VOLT:MODE FIXED') # fixed voltage mode
        self.write(':SENS:FUNC:CONC ON') # turn concurrent functions back on
        self.write(':SENS:FUNC \"CURR\"')
        self.write(':TRIG:COUN 1') # single sample

        self.Vout = Vend # make sure the last voltage is explicit

        self._visa_handle.timeout = old_timeout

        print('Keithley sweep completed.')
        # return [float(i) for i in a.split(',')] # not sure what this data represents


    def triad(self, base_frequency, duration):
        """ Sounds a musical triad using the system beep.
        :param base_frequency: A frequency in Hz between 65 Hz and 1.3 MHz
        :param duration: A time in seconds between 0 and 7.9 seconds
        """
        self.beep(base_frequency, duration)
        time.sleep(duration)
        self.beep(base_frequency*5.0/4.0, duration)
        time.sleep(duration)
        self.beep(base_frequency*6.0/4.0, duration)


    def zero_V(self, Vstep=None, sweep_rate=None):
        '''
        Ramp down voltage to zero.
        Vstep and sweep_rate if None, will use max set in init
        '''
        Vstep = self.max_step
        sweep_rate = self.max_sweep

        print('Zeroing Keithley voltage...')
        self.sweep_V(self.Vout, 0, Vstep, sweep_rate)
        print('Done zeroing Keithley.')


class Keithley2450(Keithley2400):
    _label = 'keithley'
    _idn = 'MODEL 2450'

    def __init__(self, resource='USB0::0x05E6::0x2450::04110400::INSTR',
                    max_step=0.1, max_sweep=1):
        '''
        Parameters affect sweeps and zeroing
        Max step: maximum sweep step size (V)
        Max sweep: maximum sweep rate (V/s)
        '''
        super().__init__(resource)
        self.I # trigger reading to update screen

    def setup(self):
        # self.write('*LANG SCPI2400') # for Keithley2400 compatibility mode
        super().setup()


    @property
    def I(self):
        '''
        Get the input current.
        '''
        if self.output == 'off':
            raise Exception('Need to turn output on to read current!')
        I = self.query('MEAS:CURR?') # get current reading
        return float(I)


    @property
    def V(self):
        '''
        Get the input voltage.
        '''
        if self.output == 'off':
            raise Exception('Need to turn output on to read voltage!')
        V = self.query('MEAS:VOLT?') # get voltage reading
        return float(V)


    def sweep_V(self, Vstart, Vend, Vstep=None, sweep_rate=None):
        r'''
        Sweep WITHOUT using Keithley internal function to sweep from Vstart to Vend
        with a step size of Vstep and sweep rate of sweep_rate volts/second.
        If Vstep and sweep_rate are None, use maxes set in init
        '''
        if Vstep is None:
            Vstep = self.max_step
        if sweep_rate is None:
            sweep_rate = self.max_sweep

        # if within step size of the starting value
        if round(abs(Vstart - Vend), 6) <= Vstep:  # avoid floating point error
            self.Vout = Vend
            return
        self.Vout = Vstart

        numsteps = int(abs((Vend - Vstart) / Vstep + 1))
        delay = Vstep/sweep_rate

        V = np.linspace(Vstart, Vend, numsteps)
        for v in V:
            self.Vout = v
            time.sleep(delay)


class KeithleyPPMS(Keithley2400):
    def __init__(self, gpib_address, zero_V, ten_V):
        '''
        Keithley multimeter to measure PPMS temperature.
        Can configure 0-10 V scale in PPMS software (Analog Output).
        '''
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'
        self.write(':SAMP:COUN 1')
        self.zero_V = zero_V
        self.ten_V = ten_V

    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        return {
            'output': self.output,
        }

    @property
    def output(self):
        return self.V/10*(self.ten_V-self.zero_V) + self.zero_V # calibration set in PPMS software

    @property
    def V(self):
        return float(self.query(':FETC?'))
