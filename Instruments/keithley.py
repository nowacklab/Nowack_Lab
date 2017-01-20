import visa, numpy as np, time
from .instrument import Instrument

class Keithley2400(Instrument):
    _label = 'keithley'
    '''
    Instrument driver for Keithley 2400 Source Meter
    '''
    Iout = None
    Iout_range = None
    I_compliance = None
    Vout = None
    Vout_range = None
    V_compliance = None

    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'
        self.write(':SENS:FUNC \"VOLT\"')
        self.write(':SENS:FUNC \"CURR\"') # set up to sense voltage and current


    def __getstate__(self):
        self._save_dict = {
            'output current': self._Iout,
            'output current range': self._Iout_range,
            'current compliance': self._I_compliance,
            'output voltage': self._Vout,
            'output voltage range': self._Vout_range,
            'voltage compliance': self._V_compliance
        }
        return self._save_dict

    def __setstate__(self, state):
        pass

    def ask(self, msg, tryagain=True):
        try:
            return self._visa_handle.ask(msg)
        except:
            print('Communication error with Keithley')
            self.close()
            self.__init__(self.gpib_address)
            if tryagain:
                self.ask(msg, False)

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
        return options[self.ask(':SOUR:FUNC:MODE?')]

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
        return float(self.ask(':READ?'))

    @property
    def Iout(self):
        '''
        Get the output current (if in current source mode).
        '''
        if self.source != 'I':
            raise Exception('Cannot read source current if sourcing voltage!')
        self._Iout = float(self.ask(':SOUR:CURR:LEV:AMPL?'))
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

    @property
    def Iout_range(self):
        '''
        Get the output current range (if in current source mode).
        '''
        if self.source != 'I':
            raise Exception('Cannot get source current range if sourcing voltage!')
        self._Iout_range = float(self.ask(':SOUR:CURR:RANGE?'))
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
        self._I_compliance = float(self.ask(':SENS:CURR:PROT?'))
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
        return float(self.ask(':READ?'))

    @property
    def Vout(self):
        '''
        Get the output voltage (if in voltage source mode).
        '''
        if self.source != 'V':
            raise Exception('Cannot read source voltage if sourcing current!')
        self._Vout = float(self.ask(':SOUR:VOLT:LEV:AMPL?'))
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
            raise Exception('Output voltage %s too large for range of %s' %(value, self.Vout_range))
        self.write(':SOUR:VOLT:LEV %s' %value)
        self._Vout = value

    @property
    def Vout_range(self):
        '''
        Get the output voltage range (if in voltage source mode).
        '''
        if self.source != 'V':
            raise Exception('Cannot get source voltage range if sourcing current!')
        self._Vout_range = float(self.ask(':SOUR:VOLT:RANGE?'))
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
        self._V_compliance = float(self.ask(':SENS:VOLT:PROT?'))
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


    def beep(self, frequency, duration):
        """ Sounds a system beep.
        :param frequency: A frequency in Hz between 65 Hz and 2 MHz
        :param duration: A time in seconds between 0 and 7.9 seconds
        """
        self.write(":SYST:BEEP %g, %g" % (frequency, duration))


    def close(self):
        '''
        End the visa session.
        '''
        self._visa_handle.close()
        del(self._visa_handle)

    def reset(self):
        '''
        Reset GPIB comms.
        '''
        self.write('status:queue:clear;*RST;:stat:pres;:*CLS;')


    # def sweep_V(self, Vstart, Vend, Vstep=0.1, sweep_rate=0.1):
    #     '''
    #     Sweep voltage from Vstart to Vend at given rate in volts/second.
    #     Do measurements done during the sweep.
    #     '''
    #     delay = Vstep/sweep_rate
    #     numsteps = abs(Vstart-Vend)/Vstep
    #     V = np.linspace(Vstart, Vend, numsteps)
    #     for v in V:
    #         self.Vout = v
    #         self.I # do a measurement to update the screen. This makes it slower than the desired sweep rate.
    #         time.sleep(delay)


    def sweep_V(self, Vstart, Vend, Vstep=.1, sweep_rate=.1):
        '''
        Uses the Keithley's internal sweep function to sweep from Vstart to Vend with a step size of Vstep and sweep rate of sweep_rate volts/second.
        '''
        if Vstart == Vend:
            return
        self.Vout = Vstart

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

        a = self.ask(':READ?') # starts the sweep
        self.write(':SOUR:VOLT:MODE FIXED') # fixed voltage mode
        self.write(':SENS:FUNC:CONC ON') # turn concurrent functions back on
        self.write(':TRIG:COUN 1') # single sample

        self.Vout = Vend # make sure the last voltage is explicit

        self._visa_handle.timeout = old_timeout
        return [float(i) for i in a.split(',')] # not sure what this data represents


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


    def write(self, msg):
        self._visa_handle.write(msg)

    def zero_V(self, sweep_rate=0.1):
        '''
        Ramp down voltage to zero. Sweep rate in volts/second
        '''
        print('Zeroing Keithley voltage...')
        self.sweep_V(self.Vout, 0, .1, sweep_rate)
        print('Done zeroing Keithley.')

