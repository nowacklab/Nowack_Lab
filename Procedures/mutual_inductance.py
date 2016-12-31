import time, os, numpy as np, matplotlib.pyplot as plt
from ..Utilities import conversions
from ..Utilities.save import Measurement
from ..Utilities.plotting import plot_mpl
from ..Utilities.utilities import AttrDict

class MutualInductance(Measurement):
    instrument_list = ['squidarray', 'lockin_squid', 'lockin_I']

    def __init__(self, instruments = {}, Rmeas=3172, Istart=5e-6, Iend=30e-6,
                 numamps=10, fstart = 100, fend = 20000, numf= 10):
        super().__init__()
        self._load_instruments(instruments)
        self.Rmeas = Rmeas
        self.amps = np.linspace(Istart, Iend, numamps)*Rmeas
        self.freqs = np.logspace(np.log10(fstart), np.log10(fend), numf) # 10 Hz to 20 kHz
        self.V = np.full((len(self.freqs), len(self.amps)), np.nan)
        self.I = np.full((len(self.freqs), len(self.amps)), np.nan)


    def do(self):
        for i, f in enumerate(self.freqs):
            self.lockin_squid.frequency = f
            for j, a in enumerate(self.amps):
                self.lockin_squid.amplitude = a
                time.sleep(3)
                #self.lockin_squid.auto_gain()
                #self.lockin_I.auto_gain()
                self.squidarray.reset()
                time.sleep(3)
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


class ArraylessMI(Measurement):
    '''
    Map out the response of the SQUID in the mod current / field coil current
    parameter space.

    instruments: Requires a DAQ and a preamp

    s_bias: bias point of the SQUID in uA
    r_bias_squid: bias resistor used to bias the SQUID
    r_bias_mod: bias resistor going to mod coil.
    r_bias_field: bias resistor going to field coil
    I_mod_i, I_mod_f, num_mod: defines the mod coil current sweep in uA
    I_field_i, I_field_f, num_field: defines the field coil current sweep in uA

    example:

    '''
    instrument_list = ["daq", "preamp"]
    _chan_labels = ["squid_out", "squid_bias", "mod_source", "field_source"]

    def __init__(self, s_bias, r_bias_squid, r_bias_mod, r_bias_field,
                 instruments = {}, I_mod_i = 0, I_mod_f = 0, num_mod = 100,
                 I_field_i = 0, I_field_f = 0, num_field = 10, rate = 100):

        super().__init__()
        self._load_instruments(instruments)
        self.s_bias = float(s_bias) * 1e-6
        self.r_bias_squid = r_bias_squid
        self.I_mod_i = I_mod_i * 1e-6
        self.I_mod_f = I_mod_f * 1e-6
        self.num_mod = num_mod
        self.rate = rate
        self.field_current = 1e-6 * np.linspace(I_field_i, I_field_f, num_field)
        self.r_bias_mod = r_bias_mod
        self.r_bias_field = r_bias_field
        self.V = np.full((num_mod, len(self.field_current)),
                         np.NaN)

    def do(self):
        #bias the SQUID to the desired working point
        _,_ = self.daq.sweep(
            {"squid_bias": self.daq.outputs["squid_bias"].V},
            {"squid_bias": self.s_bias * self.r_bias_squid},
            sample_rate=10000, numsteps = 10000)
        for i, f in enumerate(self.field_current):
            #source a current to the field coil
            _,_ = self.daq.sweep(
                {"field_source": self.daq.outputs["field_source"].V},
                {"field_source": f * self.r_bias_field},
                sample_rate = 10000, numsteps = 10000)
            #now sweep the current in the mod coil
            output_data, recieved = self.daq.sweep(
                {"mod_source": self.I_mod_i * self.r_bias_mod},
                {"mod_source": self.I_mod_f * self.r_bias_mod},
                chan_in = ["squid_out"], sample_rate = self.rate,
                numsteps = self.num_mod)
            self.V[:, i] = np.array(recieved["squid_out"])/self.preamp.gain
