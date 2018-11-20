from ..Procedures import alexsweep
import numpy as np
import time

class Thermometer():

    def __init__(self, daq, biasout, v1, v2,  calibrationfilename,
                    rbias = 1e6, ibias = 1e-6, iterations = 10):
        '''
        Calibration file should be CSV, with the first column being
        temperatures and the second being resistances in ohms
        V2 should be the 4 point closer to the current source. 
        '''

        self.daq = daq
        self.biasout = biasout
        self.v1 = v1
        self.v2 = v2
        self.rbias = rbias
        self.ibias = ibias
        self.iterations = iterations
        with open(filename) as f:
            calibration = [line.strip().split(',') for line in f]
        self.resistances = []
        self.temperatures = []
        for a in calibration:
            self.resistances.append(float(a[1]))
            self.temperatures.append(float(a[0]))

    @property
    def T(self):
        r = []
        for i in range(self.iterations):
            setattr(self.daq, self.biasout + '.V', self.rbias * self.ibias)
            time.sleep(1e-2)
            r.append((getattr(self.daq, self.v2 + '.V')-
                                getattr(self.daq, self.v1 + '.V'))/self.ibias)
            setattr(self.daq, self.biasout + '.V', -1 * self.rbias * self.ibias)
            time.sleep(1e-2)
            r.append((getattr(self.daq, self.v1 + '.V')-
                                getattr(self.daq, self.v2 + '.V'))/self.ibias)
            avgr = np.mean(r)
            return np.interp(avgr, self.resistances, self.temperatures)
