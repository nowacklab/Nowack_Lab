import visa
import numpy as np
import time

class Yokogawa(Instrument):
    _label = "yokogawa"
    def __init__(self, gpib_address=""):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'

    @property
    def I(self):
        return float(self.query("OD")[4:])

    @property
    def V(self):
        pass

    @property
    def Iout(self):
        pass

    @Iout.setter
    def Iout(self, val):
        self.write("S{}".format(current))
        self.write("E")
        

    @property
    def Vout(self):
        pass
