class Keithley2600(Instrument):
    '''
    Instrument driver for Keithley 2600-model Source Meter (tested with 2636A)
    '''
    def __init__(self, gpib_address='', name='sourcemeter'):
        self._units = {'current': 'A','voltage': 'V'}
        self._visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        super(Keithley2600, self).__init__(name)

    @property
    def currentA(self):
        '''Get the current reading for channel A.'''
        return float(self._visa_handle.query('print(smua.measure.i())'))
    @property
    def currentB(self):
        '''Get the current reading for channel B.'''
        return float(self._visa_handle.query('print(smub.measure.i())'))
    @currentA.setter
    def currentA(self, value):
        '''Set the source current for channel A.'''
        self._visa_handle.write('smua.source.func=smua.OUTPUT_DCAMPS;smua.source.leveli=%s' % value)
    @currentB.setter
    def currentB(self, value):
        '''Set the source current for channel B.'''
        self._visa_handle.write('smub.source.func=smub.OUTPUT_DCAMPS;smub.source.leveli=%s' % value)

    @property
    def voltageA(self):
        '''Get the voltage reading for channel A'''
        return float(self._visa_handle.query('print(smua.measure.v())'))
    @property
    def voltageB(self):
        '''Get the voltage reading for channel B'''
        return float(self._visa_handle.query('print(smub.measure.v())'))
    @voltageA.setter
    def voltageA(self, value):
        '''Set the source voltage for channel A.'''
        self._visa_handle.write('smua.source.func=smua.OUTPUT_DCVOLTS;smua.source.levelv=%s' % value)
    @voltageB.setter
    def voltageB(self, value):
        '''Set the source voltage for channel B.'''
        self._visa_handle.write('smub.source.func=smub.OUTPUT_DCVOLTS;smub.source.levelv=%s' % value)

    @property
    def modeA(self):
        '''Get the source function for channel A.'''
        return self._visa_handle.query('print(smuA.source.func())')
    @property
    def modeB(self):
        '''Get the source function for channel B.'''
        return self._visa_handle.query('print(smuB.source.func())')
    @modeA.setter
    def modeA(self, value):
        '''Set the source function ('voltage' or 'current') for channel A'''
        value={'voltage':'OUTPUT_DCVOLTS','current':'OUTPUT_DCAMPS'}[value]
        self._visa_handle.write('smua.source.func=smua.%s' % value)
    @modeB.setter
    def modeB(self, value):
        '''Set the source function ('voltage' or 'current') for channel B'''
        value={'voltage':'OUTPUT_DCVOLTS','current':'OUTPUT_DCAMPS'}[value]
        self._visa_handle.write('smub.source.func=smub.%s' % value)

    @property
    def outputA(self):
        '''Gets the source output ('on'/'off'/'highz') for channel A'''
        return {0: 'off', 1:'on', 2: 'highz'}[int(float(self._visa_handle.query('print(smua.source.output)')))]
    @property
    def outputB(self):
        '''Gets the source output ('on'/'off'/'highz')  for channel B'''
        return {0: 'off', 1:'on', 2: 'highz'}[int(float(self._visa_handle.query('print(smub.source.output)')))]
    @outputA.setter
    def outputA(self, value):
        '''Sets the source output ('on'/'off'/'highz') for channel A'''
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('smua.source.output= smua.OUTPUT_%s' %status)
    @outputB.setter
    def outputB(self, value):
        '''Sets the source output ('on'/'off'/'highz') for channel B'''
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('smub.source.output= smub.OUTPUT_%s' %status)

    @property
    def voltagelimitA(self,value):
        '''Get the output voltage compliance limit for channel A'''
        return float(self._visa_handle.query('print(smua.source.limitv'))
    @property
    def voltagelimitB(self,value):
        '''Get the output voltage compliance limit for channel B'''
        return float(self._visa_handle.query('print(smub.source.limitv'))
    @voltagelimitA.setter
    def voltagelimitA(self,value):
        '''Get the output voltage compliance limit for channel A'''
        return self._visa_handle.write('smua.source.limitv=%s' %value)
    @voltagelimitB.setter
    def voltagelimitB(self,value):
        '''Get the output voltage compliance limit for channel B'''
        return self._visa_handle.write('smub.source.limitv=%s' %value)


    @property
    def currentlimitA(self,value):
        '''Get the output current compliance limit for channel A'''
        return float(self._visa_handle.query('print(smua.source.limiti'))
    @property
    def currentlimitB(self,value):
        '''Get the output current compliance limit for channel B'''
        return float(self._visa_handle.query('print(smub.source.limiti'))
    @currentlimitA.setter
    def currentlimitA(self,value):
        '''Get the output current compliance limit for channel A'''
        return self._visa_handle.write('smua.source.limiti=%s' %value)
    @currentlimitB.setter
    def currentlimitB(self,value):
        '''Get the output current compliance limit for channel B'''
        return self._visa_handle.write('smub.source.limiti=%s' %value)

    def resetA(self):
        '''Resets the A channel'''
        self._visa_handle.write('smua.reset()')
    def resetB(self):
        '''Resets the B channel'''
        self._visa_handle.write('smub.reset()')

    def __del__(self):
        self._visa_handle.close()


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


    def sweep_V(self, Vstart, Vend, Vstep=.1, sweep_rate=1):
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

        a = self.query(':READ?') # starts the sweep
        self.write(':SOUR:VOLT:MODE FIXED') # fixed voltage mode
        self.write(':SENS:FUNC:CONC ON') # turn concurrent functions back on
        self.write(':SENS:FUNC \"CURR\"')
        self.write(':TRIG:COUN 1') # single sample

        self.Vout = Vend # make sure the last voltage is explicit

        self._visa_handle.timeout = old_timeout
    #    return [float(i) for i in a.split(',')] # not sure what this data represents


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

    def zero_V(self, Vstep=.1, sweep_rate=1):
        '''
        Ramp down voltage to zero. Sweep rate in volts/second
        '''
        print('Zeroing Keithley voltage...')
        self.sweep_V(self.Vout, 0, Vstep, sweep_rate)
        print('Done zeroing Keithley.')


