'''
Instrument base classes.
'''
import visa

class Instrument:
    _label = 'instrument'

    def __getstate__(self):
    	return self.__dict__

    def __setstate__(self, state):
        '''
        Recommended to write custom setstates for subclasses to avoid loading
        directly into properties and write values directly to instrument.
        '''
        self.__dict__.update(state)


class VISAInstrument(Instrument):
    _label = 'VISAinstrument'
    _idn = None

    def __del__(self):
        '''
        Destroy the object and close the visa handle
        '''
        self.close()

    def _init_visa(self, resource, termination='\n'):
        r'''
        Initialize the VISA connection.
        Pass in the resource name. This can be:
        - GPIB Address
            GPIB::##::INSTR
        - TCPIP Socket
            TCPIP::host address::port::SOCKET
        - COM port
            COM#
        - Or many others...
            See https://pyvisa.readthedocs.io/en/stable/names.html
        termination: e.g. \r\n: read termination.
        '''
        self._visa_handle = visa.ResourceManager().open_resource(resource)
        self._visa_handle.read_termination = termination
        if self._idn is not None:
            idn = self.ask('*IDN?')
            if self._idn not in idn:
                raise Exception('Instrument not recognized. Expected string %s in *IDN?: %s' %(self._idn, idn))

    def ask(self, cmd, timeout=3000):
        '''
        Write and read combined operation.
        Default timeout 3000 ms. None for infinite timeout
        Strip terminating characters from the response.
        '''
        self._visa_handle.timeout = timeout
        data = self._visa_handle.ask(cmd)
        return data.rstrip()

    def close(self):
        '''
        Close the visa connection.
        '''
        if hasattr(self, '_visa_handle'):
            self._visa_handle.close()
            del(self._visa_handle)

    def read(self):
        '''
        Read from VISA.
        Strip terminating characters from the response.
        '''
        data = self._visa_handle.read()
        return data.rstrip()

    def write(self, cmd):
        '''
        Write to VISA.
        '''
        self._visa_handle.write(cmd)
