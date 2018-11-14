import time
import os
import numpy as np
import matplotlib.pyplot as plt
from importlib import reload

import Nowack_Lab.Utilities.conversions as conversions
reload(conversions)

import Nowack_Lab.Utilities.save
reload(Nowack_Lab.Utilities.save)
from Nowack_Lab.Utilities.save import Measurement


import Nowack_Lab.Utilities.plotting
reload(Nowack_Lab.Utilities.plotting)
from Nowack_Lab.Utilities.plotting import plot_mpl

import Nowack_Lab.Utilities.utilities
reload(Nowack_Lab.Utilities.utilities)
from Nowack_Lab.Utilities.utilities import AttrDict

class MutualInductance_sweep(Measurement):
    instrument_list = ['daq', 'squidarray']
    _daq_inputs = ['dc']
    _daq_outputs = ['fieldcoil']

    def __init__(self, 
                 instruments = {},
                 fc_Is = [],
                 sbias = [],
                 Rbias = 3165,
                 rate = 100,
                 numsteps = 1000,
                 conversion = 1/14.4):
        super().__init__(instruments=instruments)
        self.fc_Is = np.array(fc_Is)
        self.sbias = np.array(sbias)
        self.Rbias = Rbias
        self.rate = rate
        self.numsteps = numsteps

    def do(self):
        self.mutuals = []
        self.sbias_live = []
        for sb in self.sbias:
            self.squidarray.S_bias = sb
            self.squidarray.reset()
            m = MutualInductance2(instruments, 
                                  self.fc_Is, 
                                  self.Rbias, 
                                  self.rate, 
                                  self.numsteps,
                                  self.conversion)
                 
            m.run(removeplot=True, save_appendedpath=self.filename)
            self.mutuals.append(m)
            self.sbias_live.append(sb)
            self.plot()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_ylabel('Squid Response ($\phi_0$)')
        self.ax.set_xlabel('Field Coil Current (mA)')

    def plot(self):
        m = self.mutuals[-1]
        self.ax.plot(m.Vsrc / m.Rbias / 1e-3, m.Vmeas * m.conversion, 
                     label='Sbias={0:2.2f} uA'.format(self.sbias_live[-1]*1e6))
        self.ax.legend()


class MutualInductance2(Measurement):
    instrument_list = ['daq']
    _daq_inputs = ['dc']
    _daq_outputs = ['fieldcoil']

    def __init__(self,
                instruments = {},
                Is = [],
                Rbias = 3165,
                rate=100,
                numsteps = 1000,
                title='',
                conversion = 1/14.4,
                units = r'\Phi_0'):
        super().__init__(instruments=instruments)
        self.Is = np.array(Is)
        self.Rbias = Rbias
        self.Vs = self.Is * self.Rbias
        self.rate = rate
        self.numsteps = numsteps
        self.title = title
        self.conversion = conversion
        self.units = units

    def do(self, title='', plot=True, removeplot = False):
        if title != '':
            self.title = title
        outputdata, received = self.daq.sweep(Vstart = {'fieldcoil':
                                                        self.daq.outputs['fieldcoil'].V},
                                              Vend   = {'fieldcoil': self.Vs[0]},
                                              chan_in    = self._daq_inputs,
                                              sample_rate= self.rate,
                                              numsteps   = int(self.numsteps/5)
                                              )
        outputdata, received = self.daq.sweep(Vstart = {'fieldcoil': self.Vs[0]},
                                              Vend   = {'fieldcoil': self.Vs[-1]},
                                              chan_in    = self._daq_inputs,
                                              sample_rate= self.rate,
                                              numsteps   = self.numsteps
                                              )
        self.Vmeas = np.array(received['dc'])
        self.Vsrc  = np.array(outputdata['fieldcoil'])
        _,_ = self.daq.sweep(Vstart = {'fieldcoil':
                                       self.daq.outputs['fieldcoil'].V},
                             Vend   = {'fieldcoil': 0},
                             chan_in    = self._daq_inputs,
                             sample_rate= self.rate,
                             numsteps   = int(self.numsteps/5)
                            )

        if plot:
            self.plot()
        if removeplot:
            plt.close()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        plt.pause(.01)

    def plot(self):
        super().plot()
        self.ax.plot(self.Vsrc / self.Rbias / 1e-3, self.Vmeas * self.conversion,
                     label='data')
        self.ax.set_ylabel('SQUID response (${0}$)'.format(self.units))
        self.ax.set_xlabel('Field Coil (mA)')
        self.ax.annotate(self.filename, xy=(0.02, .98), xycoords='axes fraction',
                        fontsize=8, ha='left', va='top', family='monospace')
        self.ax.annotate('max={0:2.2e}, min={1:2.2e}'.format(
                        np.max(self.Vmeas*self.conversion), np.min(self.Vmeas*self.conversion)), 
                        xy=(0.02, .1), xycoords='axes fraction',
                        fontsize=8, ha='left', va='top', family='monospace')
        self.ax.set_title(self.title)

    def plot_fit(self):
        fit = np.polyfit(self.Vsrc / self.Rbias / 1e-3, self.Vmeas * self.conversion, 1)
        xs = np.linspace(self.Vsrc[0] /self.Rbias / 1e-3,
                         self.Vsrc[-1]/self.Rbias / 1e-3, 100)
        ys = np.poly1d(fit)(xs)
        self.ax.plot(xs, ys, linestyle='--',
                    label='M={0:3.3f} $\phi_0/A$'.format(fit[0]*1e3))
        self.ax.legend()



class MutualInductance(Measurement):
    instrument_list = ['squidarray', 'lockin_squid', 'lockin_I']

    def __init__(self, instruments = {}, Rmeas=3172, Istart=5e-6, Iend=30e-6,
                 numamps=10, fstart = 100, fend = 20000, numf= 10):
        super().__init__(instruments=instruments)
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
                #self.squidarray.reset()
                time.sleep(3)
                self.V[i,j] = self.lockin_squid.X
                self.I[i,j] = self.lockin_I.X/self.Rmeas
                self.plot()


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
    ### NEEDS CLEANUP ###

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
    instrument_list = ['daq', 'preamp']
    _daq_inputs = ['squid_out']
    _daq_outputs = ['squid_bias', 'mod_source', 'field_source']

    def __init__(self, s_bias, r_bias_squid, r_bias_mod, r_bias_field,
                 instruments = {}, I_mod_i = 0, I_mod_f = 0, num_mod = 100,
                 I_field_i = 0, I_field_f = 0, num_field = 10, rate = 100):

        super().__init__(instruments=instruments)
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
                         np.nan)

    def do(self):
        '''
        Perform the MI measurement
        '''
        # Bias the SQUID to the desired working point
        _,_ = self.daq.sweep(
            {'squid_bias': self.daq.outputs['squid_bias'].V},
            {'squid_bias': self.s_bias * self.r_bias_squid},
            sample_rate=10000, numsteps = 10000)
        for i, f in enumerate(self.field_current):
            # Source a current to the field coil
            _,_ = self.daq.sweep(
                {'field_source': self.daq.outputs['field_source'].V},
                {'field_source': f * self.r_bias_field},
                sample_rate = 10000, numsteps = 10000)
            # Now sweep the current in the mod coil
            output_data, recieved = self.daq.sweep(
                {'mod_source': self.I_mod_i * self.r_bias_mod},
                {'mod_source': self.I_mod_f * self.r_bias_mod},
                chan_in = ['squid_out'], sample_rate = self.rate,
                numsteps = self.num_mod)
            self.V[:, i] = np.array(recieved['squid_out'])/self.preamp.gain
