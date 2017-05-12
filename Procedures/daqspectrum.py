from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os
import re
from ..Instruments import nidaq, preamp
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict
from ..Utilities import conversions

class DaqSpectrum(Measurement):
    _daq_inputs = ['dc'] # DAQ channel labels expected by this class
    instrument_list = ['daq','preamp']
    ## So plotting will work with no data
    f = 1
    V = 1
    t = 1
    psdAve = 1
    units = 'V'
    conversion = 1

    def __init__(self, instruments={}, measure_time=0.5, measure_freq=256000, averages=30):
        super().__init__()

        for arg in ['measure_time','measure_freq','averages']:
            setattr(self, arg, eval(arg))


    def do(self):
        self.setup_preamp()

        self.psdAve = self.get_spectrum()

        self.plot()


    def get_spectrum(self):
        Nfft = int((self.measure_freq*self.measure_time / 2) + 1)
        psdAve = np.zeros(Nfft)

        for i in range(self.averages):
            received = self.daq.monitor('dc', self.measure_time,
                                        sample_rate=self.measure_freq
                                    )
            self.V = received['dc'] #extract data from the required channel
            self.t = received['t']
            self.f, psd = signal.periodogram(self.V, self.measure_freq,
                                             'blackmanharris')
            psdAve = psdAve + psd

        psdAve = psdAve / self.averages # normalize by the number of averages

        return np.sqrt(psdAve) # spectrum in V/sqrt(Hz)


    def plot(self):
        super().plot()
        self.ax['loglog'].loglog(self.f, self.psdAve*self.conversion)
        self.ax['semilog'].semilogy(self.f, self.psdAve*self.conversion)


    def setup_plots(self):
        self.fig = plt.figure(figsize=(12,6))
        self.ax = AttrDict()
        self.ax['loglog'] = self.fig.add_subplot(121)
        self.ax['semilog'] = self.fig.add_subplot(122)

        for ax in self.ax.values():
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel(r'Power Spectral Density ($\mathrm{%s/\sqrt{Hz}}$)' %self.units)
            #apply a timestamp to the plot
            ax.annotate(self.timestamp, xy=(0.02,.98), xycoords='axes fraction',
                fontsize=10, ha='left', va = 'top', family='monospace'
            )


    def setup_preamp(self):
        if not hasattr(self, 'preamp') or self.preamp is None:
            print('No preamp!')
            return
        self.preamp.gain = 1
        self.preamp.filter = (0, 100e3)
        self.preamp.dc_coupling()
        self.preamp.diff_input(False)
        self.preamp.filter_mode('low',12)

class SQUIDSpectrum(DaqSpectrum):
    instrument_list = ['daq', 'preamp', 'squidarray']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.units = '\phi_0'
        self.conversion = conversions.Vsquid_to_phi0[self.squidarray.sensitivity]
