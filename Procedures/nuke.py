import numpy as np
import time
import matplotlib.pyplot as plt

class PulseMeasurement(Measurement):

    def __init__(self,oscope):
        testdata = oscope.getdata
        self.sampleinterval = testdata[1][-1] - testdata[1][1]
        self.numoscopeavg = 512

    def relaxationtrace(self, num_avg):
        self.xaxis = oscope.getdata[0]
        self.avgdata = np.zeros(len(self.xaxis))
        for i in num_avg:
            self.avgdata = oscope.getdata[1]/num_avg + self.avgdata
            time.sleep(self.numoscopeavg*self.sampleinterval)
        plt.plot(self.xaxis, self.avgdata)
