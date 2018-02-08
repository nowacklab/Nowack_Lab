import numpy as np
import matplotlib.pyplot as plt
from ..Utilities.save import Measurement
from ..Utilities.nestedmeasurement import NestedMeasurement
from scipy.interpolate import UnivariateSpline
from ..Utilities.plotting import plot_mpl

class SQUID_IV(Measurement):
    ''' Take Squid IV'''
    _daq_inputs = ['iv']
    _daq_outputs = ['iv']
    instrument_list = ['daq']

    _XLABEL = r'$I_{squid}$ ($\mu A$)'
    _YLABEL = r'$V_{squid}$ ($\mu V$)'

    _IV_MAX_I = 100e-6

    def __init__(self,
                 instruments = {},
                 iv_Is = np.linspace(-100e-6,100e-6,1000),
                 iv_Rbias = 2000,
                 samplerate = 1000,
                 gain = 5000, # FIXME
                 ):
        '''
        Make a SQUID IV

        Arguments:
            instruments (dict): instruments for measurement
            iv_Is       (nparray): currents to set, approximate
            iv_Rbias    (float): resistance of cold+warm bias on IV
            samplerate  (float): samples/s for measurement
            gain        (float): gain on preamp
        '''
        super().__init__(instruments=instruments)
        
        self.iv_Rbias  = iv_Rbias
        self.iv_Is     = np.array(iv_Is)
        self.iv_Vs     = self.iv_Is * self.iv_Rbias
        self.samplerate= samplerate
        self.gain      = gain

        self._safetychecker()

    def _safetychecker(self):
        if max(abs(self.iv_Is)) > self._IV_MAX_I:
            print('WARNING: max({2} current) = {0} > {1}'.format(
                max(abs(self.iv_Is)),
                self._IV_MAX_I,
                self._daq_outputs[0]
                )
            )

    def do(self, hysteresis=True, safe=True, plot=True, removeplot=False):
        '''
        Run measurement

        Arguments:
            hysteresis  (boolean): sweep up and down?
            safe        (boolean): sweep to first voltage, then to zero at end?
            plot        (boolean): should I plot?
            removeplot  (boolean): close plot upon completion?
        '''
        # Sweep to the first voltage if running safe
        if safe: 
            _,_ = self.daq.singlesweep(self._daq_outputs[0], self.iv_Vs[0], 
                                       numsteps=len(self.iv_Vs)/2)
        
        # Sweep voltage up
        fu_od, fu_r = self.daq.sweep(
            Vstart = {self._daq_outputs[0]: self.iv_Vs[ 0]},
            Vend   = {self._daq_outputs[0]: self.iv_Vs[-1]},
            chan_in = self._daq_inputs,
            sample_rate = self.samplerate,
            numsteps = len(self.iv_Vs)
        )
        
        # Sweep voltage down, if doing hysteresis
        if hysteresis:
            fd_od, fd_r = self.daq.sweep(
                Vstart = {self._daq_outputs[0]: self.iv_Vs[-1]},
                Vend   = {self._daq_outputs[0]: self.iv_Vs[ 0]},
                chan_in = self._daq_inputs,
                sample_rate = self.samplerate,
                numsteps = len(self.iv_Vs)
            )

        # Sweep voltage to zero, if running safe
        if safe: 
            _,_ = self.daq.singlesweep(self._daq_outputs[0], 0,
                                       numsteps=len(self.iv_Vs)/2)

        # save data in object
        self.Vmeas_up = np.array( fu_r[self._daq_inputs[0]]/self.gain)
        self.Vsrc_up  = np.array(fu_od[self._daq_outputs[0]])

        if hysteresis:
            self.Vmeas_down = np.array( fd_r[self._daq_inputs[0]]/self.gain)
            self.Vsrc_down  = np.array(fd_od[self._daq_outputs[0]])
        
        # Plot
        if plot:
            self.plot(hysteresis=hysteresis)

        # If I want to close plots, e.g. Mod2D, do so
        if removeplot:
            plt.close()


    def plot(self, hysteresis=True):
        super().plot()
        self.ax.plot(self.Vsrc_up / self.iv_Rbias / 1e-6, 
                     self.Vmeas_up / 1e-6,
                     label='UP')
        if hysteresis:
            self.ax.plot(self.Vsrc_down / self.iv_Rbias / 1e-6,
                         self.Vmeas_down / 1e-6,
                         label='DOWN')
            self.ax.legend()
        self.ax.set_xlabel(self._XLABEL)
        self.ax.set_ylabel(self._YLABEL)
        self.ax.annotate(self.filename, xy=(.02,.98), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')
        self.ax.annotate('rate={0:2.2f} Sa/s'.format(self.samplerate), 
                         xy=(.02, .1), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')


    def plot_resistance(self, hysteresis=True):
        '''
        Trying to use filter to plot resistance.  Does not work
        '''
        self.ax_res = self.ax.twinx()
        s = self.Vsrc_up/self.iv_Rbias
        spacing = abs(s[0]-s[1])
        self.ax_res.plot(self.Vsrc_up / self.iv_Rbias / 1e-6,
                         np.gradient(savitzky_golay(self.Vmeas_up, 15, 13, 0), spacing),
                         #savitzky_golay(self.Vmeas_up, 15, 13, 0)/1e-6,
                         linestyle='-',
                         marker='o', markersize=1,
                         label='UP: dv/di')
        if hysteresis:
            self.ax_res.plot(self.Vsrc_down / self.iv_Rbias / 1e-6,
                         np.gradient(self.Vmeas_up, spacing),
                         linestyle='',
                         marker='o', markersize=1,
                         label='DOWN: dv/di')
        self.ax_res.set_ylabel('Resistance ($\Omega$)')
        self.ax_res.legend()

    def plot_resistance_spline(self, s=1e-8):
        '''
        Model IV with cubic spline with precision s.  
        Plots spline and derivative (resistance)

        Arguments:
            s (float): precision of fit, similar to max 
                       total least-squares error of fit
        '''
        try:
            self.ax_res.cla()
        except:
            self.ax_res = self.ax.twinx()

        try:
            self.ax.lines.pop(2)
            self.ax.lines.pop(2)
        except:
            pass
        sp_up = UnivariateSpline(self.Vsrc_up / self.iv_Rbias, self.Vmeas_up, s=s)
        sp_dw = UnivariateSpline(self.Vsrc_down[::-1] / self.iv_Rbias, self.Vmeas_down[::-1], s=s)
        sp_up_1 = sp_up.derivative()
        sp_dw_1 = sp_dw.derivative()

        xs = np.linspace(self.Vsrc_up[0], self.Vsrc_up[-1],1000) / self.iv_Rbias

        self.ax.plot(xs/1e-6, sp_up(xs)/1e-6, label='up spline')
        self.ax.plot(xs/1e-6, sp_dw(xs)/1e-6, label='down spline')
        self.ax_res.plot(xs/1e-6, sp_up_1(xs), linestyle='--',label='Rup (spline, s={0}'.format(s))
        self.ax_res.plot(xs/1e-6, sp_dw_1(xs), linestyle='--',label='Rdown (spline, s={0}'.format(s))
        self.ax_res.set_ylabel('Resistance ($\Omega$)')

        #self.ax.legend()
        #self.ax_res.legend()

        lines = self.ax.lines+self.ax_res.lines
        labels = [l.get_label() for l in lines]
        self.ax.legend(lines, labels)


    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        plt.pause(.01)


class SQUID_Mod(Measurement):
    _daq_outputs = ['mod']
    instrument_list = ['daq']
    _MOD_MAX_I = 100e-6
    _NESTED_CALLABLE = SQUID_IV
    _cmap = 'coolwarm'
    _xlabel=r'$I_{IV}$ ($\mu$ A)'
    _ylabel=r'$I_{Mod}$ ($\mu$ A)'
    _clabel=r'$V_{squid} (V)$'

    def __init__(self,
                 instruments = {},
                 iv_Is = np.linspace(-100e-6,100e-6,100),
                 mod_Is = np.linspace(-100e-6,100e-6,100),
                 iv_Rbias = 2000,
                 mod_Rbias = 2000,
                 samplerate = 1000,
                 gain = 5000, # FIXME
                 ):
        '''
        SQUID_Mod: Create an object take squid modulations

        Arguments:
            instruments (dict): dictionary of instruments
            iv_Is       (nparray): currents passed to SQUID_IV
            mod_Is      (nparray): currents to set mod coil for each SQUID_IV
            iv_Rbias    (float): bias resistor for IV
            mod_Rbias   (float): bias resistor for Mod
            samplerate  (float): samples/s sampling rate
            gain        (float): gain of preamp

        '''
        super().__init__(instruments=instruments)
        self.mod_Is     = mod_Is
        self.iv_Is      = iv_Is
        self.iv_Rbias   = iv_Rbias
        self.mod_Rbias  = mod_Rbias
        self.samplerate = samplerate
        self.gain       = gain
        self.instruments = instruments

        self.mod_Vs = self.mod_Is * self.mod_Rbias
        self.V = np.full( (len(self.mod_Is), len(self.iv_Is)), np.nan)
        self._safetychecker()

    def _safetychecker(self):
        if max(abs(self.mod_Is)) > self._MOD_MAX_I:
            print('WARNING: max({2} current) = {0} > {1}'.format(
                max(abs(self.mod_Is)),
                SQUID_Mod._MOD_MAX_I,
                self._daq_outputs[0]
                ))

    def do(self):

        _,_ = self.daq.singlesweep(self._daq_outputs[0], self.mod_Vs[0], 
                              numsteps=len(self.mod_Vs)/2)
        filenames = []
        ivs = []
        # multithread this?
        i = 0
        for m_v in self.mod_Vs:
            self.daq.outputs[self._daq_outputs[0]].V = m_v
            iv = self._NESTED_CALLABLE(self.instruments, 
                          self.iv_Is,
                          self.iv_Rbias,
                          self.samplerate,
                          self.gain
                         )
            ivs.append(iv)
            iv.run(save_appendedpath = self.filename, removeplot=True)

            self.V[i,:] = iv.Vmeas_up

            self.plot()
            i += 1

        _,_ = self.daq.singlesweep(self._daq_outputs[0], 0, numsteps=len(self.mod_Vs)/2)
       
        del self.instruments


    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.im = plot_mpl.plot2D(self.ax, 
                                  self.iv_Is*1e6, 
                                  self.mod_Is*1e6,
                                  self.V,
                                  cmap=self._cmap,
                                  xlabel=self._xlabel,
                                  ylabel=self._ylabel,
                                  clabel=self._clabel,
                                  equal_aspect=False
                                  )
        self.ax.set_title(self.filename)


    def plot(self):
        plot_mpl.update2D(self.im, self.V, equal_aspect=False)
        plot_mpl.aspect(self.ax, 1)
        plt.pause(0.01)

    def plot_cut_iv(self, ivcurrent):
        i = np.abs(self.iv_Is - ivcurrent).argmin()
        v = self.V[:,i]
        fig,ax = plt.subplots()
        ax.plot(self.mod_Is*1e6, v*1e6)
        ax.set_xlabel('Mod current ($\mu$ A)')
        ax.set_ylabel('Squid Voltage ($\mu$ V)')
        ax.annotate(self.filename, xy=(.02,.98), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')
        ax.annotate('Imod = {0:2.2f} uA'.format(ivcurrent*1e6), 
                         xy=(.02,.1), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')
        pass

    def max_modulation(self):
        '''
        Find the iv current that maximizes the squid response as a function
        of modulation current.  Plot it
        '''
        maxmod = 0
        current = 0
        for i,ivcurrent in zip(range(len(self.iv_Is)), self.iv_Is):
            v = self.V[:,i]
            if maxmod < (abs(max(v) - min(v))):
                maxmod = abs( max(v)-min(v) )
                current = ivcurrent
        self.plot_cut_iv(current)
        return current


class SQUID_FCIV(SQUID_IV):
    _daq_inputs = ['iv']
    _daq_outputs = ['fc']
    instrument_list = ['daq']
    

    _XLABEL = r'$I_{fc}$ ($\mu A$)'
    _YLABEL = r'$V_{squid}$ ($\mu V$)'

    _IV_MAX_I = 2e-3


    def __init__(self,
                 instruments = {},
                 fc_Is = np.linspace(-.5e-3, .5e-3, 100),
                 fc_Rbias = 2000,
                 samplerate = 1000,
                 gain = 5000,
                 ):
        '''
        Make a SQUID IV

        Arguments:
            instruments (dict): instruments for measurement
            fc_Is       (nparray): currents to set, approximate
            fc_Rbias    (float): resistance of cold+warm bias on IV
            samplerate  (float): samples/s for measurement
            gain        (float): gain on preamp
        '''
        super().__init__(instruments=instruments,
                         iv_Is = fc_Is,
                         iv_Rbias = fc_Rbias,
                         samplerate = samplerate,
                         gain=gain
                         )

                
class SQUID_FC(SQUID_Mod):
    _daq_outputs = ['mod','iv']
    instrument_list = ['daq']
    _MOD_MAX_I = 100e-6
    _IV_MAX_I = 100e-6
    _NESTED_CALLABLE = SQUID_FCIV
    _cmap = 'magma'

    _xlabel = r'$I_{fc}$ ($\mu A$)'
    _ylabel = r'$I_{mod}$ ($\mu V$)'
    _clabel = r'$V_{squid}$ ($\mu V$)'

    def __init__(self,
                 instruments = {},
                 iv_I = 20e-6,
                 fc_Is = np.linspace(-.5e-3, .5e-3, 100),
                 mod_Is = np.linspace(-100e-6,100e-6, 100),
                 iv_Rbias = 2000,
                 fc_Rbias = 2000,
                 mod_Rbias = 2000,
                 samplerate = 1000,
                 gain = 5000,
                 ):
        '''
        SQUID_FC: Create an object take squid fieldcoil sweeps

        Arguments:
        '''
        super().__init__(instruments=instruments,
                         iv_Is = fc_Is,
                         mod_Is = mod_Is,
                         iv_Rbias = fc_Rbias,
                         mod_Rbias = mod_Rbias,
                         samplerate = samplerate,
                         gain=gain
                         )
        self.iv_I = iv_I
        self.iv_Rbias = iv_Rbias
        self.iv_V = self.iv_I * self.iv_Rbias
        # TODO: add checker here

    def do(self):
        _,_ = self.daq.singlesweep(self._daq_outputs[1], self.iv_V,
                              numsteps=len(self.mod_Vs)/2)
        super().do()
        _,_ = self.daq.singlesweep(self._daq_outputs[1], 0,
                              numsteps=len(self.mod_Vs)/2)

    def plot(self):
        super().plot()
        self.ax.annotate('Squid Ibias = {0:2.2f} uA'.format(self.iv_I*1e6), 
                        xy=(.02,.98), xycoords='axes fraction',
                        fontsize=8, ha='left', va='top', family='monospace')


class SQUID_SAA_FC(Measurement):
    _instrument_list = ['daq', 'squidarray']
    _daq_outputs = ['fc']
    _daq_inputs = ['dc']

    def __init__(self,
                 instruments = {},
                 fc_Is = np.linspace(-.5e-3,.5e-3, 100),
                 fc_Rbias = 2000,
                 ):
        pass


