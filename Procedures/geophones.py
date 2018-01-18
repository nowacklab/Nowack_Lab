import numpy as np
import matplotlib.pyplot as plt

from daqspectrum import DaqSpectrum
from ..Utilities.save import Measurement



class Geophone_sr5113(Measurement):
    _daq_inputs = ['dc']
    _instrument_list = ['daq', 'preamp']

    def __init__(self, instruments={}, 
                 measure_time=1, 
                 measure_freq=256000, 
                 averages=30,
                 preamp_diff_mode=False,
                 conversion=.32 # V/ (cm/s)
                 ):
    '''
    '''
        super().__init__(instruments=instruments)
        self.instruments = instruments
        self.measure_time = measure_time
        self.measure_freq = measure_freq
        self.averages = averages
        self.preamp_diff_mode = preamp_diff_mode
        self.conversion = conversion

    def do(self):
        self.daqspectrum = DaqSpectrum(instruments=self.instruments,
                                       measure_time=self.measure_time,
                                       measure_freq=self.measure_freq,
                                       averages=self.averages,
                                       preamp_gain_override=True,
                                       preamp_filter_override=True,
                                       preamp_dccouple_override=True,
                                       preamp_autoOL=False,
                                       preamp_diff_mode=self.preamp_diff_mode
                                       )
        self.daqspectrum.run(welch=True)

        self.V = np.mean(self.daqspectrum.V, axis=0)
        self.velocity = self.V/self.conversion
        self.t = self.daqspectrum.t
        self.position = np.trapz(self.average_velocity, x=self.t)
        self.average_acceleration = np.gradient(self.average_velocity, self.t)




