import time, os, numpy as np, matplotlib.pyplot as plt
from ..Utilities import conversions
from ..Utilities.save import Measurement, get_todays_data_path
from ..Utilities.plotting import plot_mpl


class MutualInductance(Measurement):
    instrument_list = ['squidarray', 'lockin_squid', 'lockin_I']

    def __init__(self, instruments = {}, Rmeas=3172, Istart=5e-6, Iend=30e-6, numamps=10, numfreqs=10):
        super().__init__()
        self._load_instruments(instruments)
        self.Rmeas = Rmeas
        self.amps = np.linspace(Istart, Iend, numamps)*Rmeas
        self.freqs = np.logspace(np.log10(100), np.log10(20000), numfreqs) # 10 Hz to 20 kHz
        self.V = np.full((len(self.freqs), len(self.amps)), np.nan)
        self.I = np.full((len(self.freqs), len(self.amps)), np.nan)


    def do(self):
        for i, f in enumerate(self.freqs):
            self.lockin_squid.frequency = f
            for j, a in enumerate(self.amps):
                self.lockin_squid.amplitude = a
                time.sleep(1)
                self.lockin_squid.auto_gain()
                self.lockin_I.auto_gain()
                self.squidarray.reset()
                time.sleep(1)
                self.V[i,j] = self.lockin_squid.R
                self.I[i,j] = self.lockin_I.R/self.Rmeas
                self.plot()
        self.save()


    def plot(self):
        super().plot()

        self.ax['vs_amp'].lines = []
        self.ax['vs_freq'].lines = []

        for i in range(self.V.shape[0]):
            self.ax['vs_amp'].plot(self.amps, self.V[i,:]*conversions.Vsquid_to_phi0/self.I[i,:], '.')
        for j in range(self.V.shape[1]):
            self.ax['vs_freq'].plot(self.freqs, self.V[:,j]*conversions.Vsquid_to_phi0/self.I[:,j], '.')

        plot_mpl.update2D(self.im, self.V*conversions.Vsquid_to_phi0/self.I, equal_aspect=False)
        plot_mpl.aspect(self.ax['2D'], 3)

        self.fig.tight_layout()
        self.fig.subplots_adjust(wspace=.3, hspace=.3)
        self.fig.canvas.draw()


    def setup_plots(self):
        self.fig = plt.figure()
        self.ax = AttrDict()
        self.ax['vs_amp'] = self.fig.add_subplot(221)
        self.ax['vs_amp'].set_xlabel('Amplitude (V)')
        self.ax['vs_amp'].set_ylabel('Mutual Inductance ($\phi_0$/A)')

        self.ax['vs_freq'] = self.fig.add_subplot(223)
        self.ax['vs_freq'].set_xlabel('Frequency (Hz)')
        self.ax['vs_freq'].set_ylabel('Mutual Inductance ($\phi_0$/A)')

        self.ax['2D'] = self.fig.add_subplot(122)
        self.im = plot_mpl.plot2D(self.ax['2D'], self.amps*1000,
            self.freqs/1000, self.V*conversions.Vsquid_to_phi0/self.I,
            ylabel='Frequency (kHz)', xlabel='Amplitude (mV)',
            clabel = 'Mutual inductance ($\phi_0$/A)', equal_aspect=False
        )
