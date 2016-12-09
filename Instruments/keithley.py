import visa, numpy as np, time
from .instrument import Instrument

class Keithley2400(Instrument):
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

    def zero(self):
        V = np.linspace(self.voltage, 0., abs(self.voltage)/0.01+1) # 100 steps
        for v in V:
            self.voltage = v
            time.sleep(0.01)
