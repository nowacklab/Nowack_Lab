import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize.curve_fit as curve_fit
import scipy import signal

from daqspectrum import DaqSpectrum
from ..Utilities.save import Measurement

class Geophone_calibrate(Measurement):
    _daq_inputs = ['inA', 'inB']
    _daq_outputs= ['out']
    _instrument_list = ['daq']

    Zi = 10e9
    arg0 = [4.5, 2, 380, .1, 33**2/.023]

    def __init__(self, instruments={}, Rs, sample_rate=1000):
        '''
        Arguments:
        Rs(float): resistor used as divider with geophone
        sample_rate(float): rate of measurement in Hz.  Total time
                            of measurement is 8191/sample_rate
        '''
        super().__init__(instruments=instruments)
        self.Rs = Rs
        self.sample_rate = sample_rate

    def _Ze(self, f, f0, Q0, Rt, Lt Z12sqOvMo):
        return Rt + 2j * np.pi * f * Lt + Z12sqOvMo * (2j * np.pi * f)/(
                (2 * np.pi*f0)**2 * (1 - (f/f0)**2 + (1j/Q0)* (f/f0)))

    def _Zsp(self, Rs, Zi):
        return Rs*Zi/(Rs + Zi)

    def _Zep(self, Ze, Zi):
        return Ze*Zi/(Ze + Zi)

    def rho(self, f, f0, Q0, Rt, Lt, Z12sqOvMo):
        Ze = self._Ze(f, f0, Q0, Rt, Lt, Z12spOvMo)
        Zep = self._Zep(Ze, self.Zi)
        return Zep/(Zep + self.Zsp(self.Rs, self.Zi))

    def do(self):
        # send random noise signal and montor the input channels
        noise = np.random.uniform(-10,10,8191) # max size of FIFO
        data = {'out': noise}
        received = self.daq.send_receive(data, chan_in=['inA', 'inB'], 
                                         sample_rate=self.sample_rate)
        self.Va = received['inA']
        self.Vb = received['inB']
        self.t  = received['t']

        # Should I fourier transform first?  welch it?

        # Ratio of the input voltages should look like rho
        # fit to rho with parameters
        self.ratio = self.Vb/self.Va
        self.f, self.ratiopsd = signal.welch(self.ratio, fs=self.sample_rate)
        self.dft = np.sqrt(self.ratiopsd)

        self.popt, self.pcov = curve_fit(self.rho, self.f, self.dft, p0=self.arg0)

        self.plot()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('Hz')
        self.ax.set_ylabel(r'Frequency Response (V/$\sqrt{\rm Hz}$)')
        self.ax.annotate(self.timestamp, xy=(.02,.98), xycoords='axes fraction',
                         fontsize=10, ha='left', va='top', family='monospace')

    def plot(self):
        self.ax.loglog(self.f, self.dft, marker='o', linestyle='', label='data')
        ylims = self.ax.get_ylim()

        xdata = np.linspace(1/self.sample_freq, self.sample_freq, 1000)
        self.ax.loglog(xdata, self.rho(xdata, *self.popt), label='fit')

        self.ax.set_ylim(ylims)
        self.ax.legend()

    def plot_debug(self):
        fig,ax, = plt.subplots()
        ax.plot(self.t, self.Va, label='Va')
        ax.plot(self.t, self.Vb, label='Vb')
        ax.plot(self.t, self.ratio, label='Vb/Va')

    def print_params(self):
        names = ['f0', 'Q0', 'Rt', 'Lt']
        for n,i in zip(names, range(len(names))):
            print(r"{2}: {0:f} $\pm$ {1:f}".format(self.popt[i], self.pcov[i], n))
        print(r"L12: {0:f} $\pm$ {1:f}".format((self.popt[4]*.023)**.5, 
                                               (self.pcov[4]*.023)**.5, n))

class Geophone_sr5113(Measurement):
    _daq_inputs = ['dc']
    _instrument_list = ['daq', 'preamp']

    def __init__(self, instruments={}, 
                 measure_time=1, 
                 measure_freq=256000, 
                 averages=30,
                 preamp_diff_mode=False,
                 conversion=31.5 # V/ (m/s)
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

        # conversion 
        self.c_acc = lambda s: np.abs(self.conversion * 2*np.pi*s /
                                        ((2*np.pi*s)**2 + 18*2*np.pi*s + 760))
        self.c_vel = lambda s: np.abs(self.conversion * (2*np.pi*s)**2 /
                                        ((2*np.pi*s)**2 + 18*2*np.pi*s + 760))
        self.c_pos = lambda s: np.abs(self.conversion * (2*np.pi*s)**3 /
                                        ((2*np.pi*s)**2 + 18*2*np.pi*s + 760))

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

        self.psd = self.daqspectrum.psd
        self.f   = self.daqspectrum.f

        geo = Geophone(conversion=self.conversion)
        [self.acc, self.vel, self.pos] = geo.convert(self.psd, self.f)

        self.plot()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots(3,1, sharex=True)
        self.ax = list(self.ax.flatten() )

    def plot(self):
        self.ax[0].semilogy(self.f, self.pos*1e6)
        self.ax[1].semilogy(self.f, self.vel*1e6)
        self.ax[2].semilogy(self.f, self.acc*1e6)

        for a in self.ax:
            a.set_xlim([0,1000])

        self.ax[0].set_ylabel(r'Position ($\mu$ m)')
        self.ax[1].set_ylabel(r'Velocity ($\mu$ m/s)')
        self.ax[2].set_ylabel(r'Acceleration ($\mu$ m/s/s)')
        
        self.ax[2].set_xlabel('Frequency (Hz)')



class Geophone(Object):
    conversion = 0
    c_acc = lambda s, G: np.abs(G * 2*np.pi*s /
                                ((2*np.pi*s)**2 + 18*2*np.pi*s + 760))
    c_vel = lambda s, G: np.abs(G * (2*np.pi*s)**2 /
                                ((2*np.pi*s)**2 + 18*2*np.pi*s + 760))
    c_pos = lambda s, G: np.abs(G * (2*np.pi*s)**3 /
                                ((2*np.pi*s)**2 + 18*2*np.pi*s + 760))

    def __init__(self, 
                 conversion=31.5 # V/(m/s)
                 ):
        self.conversion = conversion

    def convert(self, psd_V, f):
        acc = psd_V / self.c_acc(f, self.conversion)
        vel = psd_V / self.c_vel(f, self.conversion)
        pos = psd_V / self.c_pos(f, self.conversion)

        return [acc, vel, pos]
