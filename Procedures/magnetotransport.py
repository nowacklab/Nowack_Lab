import time, numpy as np, matplotlib.pyplot as plt
from ..Utilities.save import Measurement
from .transport import RvsSomething, RvsVg
from ..Utilities.plotting import plot_mpl
import peakutils
from scipy.interpolate import interp1d
from scipy.stats import linregress

from ..Utilities.constants import e, h

class RvsB(RvsSomething):
    instrument_list = ['ppms', 'lockin_V', 'lockin_I']
    something='B'
    something_units = 'T'

    def __init__(self, instruments = {}, Bstart = 0, Bend = 1, delay=1, sweep_rate=.1):
        '''
        Sweep rate and field in T. Delay is in seconds. Rate is T/min
        '''
        super().__init__(instruments=instruments)

        self.Bstart = Bstart
        self.Bend = Bend
        self.delay = delay
        self.sweep_rate = sweep_rate

    def do(self, plot=True, auto_gain=False):
        ## Set initial field if not already there
        if abs(self.ppms.field - self.Bstart*10000) > 0.1: # different by more than 0.1 Oersted = 10 uT.
            self.ppms.field = self.Bstart*10000 # T to Oe
            time.sleep(5) # let the field start ramping to Bstart
            print('Waiting for field to sweep to Bstart...')
            while self.ppms.field_status in ('Iterating', 'Charging', 'WarmingSwitch', 'Unknown'): # wait until stabilized
                time.sleep(5)

        if abs(self.Bstart-self.Bend)*10000 < 0.1:
            return # sweeping between the same two fields, no point in doing the measurement

        print('Starting field sweep...')

        ## Set sweep to final field
        self.ppms.field_rate = self.sweep_rate/60*10000# T/min to Oe/s
        self.ppms.field_mode = 'Persistent'
        self.ppms.field_approach = 'Linear'
        self.ppms.field = self.Bend*10000 # T to Oe

        while self.ppms.field_status not in ('Iterating', 'Charging'):
            time.sleep(2) # wait until the field is changing

        ## Measure while sweeping
        while self.ppms.field_status in ('Iterating', 'Charging'):
            self.do_measurement(delay=self.delay, plot=plot, auto_gain=auto_gain)

    def calc_n_Hall(self, Bmax=2, Rxy_channel=1):
        '''
        Calculate the carrier density using the Hall coefficient at low field.
        R_H = B/ne
        '''
        where = np.where(self.B < Bmax)
        m, b, _, _, _ = linregress(self.B[where], self.R[Rxy_channel][where])

        fig, ax = plt.subplots()
        ax.plot(self.B[where], self.R[Rxy_channel][where], '.')
        ax.plot(self.B[where], m*self.B[where]+b, '-')
        ax.set_xlabel('B (T)', fontsize=20)
        ax.set_ylabel('R$_{xy}$ ($\Omega$)', fontsize=20)

        self.n = 1/(m*e)/100**2 # convert to cm^-2


    def calc_n_QHE(self, nu=2,Rxx_channel=0, thres=0.1, min_dist=100, Brange = [1,13]):
        '''
        Calculate the carrier density using the spacing between Landau levels.
        This will only work if there are clear peaks in Rxx.
        nu: total spin/valley degeneracy (spacing between LL's in
        conductance quanta)
        Rxx_channel: which lockin measured Rxx
        thres: float between [0., 1.]. Normalized threshold.
        Only peaks with amplitudes higher than the threshold will be detected.
        (see peakutils.indexes)
        min_dist: Minimum distance between each detected peak.
        The peak with the highest amplitude is preferred to satisfy this constraint. (see peakutils.indexes)
        Brange: [Bmin, Bmax] field range over which to look for peaks
        '''
        ## Calculate 1/B and generate equally spaced array in 1/B space.
        Bmin = Brange[0]
        Bmax = Brange[1]
        oneoverB = np.linspace(1/Bmax, 1/Bmin,5000)
        f = interp1d(1/self.B, self.R[Rxx_channel])
        R = f(oneoverB)

        ## Find peaks in Rxx
        peaks = peakutils.indexes(R, thres=thres, min_dist=min_dist)

        ## Plot it to check
        fig, (ax, ax2) = plt.subplots(2)
        ax.plot(oneoverB, R)
        ax.plot(oneoverB[peaks], R[peaks], '.')
        ax.set_xlabel(r'1/B (T$^{-1}$)', fontsize=20)
        ax.set_ylabel(r'R$_{xx}$ ($\Omega$)', fontsize=20)

        deltaoneoverB = np.mean(np.diff(oneoverB[peaks]))

        ax2.plot(np.diff(oneoverB[peaks]))
        ax2.plot([deltaoneoverB for i in range(len(peaks))], '-k')
        ax2.set_xlabel('Peak number', fontsize=20)
        ax2.set_ylabel('$\Delta(1/B)$ (T$^{-1}$)', fontsize=20)

        fig.tight_layout()

        ## Calculate carrier density from average peak spacing
        self.n = nu*e/h/deltaoneoverB/100**2 # conver to cm^-2


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
    instrument_list = ['magnet', 'lockin_V', 'lockin_I']

    def do(self, plot=True, auto_gain=False):
        ## Set initial field if not already there
        if abs(self.magnet.B - self.Bstart) > 100e-6: # different by more than 100 uT
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