class Keithley2400Old(Instrument):
    _label = 'keithley'
    '''
    Instrument driver for Keithley 2400 Source Meter
    '''
    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'


    def __getstate__(self):
        self._save_dict = {'compliance_current': self.compliance_current,
                          'mode': self.mode,
                          'voltage': self.voltage,
                          'voltage_range': self.voltage_range
                          }
        return self._save_dict


    def __setstate__(self, state):
        pass

    def ask(self, msg, tryagain=True):
        try:
            return self._visa_handle.ask(msg)
        except:
            print('Communication error with Keithley')
            self.reset()
            # self.close()
            # self.__init__(self.gpib_address)
            if tryagain:
                self.ask(msg, False)

    @property
    def compliance_current(self):
        '''
        Get the compliance current
        '''
        return float(self.ask(':SENS:CURR:PROT?'))

    @compliance_current.setter
    def compliance_current(self, value):
        '''
        Set the compliance current
        '''
        if abs(value) > 1.05:
            value = np.sign(value)*1.05
        self.write(':SENS:CURR:PROT %s' %value)


    def __getstate__(self):
        self._save_dict = {'compliance_current': self.compliance_current,
                          'mode': self.mode,
                          'voltage': self.voltage,
                          'voltage_range': self.voltage_range
                          }
        return self._save_dict


    def __setstate__(self, state):
        pass


    @property
    def compliance_current(self):
        '''
        Get the compliance current
        '''
        return float(self._visa_handle.ask(':SENS:CURR:PROT?'))

    @compliance_current.setter
    def compliance_current(self, value):
        '''
        Set the compliance current
        '''
        if abs(value) > 1.05:
            value = np.sign(value)*1.05
        self._visa_handle.write(':SENS:CURR:PROT %s' %value)

    @property
    def current(self):
        '''Get the current reading.'''
        if self.output == 'off':
            raise Exception('Need to turn output on to read current!')
        return float(self.ask(':READ?').split(',')[1])

    @property
    def voltage_in(self):
        '''Get the current reading.'''
        return float(self.ask(':READ?').split(',')[0])

    @property
    def voltage(self):
        '''Get the output voltage'''
        return float(self.ask(':SOUR:VOLT:LEV:AMPL?'))

    @voltage.setter
    def voltage(self, value):
        '''Set the voltage.'''
        self.write(':SOUR:VOLT:LEV %s' %value)

    @property
    def mode(self):
        '''Get the source function.'''
        options = {
                "VOLT": "voltage",
                "CURR": "current",
                "MEM": "memory"}
        return options[self.ask(':SOUR:FUNC:MODE?')]

    @mode.setter
    def mode(self, value):
        '''Set the source function'''
        options = {
                "voltage": "VOLT",
                "current": "CURR",
                "memory": "MEM"}
        self.write(':SOUR:FUNC:MODE %s' %options[value])

    @property
    def output(self):
        return {0: 'off', 1:'on'}[int(self.ask('OUTP?'))]

    @output.setter
    def output(self, value):
        status = 'ON' if value in (True, 1, 'on') else 'OFF'
        self.write('OUTP %s' %status)

    @property
    def voltage_range(self):
        return float(self.ask(':SOUR:VOLT:RANGE?'))

    @voltage_range.setter
    def voltage_range(self, value):
        if value == 'auto':
            self.write(':SOUR:VOLT:RANG:AUTO 1')
        else:
            if abs(value) > 210:
                value = np.sign(value) * 210
            self.write(':SOUR:VOLT:RANG:AUTO 0')
            self.write(':SOUR:VOLT:RANG %g' %value)

    @property
    def voltage_range(self):
        return float(self._visa_handle.ask(':SOUR:VOLT:RANGE?'))

    @voltage_range.setter
    def voltage_range(self, value):
        if value == 'auto':
            self._visa_handle.write(':SOUR:VOLT:RANG:AUTO 1')
        else:
            if abs(value) > 210:
                value = np.sign(value) * 210
            self._visa_handle.write(':SOUR:VOLT:RANG:AUTO 0')
            self._visa_handle.write(':SOUR:VOLT:RANG %g' %value)

    def close(self):
        self._visa_handle.close()
        del(self._visa_handle)

    def write(self, msg):
        self._visa_handle.write(msg)

    def zero(self):
        V = np.linspace(self.voltage, 0., abs(self.voltage)/0.01+1) # 100 steps
        for v in V:
            self.voltage = v
            time.sleep(0.01)

if __name__ == '__main__':
    '''
    Example code. Doesn't actually work if you run this file independently.
    '''
    k = Keithley2400(23)

    ## Sourcing a voltage
    k.source = 'V'
    k.Vout_range = 21
    k.Vout = 14
    k.I_compliance = 1e-6
    k.output= 'on'
    print(k.V, k.I)

    k.zero()

    ## Sourcing a current
    k.source = 'I'
    k.Iout_range = 2e-6
    k.Iout = 1e-6
    k.V_compliance = 1
    k.output= 'on'
    print(k.V, k.I)

    k.zero()