class Keithley2600(Instrument):
    '''
    Instrument driver for Keithley 2600-model Source Meter (tested with 2636A)
    '''
    def __init__(self, gpib_address='', name='sourcemeter'):
        self._units = {'current': 'A','voltage': 'V'}
        self._visa_handle = visa.ResourceManager().open_resource(gpib_address)
        self._visa_handle.read_termination = '\n'
        super(Keithley2600, self).__init__(name)

    @property
    def currentA(self):
        '''Get the current reading for channel A.'''
        return float(self._visa_handle.query('print(smua.measure.i())'))
    @property
    def currentB(self):
        '''Get the current reading for channel B.'''
        return float(self._visa_handle.query('print(smub.measure.i())'))
    @currentA.setter
    def currentA(self, value):
        '''Set the source current for channel A.'''
        self._visa_handle.write('smua.source.func=smua.OUTPUT_DCAMPS;smua.source.leveli=%s' % value)
    @currentB.setter
    def currentB(self, value):
        '''Set the source current for channel B.'''
        self._visa_handle.write('smub.source.func=smub.OUTPUT_DCAMPS;smub.source.leveli=%s' % value)

    @property
    def voltageA(self):
        '''Get the voltage reading for channel A'''
        return float(self._visa_handle.query('print(smua.measure.v())'))
    @property
    def voltageB(self):
        '''Get the voltage reading for channel B'''
        return float(self._visa_handle.query('print(smub.measure.v())'))
    @voltageA.setter
    def voltageA(self, value):
        '''Set the source voltage for channel A.'''
        self._visa_handle.write('smua.source.func=smua.OUTPUT_DCVOLTS;smua.source.levelv=%s' % value)
    @voltageB.setter
    def voltageB(self, value):
        '''Set the source voltage for channel B.'''
        self._visa_handle.write('smub.source.func=smub.OUTPUT_DCVOLTS;smub.source.levelv=%s' % value)

    @property
    def voltageAsense(self):
        ''' Get the sense voltage for 4-probe test '''
        return float(self._visa_handle.query('print(smua.SENSE_REMOTE'))

    @property
    def voltageBsense(self):
        ''' Get the sense voltage for 4-probe test '''
        return float(self._visa_handle.query('print(smub.SENSE_REMOTE'))

    @property
    def modeA(self):
        '''Get the source function for channel A.'''
        return self._visa_handle.query('print(smuA.source.func())')
    @property
    def modeB(self):
        '''Get the source function for channel B.'''
        return self._visa_handle.query('print(smuB.source.func())')
    @modeA.setter
    def modeA(self, value):
        '''Set the source function ('voltage' or 'current') for channel A'''
        value={'voltage':'OUTPUT_DCVOLTS','current':'OUTPUT_DCAMPS'}[value]
        self._visa_handle.write('smua.source.func=smua.%s' % value)
    @modeB.setter
    def modeB(self, value):
        '''Set the source function ('voltage' or 'current') for channel B'''
        value={'voltage':'OUTPUT_DCVOLTS','current':'OUTPUT_DCAMPS'}[value]
        self._visa_handle.write('smub.source.func=smub.%s' % value)

    @property
    def outputA(self):
        '''Gets the source output ('on'/'off'/'highz') for channel A'''
        return {0: 'off', 1:'on', 2: 'highz'}[int(float(self._visa_handle.query('print(smua.source.output)')))]
    @property
    def outputB(self):
        '''Gets the source output ('on'/'off'/'highz')  for channel B'''
        return {0: 'off', 1:'on', 2: 'highz'}[int(float(self._visa_handle.query('print(smub.source.output)')))]
    @outputA.setter
    def outputA(self, value):
        '''Sets the source output ('on'/'off'/'highz') for channel A'''
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('smua.source.output= smua.OUTPUT_%s' %status)
    @outputB.setter
    def outputB(self, value):
        '''Sets the source output ('on'/'off'/'highz') for channel B'''
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('smub.source.output= smub.OUTPUT_%s' %status)

    @property
    def voltagelimitA(self,value):
        '''Get the output voltage compliance limit for channel A'''
        return float(self._visa_handle.query('print(smua.source.limitv'))
    @property
    def voltagelimitB(self,value):
        '''Get the output voltage compliance limit for channel B'''
        return float(self._visa_handle.query('print(smub.source.limitv'))
    @voltagelimitA.setter
    def voltagelimitA(self,value):
        '''Get the output voltage compliance limit for channel A'''
        return self._visa_handle.write('smua.source.limitv=%s' %value)
    @voltagelimitB.setter
    def voltagelimitB(self,value):
        '''Get the output voltage compliance limit for channel B'''
        return self._visa_handle.write('smub.source.limitv=%s' %value)


    @property
    def currentlimitA(self,value):
        '''Get the output current compliance limit for channel A'''
        return float(self._visa_handle.query('print(smua.source.limiti'))
    @property
    def currentlimitB(self,value):
        '''Get the output current compliance limit for channel B'''
        return float(self._visa_handle.query('print(smub.source.limiti'))
    @currentlimitA.setter
    def currentlimitA(self,value):
        '''Get the output current compliance limit for channel A'''
        return self._visa_handle.write('smua.source.limiti=%s' %value)
    @currentlimitB.setter
    def currentlimitB(self,value):
        '''Get the output current compliance limit for channel B'''
        return self._visa_handle.write('smub.source.limiti=%s' %value)

    def resetA(self):
        '''Resets the A channel'''
        self._visa_handle.write('smua.reset()')
    def resetB(self):
        '''Resets the B channel'''
        self._visa_handle.write('smub.reset()')

    def __del__(self):
        self._visa_handle.close()




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


    def query(self, msg, tryagain=True):
        try:
            return self._visa_handle.query(msg)
        except:
            print('Communication error with Keithley')
            self.reset()
            # self.close()
            # self.__init__(self.gpib_address)
            if tryagain:
                self.query(msg, False)

    @property
    def compliance_current(self):
        '''
        Get the compliance current
        '''
        return float(self.query(':SENS:CURR:PROT?'))

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


    @property
    def compliance_current(self):
        '''
        Get the compliance current
        '''
        return float(self._visa_handle.query(':SENS:CURR:PROT?'))

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
        return float(self.query(':READ?').split(',')[1])

    @property
    def voltage_in(self):
        '''Get the current reading.'''
        return float(self.query(':READ?').split(',')[0])

    @property
    def voltage(self):
        '''Get the output voltage'''
        return float(self.query(':SOUR:VOLT:LEV:AMPL?'))

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
        return options[self.query(':SOUR:FUNC:MODE?')]

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
        return {0: 'off', 1:'on'}[int(self.query('OUTP?'))]

    @output.setter
    def output(self, value):
        status = 'ON' if value in (True, 1, 'on') else 'OFF'
        self.write('OUTP %s' %status)

    @property
    def voltage_range(self):
        return float(self.query(':SOUR:VOLT:RANGE?'))

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
        return float(self._visa_handle.query(':SOUR:VOLT:RANGE?'))

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
