from scipy.interpolate import interp1d
import numpy as np
import time

class Thermometer():

    def __init__(self, lockin, diffv, output, calibrationfilename,
                    rbias = 1e6):
        '''
        Calibration file should be CSV, with the first column being
        temperatures and the second being resistances in ohms. Lockin
        should be configured to source a current on on side of resistor
        thermometer and record 4 point voltage across it.
        '''

        self.lockin = lockin
        self.diffv = diffv
        self.output = output
        self.rbias = rbias
        self.calibrationfilename = calibrationfilename
        with open(calibrationfilename) as f:
            calibration = [line.strip().split(',') for line in f]
        self.resistances = []
        self.temperatures = []
        for a in calibration:
            self.resistances.append(float(a[1]))
            self.temperatures.append(float(a[0]))
        self.converter = interp1d(self.resistances, self.temperatures,
                     fill_value  = 300, bounds_error = False, kind = 'cubic')

    def __getstate__(self):
        lockinstate = self.lockin.__getstate__()
        state = {'Thermo Calibration File': self.calibrationfilename,
                 'Thermo Calibration Resistances (Ohms)' : self.resistances,
                 'Thermo Calibration Temperatures (Kelvin)' : self.temperatures,
                 'Reported rbias (Ohms)' : self.rbias,
                 'Property used for ibias': self.output,
                 'Property used to record diffV': self.diffv}
        state.update(lockinstate)
        return state

    @property
    def T(self):
        r = self.rbias * (getattr(self.lockin, self.diffv)
                            /getattr(self.lockin, self.output))
        return self.converter(r)
