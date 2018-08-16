import time, numpy as np, matplotlib.pyplot as plt
from ..Utilities.save import Measurement
from .transport import RvsSomething, RvsVg
from ..Utilities.plotting import plot_mpl
import peakutils
from scipy.interpolate import interp1d
from scipy.stats import linregress

from ..Utilities.constants import e, h, G0

class RvsB(RvsSomething):
    instrument_list = ['ppms', 'lockin_V1', 'lockin_I']
    something='B'
    something_units = 'T'

    def __init__(self, instruments = {}, Bend = 1, delay=1, sweep_rate=.1):
        '''
        Sweep rate and field in T. Delay is in seconds. Rate is T/min
        '''
        super().__init__(instruments=instruments)

        # self.Bstart = Bstart
        self.Bend = Bend
        self.delay = delay
        self.sweep_rate = sweep_rate

    def do(self, plot=True, auto_gain=False):
        raise Exception('Got rid of Bstart. Check out code.')
        # Set initial field if not already there
        if abs(self.ppms.field - self.Bstart*10000) > 0.1: # different by more than 0.1 Oersted = 10 uT.
            self.ppms.field = self.Bstart*10000 # T to Oe
            time.sleep(5) # let the field start ramping to Bstart
            print('Waiting for field to sweep to Bstart...')
            while self.ppms.field_status in ('Iterating', 'Charging', 'WarmingSwitch', 'Unknown'): # wait until stabilized
                time.sleep(5)

        if abs(self.Bstart-self.Bend)*10000 < 0.1:
            return # sweeping between the same two fields, no point in doing the measurement

        print('Starting field sweep...')

        # Set sweep to final field
        self.ppms.field_rate = self.sweep_rate/60*10000# T/min to Oe/s
        self.ppms.field_mode = 'Persistent'
        self.ppms.field_approach = 'Linear'
        self.ppms.field = self.Bend*10000 # T to Oe

        while self.ppms.field_status not in ('Iterating', 'Charging'):
            time.sleep(2) # wait until the field is changing

        # Measure while sweeping
        while self.ppms.field_status in ('Iterating', 'Charging'):
            self.do_measurement(delay=self.delay, plot=plot, auto_gain=auto_gain)


    def plot_quantized_conductance(self, nu=1, Rxy_channel=1, Rxx_channel=0):
        '''
        Generate a plot with Gxy in units of nu*e^2/h. By default, the 1st lockin (the one
        used to source current) measures Rxy.
        '''
        fig, ax = plt.subplots()
        ax2 = ax.twinx()
        ax.set_xlabel('B (T)', fontsize=20)
        ax.set_ylabel('$G_{xy}\/(%se^2/h)$' %(str(nu) if nu!=1 else ''), fontsize=20, color='g')
        ax2.set_ylabel('$R_{xx}\/(\Omega)$', fontsize=20, color = 'b')
        G0 = e**2/h
        ax.plot(self.B, 1/self.R[Rxy_channel]/G0/nu, 'g')
        ax2.plot(self.B, self.R[Rxx_channel], 'b')
        ax.set_title(self.filename)
        ax.set_ylim(-40/nu,40/nu)

        return fig, ax, ax2

    def setup_label(self):
        '''
        Add sweep step size and delay to legend
        '''
        super().setup_label()

        def add_text_to_legend(text):
            if self.legendtitle is None:
                self.legendtitle = text
            else:
                self.legendtitle += '\n'+text

        add_text_to_legend('Rate = %.2f T/min' %self.sweep_rate)
        add_text_to_legend('delay = %.1f s' %self.delay)


class RvsB_BlueFors(RvsB):
    instrument_list = ['magnet', 'lockin_V1', 'lockin_I']

    def do(self, plot=True, auto_gain=False):
        raise Exception('MAGNET DRIVER WAS CHANGED. Also got rid of Bstart')
        # Set initial field if not already there
        if abs((self.magnet.B - self.Bstart)/self.magnet.B) > 0.01: # different by more than 1%
            self.magnet.ramp_to_field(self.Bstart, self.sweep_rate)
            time.sleep(5) # let the field start ramping to Bstart
            print('Waiting for field to sweep to Bstart...')
            self.magnet.wait()

        if abs(self.Bstart-self.Bend) < 10e-6:
            return # sweeping between the same two fields, no point in doing the measurement

        print('Starting field sweep...')

        ## Set sweep to final field
        self.magnet.ramp_to_field(self.Bend, self.sweep_rate)

        ## Measure while sweeping
        while self.magnet.status not in ('HOLDING', 'PAUSED', 'AT ZERO CURRENT'):
            self.do_measurement(delay=self.delay, plot=plot, auto_gain=auto_gain)

        for i in range(5): # do a few more measurements
            self.do_measurement(delay=self.delay, plot=plot, auto_gain=auto_gain)

        self.magnet.p_switch = False


