from scipy import signal
import matplotlib.pyplot as plt 
import numpy as np
from datetime import datetime
import os
import re
import time
from importlib import reload

import Nowack_Lab.Utilities.conversions as conversions
reload(conversions)

#import Nowack_Lab.Utilities.dataset
#reload(Nowack_Lab.Utilities.dataset)
#from Nowack_Lab.Utilities.dataset import Dataset

import Nowack_Lab.Utilities.datasaver
reload(Nowack_Lab.Utilities.datasaver)
from Nowack_Lab.Utilities.datasaver import Saver

class DaqSpectrum():

    _daq_inputs=['dc']

    def __init__(self,
            instruments,
            measure_time=1,
            measure_freq=256000,
            fft_fspace = 1,
            units='V',
            units_per_V=1,
            set_preamp_gain=None,
            set_preamp_filter=None,
            set_preamp_dccouple=None,
            set_preamp_diffmode=None,
            ):
        '''
        Instruments:        (dictionary): 
                            'daq', and 'preamp' instruments
        set_preamp_gain     (None or int): 
                            None (keep current value) or int
        set_preamp_filter   (None or 2ple): 
                            None (keep current value) or (0,10e3) format
        set_preamp_dccouple (None or boolean): 
                            None (keep current value) or boolean
        set_preamp_diffmode (None or boolean): 
                            None (keep current value) or if A-B

        '''
        self.daq = instruments['daq']
        self.preamp = instruments['preamp']

        self.measure_time = measure_time
        self.measure_freq = measure_freq
        self.fft_fspace   = fft_fspace

        self.units = units
        self.units_per_V = units_per_V

        self.set_preamp_gain = set_preamp_gain
        self.set_preamp_filter = set_preamp_filter
        self.set_preamp_dccouple = set_preamp_dccouple
        self.set_preamp_diffmode = set_preamp_diffmode
        self._setpreamp()

        self.V = np.full(self.measure_time*self.measure_freq, np.nan)
        self.t = np.full(self.measure_time*self.measure_freq, np.nan)
        self.meas_starttime = 0

        self.saver = Saver(name='DaqSpectrum')

    def _setpreamp(self):
        if self.set_preamp_gain is not None:
            self.preamp.gain = self.set_preamp_gain
        if self.set_preamp_filter is not None:
            self.preamp.filter = self.set_preamp_filter
        if self.set_preamp_dccouple is not None:
            self.preamp.dc_coupling(self.set_preamp_dccouple)
        if self.set_preamp_diffmode is not None:
            self.preamp.diff_input(self.set_diffmode)

    def run(self):
        self.meas_starttime = time.time()
        received = self.daq.monitor(self._daq_inputs[0],
                                    self.measure_time,
                                    sample_rate=self.measure_freq)
        self.V = received['dc']/self.preamp.gain
        self.t = received['t']

        self.saver.append('V', self.V)
        self.saver.append('t', self.t)
        self.saver.append('attrs': {'units_V': self.units,
                                    'units_t': 'seconds',
                                    'measure_freq': self.measure_freq,
                                    'measure_time': self.measure_time,
                                    })
        self.saver.append('instr/preamp': {'gain': self.preamp.gain,
                                           'filter': self.preamp.filter,
                                           # add dc coupling and diff mode
                                           })
                                           
        


