import visa
import numpy as np
import time
from .instrument import instrument
from .keithley import Keithley2400
from .VNA import VNA8722ES

# frequency sweep and field coil current plot
def scan_2d(startcurrent, stopcurrent, startfreq, stopfreq):
    k = keithley(23)
    v = VNA_ES(24)  # create instances of these instruments

    k.source = 'I'
    k.Iout_range = max(abs(startcurrent, stopcurrent))
    k.Iout = 0  # Start with no current

    v.minfreq = startfreq
    v.maxfreq = stopfreq


if __name__ == "__main__":
    print("nothing")
    pass
