"""
For the future? Instrument base class that all instruments belong to.
"""

import visa


class Instrument:
    _label = 'instrument'

    def __getstate__(self):
    	return self.__dict__

    def __setstate__(self, state):
    	"""
        Setstate for an instrument by default does not load an instrument.
        You must custom-write setstates if you want private variables to be loaded.
        It is not recommended to load directly into properties, in case this makes
        an unwanted change to the physical instrument.
        """
        pass


class VISAInstrument(Instrument):
    _label = 'VISAinstrument'
    _strip = ''  # default character to strip from read commands

    def __del__(self):
        """
        Destroy the object and close the visa handle
        """
        self.close()

    def _init_visa(self, resource, termination='\n'):
        r"""
        Initialize the VISA connection.
        Pass in the resource name. This can be:
        - GPIB Address
            GPIB::##::INSTR
        - TCPIP Socket
            TCPIP::host address::port::SOCKET
        - Or many others...
            See https://pyvisa.readthedocs.io/en/stable/names.html
        termination: e.g. \r\n: read termination.
        """
        self._visa_handle = visa.ResourceManager().open_resource(resource)
        self._visa_handle.read_termination = termination

    def ask(self, cmd, timeout=3000, strip=None):
        """
        Write and read combined operation.
        Default timeout 3000 ms. None for infinite timeout
        Strip: terminating characters to strip from the response. None = default for class.
        """
        if strip is None:
            strip = self._strip

        self._visa_handle.timeout = timeout
        data = self._visa_handle.ask(cmd)
        return data.rstrip(strip)

    def close(self):
        """
        Close the visa connection.
        """
        if hasattr(self, '_visa_handle'):
            self._visa_handle.close()
            del self._visa_handle

    def read(self, strip=''):
        """
        Read from VISA.
        Strip: terminating characters to strip from the response. None = default for class.
        """
        if strip is None:
            strip = self._strip
            
        data = self._visa_handle.read()
        return data.rstrip(strip)

    def write(self, cmd):
        """
        Write to VISA.
        """
        self._visa_handle.write(cmd)
