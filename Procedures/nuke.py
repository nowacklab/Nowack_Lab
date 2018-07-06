import numpy as np
import time
import matplotlib.pyplot as plt
from ..Utilities.save import Measurement
from IPython.display import clear_output

class PulseMeasurement(Measurement):

    def __init__(self,oscope):
        testdata = oscope.getdata
        self.oscope = oscope
        self.burstspacing  = 1e-3
        self.numoscopeavg = 512

    def relaxationtrace(self, num_avg):
        self.xaxis = self.oscope.getdata[0]
        self.avgdata = np.zeros(len(self.xaxis))
        for i in range(num_avg):
            clear_output()
            print('Average ' + str(i) + ' of ' + str(num_avg))
            time.sleep(self.numoscopeavg*self.burstspacing/2)
            self.avgdata = self.oscope.getdata[1]/num_avg + self.avgdata
        plt.clf()
        plt.plot(self.xaxis, self.avgdata)
        plt.show()
