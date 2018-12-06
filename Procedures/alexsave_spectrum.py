from scipy import signal
import matplotlib.pyplot as plt 
import numpy as np
from datetime import datetime
import os
import re
import time
from importlib import reload

import Nowack_Lab.Utilities.utilities
reload(Nowack_Lab.Utilities.utilities)
from Nowack_Lab.Utilities.utilities import reject_outliers_spectrum
from Nowack_Lab.Utilities.utilities import make_rms

import Nowack_Lab.Utilities.conversions as conversions
reload(conversions)

import Nowack_Lab.Utilities.welch
reload(Nowack_Lab.Utilities.welch)
from Nowack_Lab.Utilities.welch import Welch

import Nowack_Lab.Utilities.datasaver
reload(Nowack_Lab.Utilities.datasaver)
from Nowack_Lab.Utilities.datasaver import Saver

import Nowack_Lab.Utilities.alexsave_david_meas
reload(Nowack_Lab.Utilities.alexsave_david_meas)
from Nowack_Lab.Utilities.alexsave_david_meas import Preamp_Util

class DaqSpectrum():
    _daq_inputs=['dc']

    def __init__(self,
            instruments,
            measure_time=1,
            measure_freq=256000,
            fft_fspace = 1,
            units='V',
            units_per_V=1,
            rms_range=(500,5000),
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
        Preamp_Util.init(self, instruments, 
                        set_preamp_gain=set_preamp_gain,
                        set_preamp_filter=set_preamp_filter,
                        set_preamp_dccouple=set_preamp_dccouple,
                        set_preamp_diffmode=set_preamp_diffmode,
                        )

        self.measure_time = measure_time
        self.measure_freq = measure_freq
        self.fft_fspace   = fft_fspace

        self.units = units
        self.units_per_V = units_per_V

        self.rms_range = rms_range

        self.V = np.full(self.measure_time*self.measure_freq, np.nan)
        self.t = np.full(self.measure_time*self.measure_freq, np.nan)
        self.meas_starttime = 0

        self.saver = Saver(name='DaqSpectrum')


    def run(self):
        self.meas_starttime = time.time()
        received = self.daq.monitor(self._daq_inputs[0],
                                    self.measure_time,
                                    sample_rate=self.measure_freq)
        self.V = received['dc']/self.preamp.gain
        self.t = received['t']

        self.saver.append('/V/', self.V)
        self.saver.append('/t/', self.t)
        self.saver.append('/instr/preamp/', Preamp_Util.to_dict(self))
        self.saver.append('/attrs/', {'units_V': self.units,
                                    'units_t': 'seconds',
                                    'measure_freq': self.measure_freq,
                                    'measure_time': self.measure_time,
                                    })
        _ = self._welch()
        _ = self._make_rms()
                                           
    def _welch(self, fft_fspace=None):
        if fft_fspace == None:
            fft_fspace = self.fft_fspace

        [self.f, self.psd] = Welch.welchf(self.V, self.measure_freq, self.fft_fspace)
        self.saver.append('/psd/', self.psd)
        self.asd = np.sqrt(self.psd)*self.units_per_V
        self.saver.append('/asd/', self.asd)
        self.saver.append('/f/', self.f)

        self.saver.append('/_dims/', {
                                    'psd': np.array(['f',]),
                                    'asd': np.array(['f',]),
                                    'V': np.array(['t',]),})
        self.saver.append('/attrs/units_psd/', 'V^2/Hz')
        self.saver.append('/attrs/units_asd/', '{0}/Hz^.5'.format(self.units))
        self.saver.append('/attrs/units_f/', 'Hz')

        return [self.f, self.psd]

    def _make_rms(self, rms_range=None, sigma=2):
        '''
        Make rms of (self.psd) from self.psd and self.f given
        the range of frequencies defined by rms_range (tuple)

        returns:
        ~~~~~~~~
        [rms, rms_sigma]
        rms is the root mean squared of the amplitude spectral density
        in units of self.units

        rms_sigma is rms but rejecting outliers.  Large sigma means less
        rejected points
        '''
        if rms_range == None:
            rms_range = self.rms_range

        [rms, rms_sigma] = make_rms(self.f, self.psd, rms_range, sigma)
        rms = rms*self.units_per_V
        rms_sigma = rms_sigma*self.units_per_V

        self.saver.append('/rms_noise/', rms)
        self.saver.append('/rms_noise_exclude_outliers/', rms_sigma)
        self.saver.append('/attrs/units_rms_noise/', 
                            '{0}/Hz^.5'.format(self.units))
        self.saver.append('/attrs/units_rms_noise_exclude_outliers/', 
                            '{0}/Hz^.5'.format(self.units))
