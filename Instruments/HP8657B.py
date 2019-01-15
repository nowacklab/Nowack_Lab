# import visa
# import numpy as np
# import time
from .instrument import VISAInstrument


class FunctionGenerator(VISAInstrument):
    _label = 'HP8657'
    """
    Instrument driver for HP 8657 2GHz signal generator
    """

    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' % gpib_address
        self.gpib_address = gpib_address

        self._init_visa(gpib_address, termination='\n')

    @property
    def freq(self):
        """
        Does nothing, junk attribute
        """
        return None

    @freq.setter
    def freq(self, value):
        freqinmhz = value/1e6
        self.write('FR%sMZ' % freqinmhz)
