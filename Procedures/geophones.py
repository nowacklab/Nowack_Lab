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