class RvsVg_B(RvsVg):
    instrument_list = list(set(RvsB.instrument_list) | set(RvsVg.instrument_list))
    field_sweep_class = RvsB

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1,
                delay=1, Bstart = 0, Bend = 14, Bstep=1, Bdelay=1,sweep_rate=.1, Vg_sweep=None):
        '''
        Does gatesweeps at a series of magnetic fields.
        Stores the full gatesweeps at each field, as well as a RvsB curve done
        at a particular gate voltage between gatesweeps.

        Vstart: start of gatesweep
        Vend: end of gatesweep
        Vstep: gatesweep voltage step size
        delay: gatesweep delay time
        Bstart: starting field (Tesla)
        Bend: end field (Tesla)
        Bstep: field step between gatesweeps (Tesla)
        Bdelay: delay between resistance measurements during fieldsweep
        sweep_rate: field sweep rate (Tesla/min)
        Vg_sweep: gate voltage at which to do the field sweep (V). Leave at None if you don't care.
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
        self.Ix2D = np.full((len(self.B), len(self.Vg)), np.nan)

        ## remember: shape of matrix given in y,x. So B is on the y axis and Vg on the x axis.

        # store full field sweep data
        self.Bfull = np.array([])
        for j in range(self.num_lockins):
            setattr(self, 'R%ifull' %j, np.array([]))

    def calc_n(self, Rxy_channel=1, Vg_range=[-40, 40]):
        '''
        Calculate carrier density from the slopes of all cuts of Rxy vs B.
        Returns conversion factor between gate voltage and density. (in cm^-2/V)
        Vg_range: interval of Vgs over which to get carrier density conversion.
        '''
        from scipy.stats import linregress as lr
        slopes = np.array([])
        n = np.array([])
        Vgs = np.array([])
        Rxy = self.R2D[Rxy_channel]
        fig, ax =plt.subplots()
        for i in range(Rxy.shape[1]):
            slope, intercept, r, _, _ = lr(self.B, Rxy[:,i])

            ax.plot(self.B, Rxy[:,i],'.')
            if r**2 > .99:
                ax.plot(self.B, slope*self.B+intercept,'-')
                Vgs = np.append(Vgs, self.Vg[i])
                slopes = np.append(slopes, slope)
                n = np.append(n, 1/(slope*e))
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10,4))
        ax1.plot(Vgs, slopes,'.')
        ax2.plot(Vgs, n/100**2,'.')

        Vgmin = Vg_range[0]
        Vgmax = Vg_range[1]
        where = np.where(np.logical_and(Vgs >= Vgmin,Vgs <= Vgmax))
        slope, intercept, _, _, _ = lr(Vgs[where], n[where]/100**2) # find carrier density conversion
        ax2.plot(Vgs[where], Vgs[where]*slope+intercept, '-')
        ax1.set_xlabel('Vg (V)',fontsize=20)
        ax1.set_ylabel(r'Hall Coefficient ($\rm \Omega/T$)', fontsize=16)
        ax2.set_ylabel(r'Carrier density ($\rm{cm^{-2}}$)', fontsize=16)

        fig.tight_layout()

        self.Hall_coefficient = slopes
        self.n = n/100**2

        return abs(slope) # this will be a conversion in cm^-2/V from gate voltage to carrier density.

    def do(self, delay=0, auto_gain=False):
        '''
        delay: wait time after sweeping field
        '''
        for i, B in enumerate(self.B):
            if self.Vg_sweep is not None:
                self.keithley.sweep_V(self.keithley.V, self.Vg_sweep, .1, 1) # set desired gate voltage for the field sweep
            else: # otherwise we will go as quickly as possible and reverse every other gatesweep
                self.Vstart, self.Vend = self.Vend, self.Vstart

            ## reset field sweep
            self.fs = self.field_sweep_class(self.instruments,
                                        self.get_field(), B, 1, self.sweep_rate)
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

    def find_CNP(self, Rxx_channel=0):
        '''
        Finds the index of gate voltage corresponding to charge neutrality point.
        Uses the gate sweep at minimum field.
        '''
        return np.where(self.R2D[Rxx_channel][0]==self.R2D[Rxx_channel][0].max())[0][0] # find CNP

    def get_field(self):
        '''
        Get current field from PPMS. (Other version of this class uses Bluefors magnet)
        '''
        return self.ppms.field/10000

    def mask_CNP(self, numpts=5):
        '''
        Converts R2D into a masked array, with a mask around the charge
        neutrality point. This makes the rest of the data easier to view.

        numpts is the number of data points to either side of the CNP you want to mask.

        Currently works only for the log plot...?
        '''
        CNP = self.find_CNP()
        print(CNP, numpts)
        mask = np.full(self.R2D[0].shape, False)
        mask[:, (CNP-numpts):(CNP+numpts)] = True

        for i in range(len(self.ax.keys())): # loop through all voltage channels
            self.R2D[i] = np.ma.masked_array(self.R2D[i], mask)

        self.plot()


    def plot(self):
        Measurement.plot(self) # don't want to do RvsVg plotting

        for i in range(len(self.ax.keys())): # rows == different channels
            plot_mpl.update2D(self.im[i][0], np.abs(self.R2D[i]), equal_aspect=False)
            plot_mpl.update2D(self.im[i][1], np.log(np.abs(self.R2D[i])), equal_aspect=False)

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def plot_mobility(self, Rxy_channel=1, Rxx_channel=0):
        '''
        Makes a plot of the Hall coefficient and carrier mobility vs gate voltage.
        The voltage channel measuring Rxy is by default 1, and Rxx is 0.
        Right now we assume geometrical factor of 1, so Rxx = rho_xx
        mu = R_H/<R_xx>, average value of R_xx
        R_H = Rxy/B
        '''
        from scipy.stats import linregress as lr
        slopes = np.array([])
        mobility = np.array([])
        Rxx = self.R2D[Rxx_channel]
        Rxy = self.R2D[Rxy_channel]
        for i in range(Rxy.shape[1]):
            slope, intercept, _, _, _ = lr(self.B, Rxy[:,i])
            slopes = np.append(slopes, slope)
            mobility = np.append(mobility, slope/Rxx[:,i].mean())
        fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10,4))
        ax1.plot(self.Vg, abs(slopes))
        ax2.plot(self.Vg, abs(mobility)*100**2)
        ax1.set_xlabel('Vg (V)',fontsize=20)
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
                                                self.R2D[i],
                                                interpolation = 'none',
                                                cmap='cubehelix',
                                                xlabel='Vg (V)',
                                                ylabel= 'B (T)',
                                                clabel='R%s (Ohm)' %i,
                                                equal_aspect=False)
            self.im[i][1] = plot_mpl.plot2D(ax[1],
                                                self.Vg,
                                                self.B,
                                                np.log(np.abs(self.R2D[i])),
                                                interpolation = 'none',
                                                cmap='cubehelix',
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
