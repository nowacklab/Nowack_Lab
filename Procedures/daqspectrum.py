import matplotlib.pyplot as plt, os, re, numpy as np
from scipy import signal
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict
from ..Utilities import conversions


class DaqSpectrum(Measurement):
    '''
    Monitor a DAQ channel and compute the power spectral density

    Acqurire a number of time traces from the channel labeled 'dc' on the DAQ.
    Average the time traces and compute the power spectral density.
    '''
    _daq_inputs = ['dc']
    instrument_list = ['daq', 'preamp']
    f = 1
    V = 1
    t = 1
    psdAve = 1
    units = 'V'
    conversion = 1

    def __init__(
            self,
            instruments={},
            measure_time=0.5,
            measure_freq=256000,
            averages=30):
        '''
        Create a DaqSpectrum object

        Args:
        instruments (dict): instruments used to collect data
        measure_time (float): time in seconds that DAQ monitors the output
            channel
        measure_freq (int?): frequency that the DAQ measures the output channel
        averages (int): number of time traces averaged before computing the FFT
        '''
        super().__init__(instruments=instruments)

        for arg in ['measure_time', 'measure_freq', 'averages']:
            setattr(self, arg, eval(arg))

    def do(self):
        '''
        Do the DaqSpectrum measurment.
        '''
        self.setup_preamp()

        self.psdAve = self.get_spectrum()

        self.plot()

    def get_spectrum(self):
        '''
        Collect time traces from the DAQ and compute the FFT.

        Returns:
        psdAve (np.ndarray): power spectral density
        '''
        Nfft = int((self.measure_freq * self.measure_time / 2) + 1)
        psdAve = np.zeros(Nfft)

        for i in range(self.averages):
            received = self.daq.monitor('dc', self.measure_time,
                                        sample_rate=self.measure_freq
                                        )
            # Unpack data recieved from daq.
            # Divide out any preamp gain applied.
            self.V = received['dc'] / self.preamp.gain
            self.t = received['t']
            self.f, psd = signal.periodogram(self.V, self.measure_freq,
                                             'blackmanharris')
            psdAve = psdAve + psd

        # Normalize by the number of averages
        psdAve = psdAve / self.averages
        # Convert spectrum to V/sqrt(Hz)
        return np.sqrt(psdAve)

    def plot(self):
        '''
        Plot the power spectral density on a loglog and semilog scale
        '''
        super().plot()
        self.ax['loglog'].loglog(self.f, self.psdAve * self.conversion)
        self.ax['semilog'].semilogy(self.f, self.psdAve * self.conversion)

    def setup_plots(self):
        '''
        Setup loglog and semilog plots for PSD
        '''
        self.fig = plt.figure(figsize=(12, 6))
        self.ax = AttrDict()
        self.ax['loglog'] = self.fig.add_subplot(121)
        self.ax['semilog'] = self.fig.add_subplot(122)

        for ax in self.ax.values():
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel(
                r'Power Spectral Density ($\mathrm{%s/\sqrt{Hz}}$)' %
                self.units)
            # apply a timestamp to the plot
            ax.annotate(self.timestamp, xy=(0.02, .98), xycoords='axes fraction',
                        fontsize=10, ha='left', va='top', family='monospace')

    def setup_preamp(self):
        '''
        Set preamplifier settings appropriate for taking spectra
        '''
        if not hasattr(self, 'preamp') or self.preamp is None:
            print('No preamp!')
            return
        self.preamp.dc_coupling()
        self.preamp.diff_input(False)



class SQUIDSpectrum(DaqSpectrum):
    '''
    Wrapper for DAQSpectrum that converts from V to Phi_0.
    '''
    instrument_list = ['daq', 'preamp', 'squidarray']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.units = '\phi_0'
        self.conversion = conversions.Vsquid_to_phi0[self.squidarray.sensitivity]
