""" Procedure to take a DC power out vs. bias flux graph for RF SQUID
This is only a temporary program; should eventually make it actually use
other classes etc.
Should implement normal data saving right away"""

import matplotlib.pyplot as plt
import numpy as np
import time, os
from datetime import datetime
from ..Instruments.nidaq import NIDAQ

class double_mixer_measurement():

    """general operation: steps daq voltage out to
    step flux bias; at each step, record the
    voltage from the daq input"""

    def __init__(self, bias_resistance, Ioutmin, Ioutmax, numpoints):
        self.dq = NIDAQ() # create new daq object

    def do(self):
        self.dq.ao0.V = 0 # zero daq 0 ouput

        daq_iout_range = range(Ioutmin, Ioutmax, numpoints)
        daq_vout_range = bias_resistance*daq_iout_range

        #arr = numpy.zeros()

        for i in daq_iout_range:
            pass

class daq_test():
    def __init__(self):
        self.dq = NIDAQ()

    def test(self, numpoints, timestep):
        print("number of points: ", numpoints)
        print("time step (seconds): ", timestep)
        arr = np.zeros((numpoints, 0))
        print(np.shape(arr))
        for i in range(numpoints):
            time.sleep(1)
            self.dq.ai0.V()
            arr[i] = self.dq.ai0.V()
        print(arr)
