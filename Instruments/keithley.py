import visa

class Keithley2400():
    '''
    Instrument driver for Keithley 2400 Source Meter
    '''
    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'

    @property
    def current(self):
        '''Get the current reading.'''
        return float(self._visa_handle.ask(':READ?').split(',')[1])

    @property
    def voltage_in(self):
        '''Get the current reading.'''
        return float(self._visa_handle.ask(':READ?').split(',')[0])

    @property
    def voltage(self):
        '''Get the output voltage'''
        return float(self._visa_handle.ask(':SOUR:VOLT:LEV:AMPL?'))

    @voltage.setter
    def voltage(self, value):
        '''Set the voltage.'''
        self._visa_handle.write(':SOUR:VOLT:LEV %s' %value)

    @property
    def mode(self):
        '''Get the source function.'''
        options = {
                "VOLT": "voltage",
                "CURR": "current",
                "MEM": "memory"}
        return options[self._visa_handle.ask(':SOUR:FUNC:MODE?')]

    @mode.setter
    def mode(self, value):
        '''Set the source function'''
        options = {
                "voltage": "VOLT",
                "current": "CURR",
                "memory": "MEM"}
        self._visa_handle.write(':SOUR:FUNC:MODE %s' %options[value])

    @property
    def output(self):
        return {0: 'off', 1:'on'}[int(self._visa_handle.ask('OUTP?'))]

    @output.setter
    def output(self, value):
        status = 'ON' if ((value==True) or (value==1) or (value=='on')) else 'OFF'
        self._visa_handle.write('OUTP %s' %status)

    def close(self):
        self._visa_handle.close()
        del(self._visa_handle)