class RvsB_Phil(RvsB):
    instrument_list = ['magnet', 'lockin_V1', 'lockin_I']

    def do(self, plot=True, auto_gain=False):

        if abs(self.magnet.Bmagnet-self.Bend) < 10e-6:
            return # sweeping between the same two fields, no point in doing the measurement

        print('Starting field sweep...')

        # Set sweep to final field
        self.magnet.ramp_to_field(self.Bend, Brate=self.sweep_rate, wait=False)

        # Measure while sweeping
        while self.magnet.status == 'RAMPING':
            self.do_measurement(delay=self.delay, plot=plot, auto_gain=auto_gain)

        while abs(self.magnet.Vmag-0.02) > 0.01:
            self.do_measurement(delay=self.delay, plot=plot, auto_gain=auto_gain)

        self.magnet.enter_persistent_mode()


class RvsVg_B(RvsVg):
    instrument_list = list(set(RvsB.instrument_list) | set(RvsVg.instrument_list))
    field_sweep_class = RvsB

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1,
                delay=1, sweep=1, Bstart = 0, Bend = 14, Bstep=1, Bdelay=1,sweep_rate=.1,
                Vg_sweep=None, raster=False):
        '''
        Does gatesweeps at a series of magnetic fields.
        Stores the full gatesweeps at each field, as well as a RvsB curve done
        at a particular gate voltage between gatesweeps.

        Vstart: start of gatesweep
        Vend: end of gatesweep
        Vstep: gatesweep voltage step size
        delay: gatesweep delay time
        sweep: sweep rate to Vstart (V/s)
        Bstart: starting field (Tesla)
        Bend: end field (Tesla)
        Bstep: field step between gatesweeps (Tesla)
        Bdelay: delay between resistance measurements during fieldsweep
        sweep_rate: field sweep rate (Tesla/min)
        Vg_sweep: gate voltage at which to do the field sweep (V). Leave at None if you don't care.
        raster: sweep forwards and backwards to save time with gatesweeps
        '''
        super().__init__(instruments=instruments, Vstart=Vstart, Vend=Vend, Vstep=Vstep, delay=delay)
        self.__dict__.update(locals()) # cute way to set attributes from arguments
        del self.self # but includes self, get rid of this!

        self.B = np.linspace(Bstart, Bend, round(abs(Bstart-Bend)/Bstep)+1)
        self.gs = RvsVg(self.instruments, self.Vstart, self.Vend, self.Vstep, self.delay)

        self.Vg = self.gs.Vg_values

        self.R2D = {i: np.full((len(self.B), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Vx2D = {i: np.full((len(self.B), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Vy2D = {i: np.full((len(self.B), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Ix2D = np.full((len(self.B), len(self.Vg)), np.nan)
        self.Iy2D = np.full((len(self.B), len(self.Vg)), np.nan)

        ## remember: shape of matrix given in y,x. So B is on the y axis and Vg on the x axis.

        # store full field sweep data
        self.Bfull = np.array([])
        for j in range(self.num_lockins):
            setattr(self, 'R%ifull' %j, np.array([]))

        self.gs_names = []

    def do(self, delay=0, auto_gain=False):
        '''
        delay: wait time after sweeping field
        '''
        for i, B in enumerate(self.B):
            if self.Vg_sweep is not None:
                self.keithley.sweep_V(self.keithley.V, self.Vg_sweep, self.Vstep, self.delay) # set desired gate voltage for the field sweep
            elif self.raster: # otherwise we will go as quickly as possible and reverse every other gatesweep
                self.Vstart, self.Vend = self.Vend, self.Vstart

            # reset field sweep
            self.fs = self.field_sweep_class(self.instruments,
                                        B, 1, self.sweep_rate)
            self.fs.run(plot=False)

            # Wait for cooling/stabilization
            time.sleep(delay)

            # store full field sweep data
            self.Bfull = np.append(self.Bfull, self.fs.B)
            for j in range(self.num_lockins):
                r = getattr(self, 'R%ifull' %j)
                setattr(self, 'R%ifull' %j, np.append(r, self.fs.R[j]))

            ## reset arrays for gatesweep
            self.gs = RvsVg(self.instruments, self.Vstart, self.Vend, self.Vstep, self.delay)
            self.gs.run(auto_gain=auto_gain)
            self.gs_names.append(self.gs.filename)

            for j in range(self.num_lockins):
                if self.Vstart > self.Vend:
                    self.R2D[j][i, :] = self.gs.R[j][::-1] # reverse if we did the sweep backwards
                    self.Vx2D[j][i, :] = self.gs.Vx[j][::-1] # reverse if we did the sweep backwards
                    self.Vy2D[j][i, :] = self.gs.Vy[j][::-1] # reverse if we did the sweep backwards
                    self.Ix2D[i, :] = self.gs.Ix[::-1] # reverse if we did the sweep backwards
                    self.Iy2D[i, :] = self.gs.Iy[::-1] # reverse if we did the sweep backwards
                else:
                    self.R2D[j][i, :] = self.gs.R[j] # first index is voltage channel, second is B, third is Vg. Reve
                    self.Vx2D[j][i, :] = self.gs.Vx[j]
                    self.Vy2D[j][i, :] = self.gs.Vy[j]
                    self.Ix2D[i, :] = self.gs.Ix
                    self.Iy2D[i, :] = self.gs.Iy
            self.plot()


    def get_field(self):
        '''
        Get current field from PPMS. (Other version of this class uses Bluefors magnet)
        '''
        return self.ppms.field/10000


    def plot(self):
        Measurement.plot(self) # don't want to do RvsVg plotting

        for i in range(len(self.ax.keys())): # rows == different channels
            plot_mpl.update2D(self.im[i][0], np.abs(self.R2D[i]), equal_aspect=False)
            plot_mpl.update2D(self.im[i][1], np.log(np.abs(self.R2D[i])), equal_aspect=False)

        self.fig.tight_layout()
        self.fig.canvas.draw()


    def plot_linecut(self, idx=0, num_squares=1, Rxx_channel=0, Rxy_channel=1, QH_type='MLG'):
        '''
        Plot a gatesweep at constant field.
        idx: index of the gatesweep you wish to plot
        num_squares: aspect ratio used to convert Rxx to resistivity
        Rxx_channel: Rxx channel number
        Rxy_channel: Rxy channel number
        QH_type: 'MLG' or 'BLG' for monolayer/bilayer graphene. None for no plot

        Returns:
        fig - the figure
        ax - the axes
        '''
        fig, ax = plt.subplots()
        ax2 = ax.twinx()

        # Plot the resistance channels
        ax.plot(self.Vg, self.R2D[Rxx_channel][idx,:]/1000/num_squares)
        # ax.set_ylim(-.01, 3.5)
        ax.set_xlim(self.Vg.min(), self.Vg.max())
        Gxy = 1/self.R2D[Rxy_channel][idx,:]/G0
        ax2.plot(self.Vg, Gxy, 'C1')

        if QH_type == 'MLG':
            plateaus = (np.array(range(9))-4+1/2)*4
        elif QH_type == 'BLG':
            plateaus = (np.array(range(9))-4)*4
        elif QH_type == None:
            plateaus = []
        else:
            plateaus = (np.array(range(9))-4)
        for i in plateaus:
            ax2.axhline(i, color='k', ls='--', alpha=0.5)
        ylim = np.ceil(max(abs(Gxy[0]), abs(Gxy[-1]))) # choose the larger of the two endpoints
        ax2.set_ylim(-ylim,ylim)

        ax.set_xlabel('Gate voltage (V)',fontsize=16)
        ax.set_ylabel(r'$\rho_{xx}$ (k$\Omega$/☐)',fontsize=16)
        ax2.set_ylabel(r'$\sigma_{xy}$ ($e^2/h$)',fontsize=16, color='C1')

        ax.text(.1, 0.9, '%g T' %self.B[idx], fontsize=20, transform=ax.transAxes)
        plt.tight_layout()
        fig.canvas.draw()
        return fig, (ax, ax2)


    def plot_mobility(self, l=0, u=-1, Rxx_channel=0, Rxy_channel=1):
        '''
        Makes a plot of the Hall coefficient and carrier mobility vs gate voltage.
        The voltage channel measuring Rxy is by default 1, and Rxx is 0.
        Right now we assume geometrical factor of 1, so Rxx = rho_xx
        mu = R_H/<R_xx>, average value of R_xx
        R_H = Rxy/B

        l: lower index to do the fit
        u: upper index to do the fit
        Rxx_channel: channel number for Rxx
        Rxy_channel: channel number for Rxy
        '''
        from scipy.stats import linregress as lr
        slopes = np.array([])
        mobility = np.array([])
        Rxx = self.R2D[Rxx_channel]
        Rxy = self.R2D[Rxy_channel]
        for i in range(Rxy.shape[1]):
            slope, intercept, _, _, _ = lr(self.B[l:u], Rxy[l:u,i])
            slopes = np.append(slopes, slope)
            mobility = np.append(mobility, slope/Rxx[l:u,i].mean())
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10,4))
        ax1.plot(self.Vg, abs(slopes))
        ax2.plot(self.Vg, abs(mobility)*100**2)
        ax1.set_xlabel('Vg (V)',fontsize=20)
        ax2.set_xlabel('Vg (V)',fontsize=20)

        ax1.set_ylabel(r'Hall Coefficient ($\rm \Omega/T$)', fontsize=16)
        ax2.set_ylabel(r'Carrier mobility ($\rm{cm^2/V\cdot s}$)', fontsize=16)

        fig.tight_layout()

        self.Hall_coefficient = abs(slopes)
        self.mobility = abs(mobility)*100**2

        return fig, ax1, ax2


    def setup_plots(self):
        self.fig, ax = plt.subplots(nrows = self.num_lockins, ncols=2, figsize=(10,10))
        self.fig.subplots_adjust(wspace=.5, hspace=.5) # breathing room
        if self.num_lockins == 1 :
            self.ax = {0: {j: ax[j] for j in range(ax.shape[0])}}
            self.im = {0: {j: None for j in range(ax.shape[0])}}
        else:
            self.ax = {i: {j: ax[i][j] for j in range(ax.shape[1])} for i in range(ax.shape[0])}
            # first index is lockin #, second index is plot # (one for regular, one for log)
            self.im = {i: {j: None for j in range(ax.shape[1])} for i in range(ax.shape[0])}

        for i in range(self.num_lockins): # different channels
            ## Here we are plotting both |R| and log|R| for each channel
            ax = self.ax[i]
            self.im[i][0] = plot_mpl.plot2D(ax[0],
                                                self.Vg,
                                                self.B,
                                                np.abs(self.R2D[i]),
                                                interpolation = 'none',
                                                cmap='viridis',
                                                xlabel='Vg (V)',
                                                ylabel= 'B (T)',
                                                clabel='|R%s| (Ohm)' %i,
                                                equal_aspect=False)
            self.im[i][1] = plot_mpl.plot2D(ax[1],
                                                self.Vg,
                                                self.B,
                                                np.log(np.abs(self.R2D[i])),
                                                interpolation = 'none',
                                                cmap='viridis',
                                                xlabel='Vg (V)',
                                                ylabel= 'B (T)',
                                                clabel='log(|R%s (Ohm)|)' %i,
                                                equal_aspect=False)

            for j in range(2):
                ax[j].set_xlabel('Vg (V)', fontsize=20)
                ax[j].set_ylabel('B (T)', fontsize=20)
                plot_mpl.aspect(ax[j], 1)
                ax[j].set_title(self.filename)


class RvsVg_B_BlueFors(RvsVg_B):
    field_sweep_class = RvsB_BlueFors
    instrument_list = list(set(RvsB_BlueFors.instrument_list)
                                                | set(RvsVg.instrument_list))

    def get_field(self):
        '''
        Get current field from BlueFors magnet instead of PPMS.
        '''
        return self.magnet.B


class RvsVg_B_Phil(RvsVg_B):
    field_sweep_class = RvsB_Phil
    instrument_list = list(set(RvsB_Phil.instrument_list)
                                                | set(RvsVg.instrument_list))

    def get_field(self):
        '''
        Get current field from BlueFors magnet instead of PPMS.
        '''
        return self.magnet.Bmagnet
