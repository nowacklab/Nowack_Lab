import matplotlib.pyplot as plt, os, re, numpy as np, time
from scipy import signal
from .measurement import Measurement
from ..Utilities.utilities import AttrDict
from ..Utilities import conversions
from scipy.optimize import curve_fit
from scipy.stats import linregress as lr

class DaqSpectrum(Measurement):
    '''
    Monitor a DAQ channel and compute the spectral density

    Acqurire a number of time traces from the channel labeled 'dc' on the DAQ.
    Average the time traces and compute the spectral density.
    '''
    _daq_inputs = ['dc']
    instrument_list = ['daq'] # 'preamp' optional
    f = 1
    V = 1
    t = 1
    Vn = 1
    units = 'V'
    conversion = 1

    def __init__(
            self,
            instruments={},
            measure_time=0.5,
            measure_freq=256000,
            averages=30,
            preamp_gain=1):
        '''
        Create a DaqSpectrum object

        Args:
        instruments (dict): instruments used to collect data
        measure_time (float): time in seconds that DAQ monitors the output
            channel
        measure_freq (int?): frequency that the DAQ measures the output channel
        averages (int): number of time traces averaged before computing the FFT
        preamp_gain (float): gain factor from preamp
        '''
        super().__init__(instruments=instruments)

        for arg in ['measure_time', 'measure_freq', 'averages', 'preamp_gain']:
            setattr(self, arg, eval(arg))

        self.timetraces_t = [None]*averages
        self.timetraces_V = [None]*averages

    def do(self, plot=True):
        '''
        Do the DaqSpectrum measurment.
        '''
        self.setup_preamp()

        self.Vn = self.get_spectrum()

        if plot:
            self.plot()


    def fit_one_over_f(self, fmin=0, fmax=None, filters=[60], filters_bw=[10],
        plot=True):
        '''
        Returns A, alpha fit parameters to A/f^alpha.
        Linear fitting of a log-log plot over the frequency range [fmin, fmax].
        filter: A list of frequencies (Hz) to filter out for the fit.
        filter_bw: A list of bandwidths (Hz) corresponding to each filter frequency
        plot: if True, will plot the fit curve on the figure.
        '''
        argmin, argmax = self._get_argmin_argmax(fmin, fmax)
        f = self.f[argmin:argmax]
        Vn = self.Vn[argmin:argmax]

        for i in range(len(filters)):
            freq0 = filters[i]
            freq = freq0
            j=1
            while freq < fmax:
                # harmonics
                freq = freq0 * j
                j += 1

                where, = np.where(abs(f-freq) > filters_bw[i]/2)  # find indices where frequency is outside bandwidth of filter center frequency
                f = f[where]
                Vn = Vn[where]

        # popt, pcov = curve_fit(one_over_f, f, Vn, p0=[1e-5,.5], bounds=([-np.inf, .4], [np.inf, .6]))
        # return popt
        m,b, _, _, _ = lr(np.log(f), np.log(Vn))

        if plot and self.ax is not None:
            self.ax['loglog'].loglog(np.exp(b)*self.f**(m))

        return np.exp(b), -m

    def get_average(self, fmin=0, fmax=None):
        '''
        Returns an average spectral density over the given frequency range [fmin, fmax].
        Default, returns average spectral density over entire spectrum
        '''
        argmin, argmax = self._get_argmin_argmax(fmin, fmax)
        return np.mean(self.Vn[argmin:argmax])

    def _get_argmin_argmax(self, fmin=0, fmax=None):
        '''
        Get the indices corresponding to frequencies fmin and fmax
        '''
        if fmax is None:
            fmax  = self.f.max()
        argmin = abs(self.f-fmin).argmin()
        argmax = abs(self.f-fmax).argmin()
        return argmin, argmax

    def get_Nfft(self):
        '''
        Number of points for the FFT. This is different between DAQ and Zurich.
        '''
        return np.round(self.measure_freq * self.measure_time / 2)

    def get_spectrum(self):
        '''
        Collect time traces from the DAQ and compute the FFT.

        Returns:
        Vn (np.ndarray): Square root of the power spectral density
        '''
        Nfft = self.get_Nfft()

        psdAve = np.zeros(int(Nfft))

        for i in range(self.averages):
            t, V = self.get_time_trace()

            # Divide by gain
            if hasattr(self, 'preamp'):
                gain = self.preamp.gain
            else:
                gain = self.preamp_gain
            V /= gain

            self.timetraces_t[i] = t
            self.timetraces_V[i] = V
            self.f, psd = signal.periodogram(V, self.measure_freq,
                                             'blackmanharris')
            psdAve = psdAve + psd

        self.timetraces_t = np.array(self.timetraces_t)
        self.timetraces_V = np.array(self.timetraces_V)

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
        V = received['dc']
        t = received['t']
        return t, V

    @classmethod
    def load(cls, filename=None):
        '''
        Overwritten load method to fix variable name
        '''
        obj = ZurichSpectrum._load(filename)
        if hasattr(obj, 'psdAve'):
            obj.Vn = obj.psdAve  # legacy loading after variable name change
        return obj

    def plot(self):
        '''
        Plot the power spectral density on a loglog and semilog scale
        '''
        super().plot()
        self.ax['loglog'].loglog(self.f, self.Vn * self.conversion)
        self.ax['semilog'].semilogy(self.f, self.Vn * self.conversion)

    def setup_plots(self):
        '''
        Setup loglog and semilog plots for spectral density
        '''
        self.fig = plt.figure(figsize=(12, 6))
        self.ax = AttrDict()
        self.ax['loglog'] = self.fig.add_subplot(121)
        self.ax['semilog'] = self.fig.add_subplot(122)

        for ax in self.ax.values():
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel(
                r'Spectral Density ($\mathrm{%s/\sqrt{Hz}}$)' %
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
            averages=30,
            input_ch = 0,
            preamp_gain=1):
        '''
        Create a ZurichSpectrum object

        Args:
        instruments (dict): Instrument dictionary
        measure_freq (float): sampling rate (Hz). Must be in MFLI.freq_opts
        averages (int): number of time traces averaged before computing the FFT
        input_ch - Input channel. 0 = "Signal Input 1"; 9 = "Aux Input 2"
        preamp_gain - gain of preamp used in measurement
        '''
        super().__init__(instruments, None, measure_freq, averages, preamp_gain)

        if hasattr(self, 'zurich'):
            if measure_freq not in self.zurich.freq_opts:
                raise Exception('Frequency must be in: %s' %self.zurich.freq_opts)
        self.measure_time = 16384/measure_freq  # 16384 = 2^14 fixed number
        self.input_ch = input_ch

        self.zurich.daq.setInt('/dev3447/sigins/%i/autorange' %input_ch, 1)  # autorange input
        time.sleep(5)  # wait for autoranging to complete


    def get_Nfft(self):
        '''
        Number of points for the FFT. This is different between DAQ and Zurich.
        '''
        return np.round(self.measure_freq * self.measure_time / 2) + 1

    def get_time_trace(self):
        '''
        Collect a single time trace from the Zurich.
        '''
        return self.zurich.get_scope_trace(freq=self.measure_freq, N=16384, input_ch=self.input_ch)

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
