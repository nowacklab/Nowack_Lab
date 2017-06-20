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
    	Setstate for an instrument by default does not load an instrument.
    	You must custom-write setstates if you want private variables to be loaded.
    	It is not recommended to load directly into properties, in case this makes
    	an unwanted change to the physical instrument.
    	'''
    	pass

class VISAInstrument(Instrument):
    _label = 'VISAinstrument'

    def __del__(self):
        '''
        Destroy the object and close the visa handle
        '''
        self.close()

    def _init_visa(self):
        '''
        Initialize the VISA connection.
        '''
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'
        self._visa_handle.write('OUTX 1') #1=GPIB

    def ask(self, cmd, timeout=3000):
        '''
        Write and read combined operation.
        Default timeout 3000 ms. None for infinite timeout
        '''
        self._visa_handle.timeout = timeout
        return self._visa_handle.ask(cmd)

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
        '''
        return self._visa_handle.read()

    def write(self, cmd):
        '''
        Write to VISA.
        '''
        self._visa_handle.write(cmd)
