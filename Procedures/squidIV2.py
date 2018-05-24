import numpy as np
import matplotlib.pyplot as plt
from importlib import reload
from scipy.interpolate import UnivariateSpline
from ..Utilities.plotting import plot_mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.signal import savgol_filter

# Nowack_Lab imports
import Nowack_Lab.Utilities.save
reload(Nowack_Lab.Utilities.save)
from Nowack_Lab.Utilities.save import Measurement


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
                                       numsteps=len(self.iv_Vs)/2, 
                                       sample_rate=self.samplerate)
        
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
                                       numsteps=len(self.iv_Vs)/2,
                                       sample_rate=self.samplerate)

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
        Is = self.Vsrc_up/self.iv_Rbias
        self.ax.annotate('Rshunt ~ {0:2.2f} ohms'.format( 
                            np.abs( np.max(self.Vmeas_up) - 
                                    np.min(self.Vmeas_up))/
                            np.abs( Is[np.argmax(self.Vmeas_up)] - 
                                    Is[np.argmin(self.Vmeas_up)])/2),
                            xy=(.7, .98), xycoords='axes fraction',
                            fontsize=8, ha='left', va='top', family='monospace'
                            
                        )


    def plot_resistance(self, hysteresis=True):
        '''
        Trying to use filter to plot resistance.  Does not work
        '''
        self.ax_res = self.ax.twinx()
        s = self.Vsrc_up/self.iv_Rbias/1e-6
        spacing = abs(s[0]-s[1])
        self.ax_res.plot(self.Vsrc_up / self.iv_Rbias / 1e-6,
#              savgol_filter(
                         savgol_filter(self.Vmeas_up, window_length=21, polyorder=5, 
                                       deriv=1, delta=spacing)/1e-6, 
#                         window_length=9, polyorder=3),
                         #np.gradient(savitzky_golay(self.Vmeas_up, 15, 13, 0), spacing),
                         #savitzky_golay(self.Vmeas_up, 15, 13, 0)/1e-6,
                         linestyle='',
                         marker='.', markersize=1,
                         label='UP: dv/di')
        if hysteresis:
            self.ax_res.plot(self.Vsrc_down / self.iv_Rbias / 1e-6,
#              savgol_filter(
                         -1*savgol_filter(self.Vmeas_down, window_length=21, polyorder=5, 
                                       deriv=1, delta=spacing)/1e-6,
#                         window_length=9, polyorder=3),
                         linestyle='',
                         marker='.', markersize=1,
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
        self.ax_res.plot(xs/1e-6, sp_up_1(xs), linestyle='--',label='Rup (spline, s={0})'.format(s))
        self.ax_res.plot(xs/1e-6, sp_dw_1(xs), linestyle='--',label='Rdown (spline, s={0})'.format(s))
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
    _numcontour = 30

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
        self.V_down = np.full( (len(self.mod_Is), len(self.iv_Is)), np.nan)
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
                              numsteps=len(self.mod_Vs)/2,
                              sample_rate=self.samplerate)
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
            self.V_down[i,:] = iv.Vmeas_down

            self.plot()
            i += 1

        _,_ = self.daq.singlesweep(self._daq_outputs[0], 0, numsteps=len(self.mod_Vs)/2,
                                    sample_rate=self.samplerate)

        self.plot_contour(numcontours = self._numcontour)
       
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

    def plot_contour(self, numcontours=30):
        self.ax.contour(self.iv_Is*1e6, self.mod_Is*1e6, self.V, numcontours)

    def plot_cut_iv(self, ivcurrent, ax=None):
        i = np.abs(self.iv_Is - ivcurrent).argmin()
        v = self.V[:,i]
        if ax == None:
            fig,ax = plt.subplots()
        ax.plot(self.mod_Is*1e6, v*1e6)
        ax.set_xlabel('Mod current ($\mu$ A)')
        ax.set_ylabel('Squid Voltage ($\mu$ V)')
        ax.annotate(self.filename, xy=(.02,.98), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')
        ax.annotate('Imod = {0:2.2f} uA'.format(ivcurrent*1e6), 
                         xy=(.02,.1), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')

    def max_modulation(self, ax=None):
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
        self.plot_cut_iv(current, ax=ax)
        return current

    def plot_dvdi(self, ax=None):
        pass


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
    _numcontour = 5 

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
                              numsteps=len(self.mod_Vs)/2,
                              sample_rate=self.samplerate)
        super().do()
        _,_ = self.daq.singlesweep(self._daq_outputs[1], 0,
                              numsteps=len(self.mod_Vs)/2,
                              sample_rate=self.samplerate)

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

class SQUID_IV_MOD(SQUID_IV):
    '''For constant squid current bias, sweep modulation'''
    _daq_inputs = ['iv']
    _daq_outputs = ['mod']
    instrument_list = ['daq']

    _XLABEL = r'$I_{mod}$ ($\mu A$)'
    _YLABEL = r'$V_{squid}$ ($\mu V$)'

    _IV_MAX_I = 100e-6

    def __init__(self,
                 instruments = {},
                 mod_Is = np.linspace(-100e-6,100e-6,1000),
                 mod_Rbias = 2000,
                 samplerate = 1000,
                 gain = 5000, # FIXME
                 ):
        super().__init__(instruments=instruments,
                         iv_Is = mod_Is,
                         iv_Rbias = mod_Rbias,
                         samplerate = samplerate,
                         gain=gain
                         )
        
class SQUID_Mod_FastMod(SQUID_Mod):
    _daq_outputs = ['iv']
    instrument_list = ['daq']
    _MOD_MAX_I = 100e-6
    _NESTED_CALLABLE = SQUID_IV_MOD
    _cmap = 'coolwarm'
    _xlabel=r'$I_{IV}$ ($\mu$ A)'
    _ylabel=r'$I_{Mod}$ ($\mu$ A)'
    _clabel=r'$V_{squid} (V)$'
    _numcontour = 30
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
        SQUID_Mod_FastMod: Create an object take squid modulations

        ****Work In Progress****

        Note: this uses SQUID_MOD but switches iv and mod labels

        Arguments:
            instruments (dict): dictionary of instruments
            iv_Is       (nparray): currents to set SQUID bias for each SQUID_IV_MOD
            mod_Is      (nparray): currents passed to SQUID_IV_MOD for mod coil
            iv_Rbias    (float): bias resistor for IV
            mod_Rbias   (float): bias resistor for Mod
            samplerate  (float): samples/s sampling rate
            gain        (float): gain of preamp

        '''
        super().__init__(instruments=instruments,
                         iv_Is = mod_Is,
                         mod_Is = iv_Is,
                         iv_Rbias = mod_Rbias,
                         mod_Rbias = iv_Rbias,
                         samplerate = samplerate,
                         gain=gain)

    def plot(self):
        plot_mpl.update2D(self.im, self.V.T, equal_aspect=False)
        plot_mpl.aspect(self.ax, 1)
        plt.pause(0.01)

    def plot_contour(self, numcontours=30):
        self.ax.contour(self.mod_Is*1e6, self.iv_Is*1e6,  self.V.T, numcontours)

class ThreeParam_Sweep(Measurement):
    _daq_inputs = ['iv']
    _daq_outputs = ['fc', 'mod', 'iv']
    instrument_list = ['daq', 'preamp']
    '''
    Inherit this class to do fast parameter sweeps for in depth 
    mod coil sweeps and field coil sweeps
    '''

    def __init__(self, instruments=[],
                daqout_I0s = [],
                daqout_I1s = [],
                daqout_I2s = [],
                daqout_R0 = 2400,
                daqout_R1 = 2400,
                daqout_R2 = 2400,
                samplerate = 10000,
                ):
        '''
        Generic three paramter sweep on daq for squid iv (mod2d, fc2d)
        
        Arguments:
        instruments: dictionary of instruments
        daqout_I0s:  nparray of currents, slowest swept
        daqout_I1s:  nparray of currents, middle swept
        daqout_I2s:  nparray of currents, fastest swept
        daqout_R0:   resistance to convert I0s to V0s
        daqout_R1:   resistance to convert I1s to V1s
        daqout_R2:   resistance to convert I2s to V2s
        samplerate:  rate to take points

        For instance, if we want to do a mod 2D with fast iv, 
        I0 would be for fc, I1 would be for mod, and I2 would
        be for iv.  

        The ith element of ThreeParam_sweep._daq_outputs is 
        tied to daqout_Iis, daqout_Vis, and daqoutRi.

        Voltages read are in Vmeas.  
        Voltages applied are in Vsrc

        Vmeas.shape = (len(daqout_I0s), len(daqout_I1s), 
                       2 (increasing V, decreasing V),
                       len(daqout_I2s))
        Vsrc.shape = (len(daqout_I0s), len(daqout_I1s), 
                       2 [increasing V, decreasing V],
                       len(daqout_I2s), 
                       3 [daqout_V0, daqout_V1, daqout_V2])
        '''
        super().__init__(instruments=instruments)
        self.samplerate = samplerate
        self.daqout_I0s = np.array(daqout_I0s)
        self.daqout_I1s = np.array(daqout_I1s)
        self.daqout_I2s = np.array(daqout_I2s)
        self.daqout_R0  = daqout_R0
        self.daqout_R1  = daqout_R1
        self.daqout_R2  = daqout_R2
        self.daqout_V0s = self.daqout_I0s * self.daqout_R0
        self.daqout_V1s = self.daqout_I1s * self.daqout_R1
        self.daqout_V2s = self.daqout_I2s * self.daqout_R2

        self.Vmeas = np.full((self.daqout_V0s.shape[0], 
                          self.daqout_V1s.shape[0], 
                          2,
                          self.daqout_V2s.shape[0]
                          ), np.nan
                        )
        self.Vsrc = np.full((self.daqout_V0s.shape[0], 
                          self.daqout_V1s.shape[0], 
                          2,
                          self.daqout_V2s.shape[0],
                          3
                          ), np.nan
                        )

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()

    def plot(self):
        pass

    def _do(self, i, j):
        daqoutch = self._daq_outputs[2]
        self._sweeptopt(daqoutch, self.daqout_V2s[0], self.daqout_V2s)

        fu_src, fu_meas = self.daq.sweep(
            Vstart = {daqoutch: self.daqout_V2s[0]},
            Vend   = {daqoutch: self.daqout_V2s[-1]},
            chan_in = self._daq_inputs,
            sample_rate = self.samplerate,
            numsteps = len(self.daqout_V2s)
        )

        fd_src, fd_meas = self.daq.sweep(
            Vstart = {daqoutch: self.daqout_V2s[0]},
            Vend   = {daqoutch: self.daqout_V2s[-1]},
            chan_in = self._daq_inputs,
            sample_rate = self.samplerate,
            numsteps = len(self.daqout_V2s)
        )


        # i    : 0th entry of self._daq_outputs
        # j    : 1st entry of self._daq_outputs
        # [0,1]: up or down
        # data or each element of vsrc for that measured data point

        self.Vmeas[i][j][0] = np.array(fu_meas[self._daq_inputs[0]]/self.preamp.gain)
        self.Vmeas[i][j][1] = np.array(fd_meas[self._daq_inputs[0]]/self.preamp.gain)
        self.Vsrc [i][j][0][:,0] = np.ones(fu_src[self._daq_outputs[2]].shape
                                        ) * self.daq.outputs[self._daq_outputs[0]].V
        self.Vsrc [i][j][1][:,0] = np.ones(fu_src[self._daq_outputs[2]].shape
                                        ) * self.daq.outputs[self._daq_outputs[0]].V
        self.Vsrc [i][j][0][:,1] = np.ones(fu_src[self._daq_outputs[2]].shape
                                     ) * self.daq.outputs[self._daq_outputs[1]].V
        self.Vsrc [i][j][1][:,1] = np.ones(fu_src[self._daq_outputs[2]].shape
                                     ) * self.daq.outputs[self._daq_outputs[1]].V
        self.Vsrc [i][j][0][:,2] = np.array(fu_src[self._daq_outputs[2]])
        self.Vsrc [i][j][1][:,2] = np.array(fd_src[self._daq_outputs[2]])
        

        self._sweeptopt(self._daq_outputs[2], 0, self.daqout_V2s)
        

    def _sweeptopt(self, output, voltage, outputarray):
        _,_ = self.daq.singlesweep(output, voltage, 
                                   numsteps=max(int(len(outputarray)/2), 3), 
                                   sample_rate=self.samplerate)

    def do(self):
        # Slowly go to first voltage in daqout_V0
        self._sweeptopt(self._daq_outputs[0], self.daqout_V0s[0], self.daqout_V0s)

        for i in range(0,len(self.daqout_V0s)):
            # quickly go to ith voltage in daqout_V0.  Will always be close
            self._sweeptopt(self._daq_outputs[0], self.daqout_V0s[i], [])

            # slowly go to the first voltage in daqout_V1
            self._sweeptopt(self._daq_outputs[1], self.daqout_V1s[0], self.daqout_V1s)

            for j in range(0,len(self.daqout_V1s)):
                # quickly go to the jth voltage in daqout_V1.  will always be close
                self._sweeptopt(self._daq_outputs[1], self.daqout_V1s[j], [])
                self._do(i,j)

        self._sweeptopt(self._daq_outputs[0], 0, self.daqout_V0s)
        self._sweeptopt(self._daq_outputs[1], 0, self.daqout_V1s)
        self._sweeptopt(self._daq_outputs[2], 0, self.daqout_V2s)

        self.plot()

    @staticmethod
    def plot_lines(ax, vsquids, ibias):
        offset = 0
        for i in range(vsquids.shape[0]):
            offset += 4*np.std(vsquids[i])
            ax.plot(ibias, vsquids[i] + offset - np.mean(vsquids[i]),
                    linestyle='',marker='.', markersize=1)
        return ax
            
    #@staticmethod
    #def plot_color(obj,ax):
    #    imd = obj.Vmeas[0,:,0,:]*1e6
    #    im = ax.imshow(imd, 
    #                   extent=(obj.mod_Is[0]*1e6, obj.mod_Is[-1]*1e6,
    #                           obj.iv_Is[0]*1e6,  obj.iv_Is[-1]*1e6),
    #                   aspect='auto')
    #    self.ax.set_xlabel('Imod (uA)')
    #    self.ax.set_xlabel('ISquid (uA)')

    @staticmethod
    def plot_color_diff(obj,ax):
        imd = obj.Vmeas[0,:,0,:]*1e6 - np.tile(np.mean(imd, axis=1))
        im = ax.imshow(obj.imd, 
                       extent=(obj.mod_Is[0]*1e6, obj.mod_Is[-1]*1e6,
                               obj.iv_Is[0]*1e6,  obj.iv_Is[-1]*1e6),
                       aspect='auto')
        self.ax.set_xlabel('Imod (uA)')
        self.ax.set_xlabel('ISquid (uA)')

    @staticmethod
    def plot_color(ax, xaxis, yaxis, z, cmap='viridis'):
        im = ax.imshow(z, cmap, extent=(xaxis[0], xaxis[-1], yaxis[0], yaxis[-1]),
                        aspect='auto')
        d = make_axes_locatable(ax)
        cax = d.append_axes('right', size=.1, pad=.1)
        cbar = plt.colorbar(im, cax=cax)
        
        return [ax, cbar]

    @staticmethod
    def plot_color_gradient(ax, xaxis, yaxis, z, cmap='viridis'):
        delta = np.abs(xaxis[0]-xaxis[1])
        gradient = savgol_filter(z, 11, 5, deriv=1, delta=delta)
        return ThreeParam_Sweep.plot_color(ax, xaxis, yaxis, gradient, cmap)

    @staticmethod
    def plot_color_absgradient(ax, xaxis, yaxis, z, cmap='viridis'):
        delta = np.abs(xaxis[0]-xaxis[1])
        gradient = np.abs(savgol_filter(z, 11, 5, deriv=1, delta=delta))
        return ThreeParam_Sweep.plot_color(ax, xaxis, yaxis, gradient, cmap)

    @staticmethod
    def plot_fastmod(fig, axs, v, Ix, Iy, Ixlabel, Iylabel, vlabel, dirlabel, filename):
        axs[2] = ThreeParam_Sweep.plot_lines( axs[2], v, Ix)
        axs[2].set_xlabel(Ixlabel)
        axs[2].set_ylabel(vlabel)

        axs[0], cbar = ThreeParam_Sweep.plot_color(axs[0], Ix, Iy, v,
                                                       cmap='coolwarm')
        axs[0].set_ylabel(Iylabel)
        axs[0].set_xlabel(Ixlabel)
        cbar.set_label(vlabel)

        axs[1], cbar1 = ThreeParam_Sweep.plot_color_absgradient(
                            axs[1], Ix, Iy, v)
        axs[1].set_ylabel(Iylabel)
        axs[1].set_xlabel(Ixlabel)
        cbar1.set_label(dirlabel)

        for ax in axs:
            ax.annotate(filename, xy=(.02,.98), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')

        fig.tight_layout()
        return [fig,axs]




        

class SQUID_Mod_FastIV(ThreeParam_Sweep):
    _daq_inputs = ['iv']
    _daq_outputs = ['fc', 'mod', 'iv']
    instrument_list = ['daq', 'preamp']
    '''
    Creates mod 2D plot quickly.  
    No plotting until the end.
    Saves all data in numpy arrays in a 
    rather complicated structure set 
    by ThreeParam_Sweep.

    Sweeps IV fast, mod slow
    '''

    def __init__(self, instruments=[],
                mod_Is = [],
                iv_Is  = [],
                mod_R = 2400,
                iv_R  = 2400,
                samplerate = 10000,
                ):
        super().__init__(instruments=instruments,
                        daqout_I0s = np.zeros(1), 
                        daqout_I1s = mod_Is,
                        daqout_I2s = iv_Is,
                        daqout_R0 = 2400,
                        daqout_R1 = mod_R,
                        daqout_R2 = iv_R,
                        samplerate = samplerate
                        )
        self.mod_Vs = self.daqout_V1s
        self.iv_Vs  = self.daqout_V2s
        self.mod_Is = self.daqout_I1s
        self.iv_Is  = self.daqout_I2s
        self.iv_R   = self.daqout_R2
        self.mod_R  = self.daqout_R1

    def do(self):
        super().do()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots(1,2, figsize=(16,6))
        self.ax = list(self.ax)


    def plot(self):
        self.ax[0], cbar = SQUID_Mod_FastIV.plot_color(
                            self.ax[0], 
                            self.iv_Is*1e6, 
                            self.mod_Is*1e6, 
                            self.Vmeas[0,:,0,:]*1e6,
                            cmap='coolwarm')
        self.ax[0].set_xlabel('Isquid (uA)')
        self.ax[0].set_ylabel('Imod   (uA)')
        cbar.set_label('V squid (uV)')

        self.ax[1], cbar1 = SQUID_Mod_FastIV.plot_color_absgradient(
                            self.ax[1],
                            self.iv_Is*1e6,
                            self.mod_Is*1e6,
                            self.Vmeas[0,:,0,:]*1e6)
        self.ax[1].set_xlabel('Isquid (uA)')
        self.ax[1].set_ylabel('Imod   (uA)')
        cbar1.set_label(r'$|\frac{\mathrm{d}V_{\rm squid}}{\mathrm{d}I_{\rm bias}}|$')

        for ax in self.ax:
            ax.annotate(self.filename, xy=(.02,.98), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')

        self.fig.tight_layout()

class SQUID_Mod_FastMod(ThreeParam_Sweep):
    '''
    Creates mod 2D plot quickly.  
    No plotting until the end.
    Saves all data in numpy arrays in a 
    rather complicated structure set 
    by ThreeParam_Sweep.

    Sweeps mod fast, iv slow
    '''
    _daq_inputs = ['iv']
    _daq_outputs = ['fc', 'iv', 'mod']
    instrument_list = ['daq', 'preamp']

    def __init__(self, instruments=[],
                mod_Is = [],
                iv_Is  = [],
                mod_R = 2400,
                iv_R  = 2400,
                samplerate = 10000,
                ):
        super().__init__(instruments=instruments,
                        daqout_I0s = np.zeros(1), 
                        daqout_I2s = mod_Is,
                        daqout_I1s = iv_Is,
                        daqout_R0 = 2400,
                        daqout_R2 = mod_R,
                        daqout_R1 = iv_R,
                        samplerate = samplerate
                        )
        self.mod_Vs = self.daqout_V2s
        self.iv_Vs  = self.daqout_V1s
        self.mod_Is = self.daqout_I2s
        self.iv_Is  = self.daqout_I1s
        self.iv_R   = self.daqout_R1
        self.mod_R  = self.daqout_R2

    def do(self):
        super().do()

    def plot_c(self):
        self.ax, cbar = SQUID_Mod_FastMod.plot_color(
                            self.ax, 
                            self.mod_Is*1e6, 
                            self.iv_Is*1e6, 
                            self.Vmeas[0,:,0,:]*1e6)
        self.ax.set_ylabel('Isquid (uA)')
        self.ax.set_mlabel('Imod   (uA)')
        cbar.set_label('V squid (uV)')

    def setup_plots(self):
        self.fig, self.ax = plt.subplots(1,3,figsize=(16,9))
        self.ax = list(self.ax)

    def plot(self):
        [self.fig, self.ax] = SQUID_FC_FastMod.plot_fastmod(
            fig=self.fig,
            axs=self.ax, 
            v=self.Vmeas[0,:,0,:]*1e6, 
            Ix=self.mod_Is*1e6, 
            Iy=self.iv_Is*1e6, 
            Ixlabel='Imod (uA)', 
            Iylabel='Isquid (uA)', 
            vlabel='Vsquid (uV)', 
            dirlabel=r'$|\frac{\mathrm{d}V_{\rm squid}}{\mathrm{d}I_{\rm mod}}|$', 
            filename=self.filename)


class SQUID_FC_FastMod(ThreeParam_Sweep):
    _daq_inputs = ['iv']
    _daq_outputs = ['iv', 'fc', 'mod']
    instrument_list = ['daq', 'preamp']

    def __init__(self, instruments=[],
                iv_I   = 10e-6,
                mod_Is = [],
                fc_Is  = [],
                mod_R = 2400,
                iv_R  = 2400,
                fc_R  = 2400,
                samplerate = 10000,
                ):
        super().__init__(instruments=instruments,
                        daqout_I0s = np.array([iv_I]),
                        daqout_I2s = mod_Is,
                        daqout_I1s = fc_Is,
                        daqout_R0 = iv_R,
                        daqout_R1 = fc_R,
                        daqout_R2 = mod_R,
                        samplerate = samplerate
                        )
        #TODO
        self.iv_I   = self.daqout_I0s[0]
        self.mod_Vs = self.daqout_V2s
        self.fc_Vs  = self.daqout_V1s
        self.mod_Is = self.daqout_I2s
        self.fc_Is  = self.daqout_I1s
        self.iv_R   = self.daqout_R0
        self.fc_R   = self.daqout_R0
        self.mod_R  = self.daqout_R2

    def do(self):
        super().do()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots(1,3,figsize=(16,9))
        self.ax = list(self.ax)

    def plot(self):
        [self.fig, self.ax] = SQUID_FC_FastMod.plot_fastmod(
            fig=self.fig,
            axs=self.ax, 
            v=self.Vmeas[0,:,0,:]*1e6, 
            Ix=self.mod_Is*1e6, 
            Iy=self.fc_Is*1e6, 
            Ixlabel='Imod (uA)', 
            Iylabel='Ifc (uA)', 
            vlabel='Vsquid (uV)', 
            dirlabel=r'$|\frac{\mathrm{d}V_{\rm squid}}{\mathrm{d}I_{\rm mod}}|$', 
            filename=self.filename)
