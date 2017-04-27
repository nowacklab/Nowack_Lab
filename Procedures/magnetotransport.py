import time, numpy as np, matplotlib.pyplot as plt
from ..Utilities.save import Measurement
from .transport import RvsSomething, RvsVg
from ..Utilities.plotting import plot_mpl

## Constants here
e = 1.60217662e-19 #coulombs
h = 6.626e-34 # m^2*kg/s

class RvsB(RvsSomething):
    instrument_list = ['ppms', 'lockin_V', 'lockin_I']
    something='B'
    something_units = 'T'

    def __init__(self, instruments = {}, Bstart = 0, Bend = 14, delay=1, sweep_rate=.01):
        '''
        Sweep rate and field in T. PPMS uses Oe. Delay is in seconds. Rate is T/second
        '''
        super().__init__(instruments)

        self.Bstart = Bstart
        self.Bend = Bend
        self.delay = delay
        self.sweep_rate = sweep_rate

    def do(self, plot=True):
        self.do_before(plot)

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
        self.ppms.field_rate = self.sweep_rate*10000# T to Oe
        self.ppms.field_mode = 'Persistent'
        self.ppms.field_approach = 'Linear'
        self.ppms.field = self.Bend*10000 # T to Oe

        while self.ppms.field_status not in ('Iterating', 'Charging'):
            time.sleep(2) # wait until the field is changing

        ## Measure while sweeping
        while self.ppms.field_status in ('Iterating', 'Charging'):
            self.B = np.append(self.B, self.ppms.field/10000) # Oe to T
            self.do_measurement(delay=self.delay, plot=plot)

        self.do_after()

    def plot_quantized_conductance(self, nu=1, Rxy_channel=0, Rxx_channel=1):
        '''
        Generate a plot with Gxy in units of nu*e^2/h. By default, the zeroth lockin (the one
        used to source current) measures Rxy.
        '''
        fig, ax = plt.subplots()
        ax2 = ax.twinx()
        ax.set_xlabel('B (T)', fontsize=20)
        ax.set_ylabel('Gxy (%ie^2/h)' %nu, fontsize=20)
        ax2.set_ylabel('Rxx (Ohm)', fontsize=20)
        G0 = e**2/h
        ax.plot(self.B, 1/self.R[str(Rxy_channel)]/G0/nu, 'g')
        ax2.plot(self.B, self.R[str(Rxx_channel)], 'b')
        ax.set_title(self.filename)
        ax.set_ylim(-40/nu,40/nu)

        return fig, ax, ax2

class RvsVg_B(RvsVg):
    instrument_list = list(set(RvsB.instrument_list) | set(RvsVg.instrument_list))

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1,
                delay=1, Bstart = 0, Bend = 14, Bstep=1, Bdelay=1,sweep_rate=.01, Vg_sweep=None):
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
        sweep_rate: field sweep rate (Tesla/s)
        Vg_sweep: gate voltage at which to do the field sweep (V). Leave at None if you don't care.
        '''
        super().__init__(instruments, Vstart, Vend, Vstep, delay)
        self.__dict__.update(locals()) # cute way to set attributes from arguments
        del self.self # but includes self, get rid of this!

        self.B = np.linspace(Bstart, Bend, round(abs(Bstart-Bend)/Bstep)+1)
        self.gs = RvsVg(self.instruments, self.Vstart, self.Vend, self.Vstep, self.delay)

        self.Vg = self.gs.Vg_values

        self.R2D = {str(i): np.full((len(self.B), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        ## remember: shape of matrix given in y,x. So B is on the y axis and Vg on the x axis.

        # store full field sweep data
        self.Bfull = np.array([])
        for j in range(self.num_lockins):
            setattr(self, 'R%ifull' %j, np.array([]))


    def do(self, ):
        self.do_before()

        for i, B in enumerate(self.B):
            if self.Vg_sweep is not None:
                self.keithley.sweep_V(self.keithley.V, self.Vg_sweep, .1, 1) # set desired gate voltage for the field sweep
            else: # otherwise we will go as quickly as possible and reverse every other gatesweep
                self.Vstart, self.Vend = self.Vend, self.Vstart

            ## reset field sweep
            self.fs = RvsB(self.instruments, self.ppms.field/10000, B, 1, self.sweep_rate)
            self.fs.do(plot=False)

            # store full field sweep data
            self.Bfull = np.append(self.Bfull, self.fs.B)
            for j in range(self.num_lockins):
                r = getattr(self, 'R%ifull' %j)
                r = np.append(r, self.fs.R[str(j)])

            ## reset arrays for gatesweep
            self.gs = RvsVg(self.instruments, self.Vstart, self.Vend, self.Vstep, self.delay)
            self.gs.do()

            for j in range(self.num_lockins):
                if self.Vstart > self.Vend:
                    self.R2D[str(j)][i, :] = self.gs.R[str(j)][::-1] # reverse if we did the sweep backwards
                else:
                    self.R2D[str(j)][i, :] = self.gs.R[str(j)] # first index is voltage channel, second is B, third is Vg. Reve
            self.plot()

        self.do_after()

    def plot(self):
        Measurement.plot(self) # don't want to do RvsVg plotting

        for i in range(len(self.ax.keys())): # rows == different channels
            plot_mpl.update2D(self.im[str(i)]['0'], np.abs(self.R2D[str(i)]), equal_aspect=False)
            plot_mpl.update2D(self.im[str(i)]['1'], np.log(np.abs(self.R2D[str(i)])), equal_aspect=False)

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def setup_plots(self):
        self.fig, ax = plt.subplots(nrows = self.num_lockins, ncols=2, figsize=(10,10))
        self.fig.subplots_adjust(wspace=.5, hspace=.5) # breathing room
        self.ax = {str(i): {str(j): ax[i][j] for j in range(ax.shape[1])} for i in range(ax.shape[0])}
        # first index is lockin #, second index is plot # (one for regular, one for log)
        self.im = {str(i): {str(j): None for j in range(ax.shape[1])} for i in range(ax.shape[0])}

        for i in range(ax.shape[0]): # rows == different channels
            ## Here we are plotting both |R| and log|R| for each channel
            i = str(i)
            ax = self.ax[i]
            self.im[i]['0'] = plot_mpl.plot2D(ax['0'],
                                                self.Vg,
                                                self.B,
                                                self.R2D[i].T,
                                                interpolation = 'none',
                                                cmap='cubehelix',
                                                xlabel='Vg (V)',
                                                ylabel= 'B (T)',
                                                clabel='R%s (Ohm)' %i,
                                                equal_aspect=False)
            self.im[i]['1'] = plot_mpl.plot2D(ax['1'],
                                                self.Vg,
                                                self.B,
                                                np.log(np.abs(self.R2D[i].T)),
                                                interpolation = 'none',
                                                cmap='cubehelix',
                                                xlabel='Vg (V)',
                                                ylabel= 'B (T)',
                                                clabel='log(|R%s (Ohm)|)' %i,
                                                equal_aspect=False)

            for j in range(2):
                j = str(j)
                ax[j].set_xlabel('Vg (V)', fontsize=20)
                ax[j].set_ylabel('B (T)', fontsize=20)
                plot_mpl.aspect(ax[j], 1)
                ax[j].set_title(self.filename)
