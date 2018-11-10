# just updates DAQ input voltage data
import numpy as np
import matplotlib.pyplot as plt
import time
from ..Instruments.nidaq import *

class daq_plotter:
    def __init__(self, total_time=5, timestep=.01):
        self.total_time = total_time
        self.timestep = timestep
        self.numpoints = int(float(self.total_time)/float(self.timestep))
        self.dq = NIDAQ()

    def do(self):
        arr = np.zeros((self.numpoints, 1))
        for i in range(self.numpoints):
            time.sleep(self.timestep)
            arr[i] = self.dq.ai0.V
        plt.ylim(-10, 10)
        print(np.mean(arr))
        plt.plot(arr)


class plot_tester:
    def __init__(self):
        pass

    def do(self):
        plt.axis([0, 10, 0, 1])

        for i in range(10):
            y = np.random.random()
            plt.scatter(i, y)
            plt.pause(0.05)
        plt.show()
