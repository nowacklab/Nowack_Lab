import time, numpy as np, matplotlib.pyplot as plt
from ..Utilities.save import Measurement
from .transport import RvsSomething, RvsVg
from ..Utilities.plotting import plot_mpl

class RvsB(RvsSomething):
    instrument_list = ['ppms', 'lockin_V', 'lockin_I']
    something='B'

    def __init__(self, instruments = {}, Bstart = 0, Bend = 14, delay=1, sweep_rate=.01):
        '''
        Sweep rate and field in T. PPMS uses Oe. Delay is in seconds. Rate is T/second
        '''
        super().__init__(instruments)

        self.Bstart = Bstart
        self.Bend = Bend
        self.delay = delay
        self.sweep_rate = sweep_rate

    def do(self):
        self.do_before()

        ## Set initial field if not already there
        if abs(self.ppms.field - self.Bstart*10000) > 0.1: # different by more than 0.1 Oersted = 10 uT.
            self.ppms.field = self.Bstart*10000 # T to Oe
            time.sleep(5) # let the field start ramping to Bstart
            while self.ppms.field_status in ('Iterating', 'Charging'): # wait until stabilized
                time.sleep(5)

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
            self.do_measurement(delay=self.delay)

        self.do_after()

class RvsVg_B(RvsVg):
    instrument_list = list(set(RvsB.instrument_list) | set(RvsVg.instrument_list))

    def __init__(self, instruments = {}, Vmin = -40, Vmax = 40, Vstep=.1,
                delay=1, Bstart = 0, Bend = 14, Bstep=1, Bdelay=1,sweep_rate=.01, Vg_sweep=0):
        '''
        Does gatesweeps at a series of magnetic fields.
        Stores the full gatesweeps at each field, as well as a RvsB curve done
        at a particular gate voltage between gatesweeps.

        Vmin: bottom of gatesweep
        Vmax: top of gatesweep
        Vstep: gatesweep voltage step size
        delay: gatesweep delay time
        Bstart: starting field (Tesla)
        Bend: end field (Tesla)
        Bstep: field step between gatesweeps (Tesla)
        Bdelay: delay between resistance measurements during fieldsweep
        sweep_rate: field sweep rate (Tesla/s)
        Vg_sweep: gate voltage at which to do the field sweep (V)
        '''
        super().__init__(instruments, Vmin, Vmax, Vstep, delay)
        self.__dict__.update(locals()) # cute way to set attributes from arguments
        del self.self # but includes self, get rid of this!

        self.B = np.linspace(Bstart, Bend, round(abs(Bstart-Bend)/Bstep)+1)

    def do(self):
        self.do_before()

        for i, B in enumerate(self.B):
            self.keithley.sweep_V(self.keithley.V, self.Vg_sweep, .1, 1) # set desired gate voltage for the field sweep

            fs = RvsB(self.instruments, self.ppms.field, B, 1, self.sweep_rate)
            fs.do()

            ## reset arrays for gatesweep
            gs = RvsVg(self.instruments, self.Vmin, self.Vmax, self.Vstep, self.delay)
            gs.do()

            for j in self.num_lockins:
                if i == 0:
                    self.R2D[j] = np.full((len(gs.R[j]), len(self.B)), np.nan)
                    self.R2D[j][:, i] = gs.R[j] # first index is voltage channel, second is Vg, third is B
                else:
                    self.R2D[j] = np.append(self.R2D[j], gs.R[j])

        self.do_after()

    def plot(self):
        super().plot()

        for i in self.ax.shape[0]: # rows == different channels
            plot_mpl.update2D(self.im[i,0], np.abs(self.R2D[i]))
            plot_mpl.update2D(self.im[i,1], np.log(np.abs(self.R2D[i])))

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots(nrows = self.num_lockins, ncols=2)
        self.ax.set_xlabel('Vg (V)', fontsize=20)
        self.ax.set_ylabel('B (T)', fontsize=20)
        self.im = np.empty(self.ax.shape)

        for i in self.ax.shape[0]: # rows == different channels
            self.im[i,0] = plot_mpl.plot2D(ax, gs.Vg, self.B, np.abs(self.R2D[i]), interpolation = 'none', cmap='cubehelix', xlabel='Vg (V)', ylabel= 'B (T)', clabel='R%i (Ohm)' %i)
            self.im[i,1] = plot_mpl.plot2D(ax, gs.Vg, self.B, np.log(np.abs(self.R2D[i])), interpolation = 'none', cmap='cubehelix', xlabel='Vg (V)', ylabel= 'B (T)', clabel='log(R%i (Ohm))' %i)

            plot_mpl.aspect(ax, 1)
            ax.set_xlabel('Vg (V)')
            ax.set_ylabel('B (T)')
            ax.set_title(self.filename)
