import matplotlib.pyplot as plt, os, re, numpy as np
from scipy import signal
from .measurement import Measurement
from ..Utilities.utilities import AttrDict
from ..Utilities import conversions


class DaqSpectrum(Measurement):
    '''
    Monitor a DAQ channel and compute the power spectral density

    Acqurire a number of time traces from the channel labeled 'dc' on the DAQ.
    Average the time traces and compute the power spectral density.
    '''
    _daq_inputs = ['dc']
    instrument_list = ['daq'] # 'preamp' optional
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

        self.timetraces_t = [None]*averages
        self.timetraces_V = [None]*averages

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
        Nfft = np.round(self.measure_freq * self.measure_time / 2) + 1
            # 7/12/2018 daq changed forced remove +1
            # 7/26/2018 Needed to add +1 for Zurich. Check DAQ again.
        psdAve = np.zeros(int(Nfft))

        for i in range(self.averages):
            t, V = self.get_time_trace()
            self.timetraces_t[i] = t
            self.timetraces_V[i] = V
            self.f, psd = signal.periodogram(V, self.measure_freq,
                                             'blackmanharris')
            psdAve = psdAve + psd

        # Normalize by the number of averages
        psdAve = psdAve / self.averages
        # Convert spectrum to V/sqrt(Hz)
        return np.sqrt(psdAve)

    def get_time_trace(self):
        '''
        Collect a single time trace from the DAQ.
        '''
        received = self.daq.monitor('dc', self.measure_time,
                                    sample_rate=self.measure_freq
                                    )
        # Unpack data recieved from daq.
        # Divide out any preamp gain applied.
        if hasattr(self, 'preamp'):
            gain = self.preamp.gain
        else:
            gain = 1
        self.V = received['dc'] / gain
        self.t = received['t']
        return t, V

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


class ZurichSpectrum(DaqSpectrum):
    '''
    Use the Zurich MFLI to take a spectrum
    '''
    instrument_list = ['zurich']

    def __init__(
            self,
            instruments={},
            measure_freq=14.6e3,
            averages=30):
        '''
        Create a ZurichSpectrum object

        Args:
        instruments (dict): Instrument dictionary
        measure_freq (float): sampling rate (Hz). Must be in MFLI.freq_opts
        averages (int): number of time traces averaged before computing the FFT
        '''
        super().__init__(instruments, None, measure_freq, averages)

        if measure_freq not in self.zurich.freq_opts:
            raise Exception('Frequency must be in: %s' %self.freq_opts)
        self.measure_time = 16384/measure_freq  # 16384 = 2^14 fixed number

    def get_time_trace(self):
        '''
        Collect a single time trace from the Zurich.
        '''
        return self.zurich.get_scope_trace(freq=self.measure_freq, N=16384)

    def setup_preamp(self):
        '''
        No preamp used with Zurich
        '''
        pass


class SQUIDSpectrum(DaqSpectrum):
    '''
    Wrapper for DAQSpectrum that converts from V to Phi_0.
    '''
    instrument_list = ['daq', 'preamp', 'squidarray']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.units = '\phi_0'
        self.conversion = conversions.Vsquid_to_phi0[self.squidarray.sensitivity]
