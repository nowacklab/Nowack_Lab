import time, numpy as np, matplotlib.pyplot as plt
from .measurement import Measurement
from ..Utilities.plotting import plot_mpl
from matplotlib import cm

from ..Utilities.constants import e, h

class RvsSomething(Measurement):
    '''
    Monitor R = lockin_V.X/lockin_I.Y from two different lockins.
    Can supply additional lockin_V2, lockin_V3, etc to montior more voltages
    (plotted as resistance)
    This is a superclass for measuring resistance vs different things
    (e.g. gate voltage, temperature, field...)
    By default, this class measures vs. time (useful for timing subclasses!)

    Make sure to change the name of the "something" you're measuring vs!
    '''
    instrument_list = ['lockin_V1', 'lockin_I']
    something='time'
    something_units = 's'
    legendtitle=None

    def __init__(self, instruments = {}):
        super().__init__(instruments=instruments)

        # Set up dictionaries for each voltage channel.
        # Empty arrays for each lockin
        self.Vx = {i: np.array([]) for i in range(self.num_lockins)}
        self.Vy = {i: np.array([]) for i in range(self.num_lockins)}
        self.Ix = np.array([])
        self.Iy = np.array([])
        self.B = np.array([]) # if we can record field, let's do it.
        self.T = np.array([]) # if we can record temperature

        self.R = {i: np.array([]) for i in range(self.num_lockins)}
        setattr(self, self.something, np.array([]))

        if instruments != {}:
            self.setup_lockins()

    def _load_instruments(self, instruments={}):
        '''
        Loads instruments from a dictionary.
        Specify instruments needed using self.instrument_list.
        This is unique for this class because you can supply up to two
        additional lockins to monitor inputs from.
        '''
        super()._load_instruments(instruments)
        for name, handle in instruments.items():
            if name[:-1] == 'lockin_V': # e.g. lockin_V2, cut off the "2"
                setattr(self, name, handle)

    @property
    def num_lockins(self):
        num_lockins=0
        for name, handle in self.__dict__.items():
            if name[:-1] == 'lockin_V': # e.g. lockin_V2, cut off the "2"
                num_lockins += 1
        if num_lockins == 0:
            try:
                num_lockins = len(self.R) # if no instruments loaded
            except:
                pass # if you haven't yet given data.
        self._num_lockins = num_lockins
        return self._num_lockins

    def do(self, duration=None, delay=1, num_avg = 1, delay_avg = 0, plot=True, auto_gain=False):
        '''
        Duration and delay both in seconds.
        Use do_measurement() for each resistance measurement.
        '''
        time_start = time.time()
        if duration is None:
            duration = 1000000000000
        while True:
            self.time = np.append(self.time, time.time()-time_start)
            self.do_measurement(delay, num_avg, delay_avg, plot, auto_gain=auto_gain)
            if duration is not None:
                if self.time[-1] >= duration:
                    break


    def do_measurement(self, delay = 0, num_avg = 1, delay_avg = 0,
                                plot=True, auto_gain=True):
        '''
        Take a resistance measurement. Usually this will happen in a loop.
        Optional argument to set a delay before the measurement happens.
        plot argument determines whether data is plotted or not
        num_avg is the number of data points to be averaged
        delay_avg is the time delay (seconds) between averages
        auto_gain: automatically adjust lockin gain for small or OL signals

        Doesn't make a whole lot of sense to average for a measurement vs time,
        but the averaging could be useful for a subclass.
        '''

        if delay > 0:
            time.sleep(delay)


        self.Ix = np.append(self.Ix, self.lockin_I.X)
        self.Iy = np.append(self.Iy, self.lockin_I.Y)

        for j in range(self.num_lockins):
            if auto_gain:
                getattr(self, 'lockin_V%i' %(j+1)).fix_sensitivity() # make sure we aren't overloading or underloading.
                self.lockin_I.fix_sensitivity()

            ## Take as many measurements as requested and average them
            vx = 0
            vy = 0
            r = 0
            for i in range(num_avg):
                vx += getattr(self, 'lockin_V%i' %(j+1)).X
                vy += getattr(self, 'lockin_V%i' %(j+1)).Y

                r += vx/self.Ix[-1]
                if i != num_avg-1: # no reason to sleep the last time!
                    time.sleep(delay_avg)
            vx /= num_avg
            vy /= num_avg
            r /= num_avg

            self.Vx[j] = np.append(self.Vx[j], vx)
            self.Vy[j] = np.append(self.Vy[j], vy)
            self.R[j] = np.append(self.R[j], r)

        # Get temperature and field (if available)
        if hasattr(self, 'ppms'):
            self.B = np.append(self.B, self.ppms.field/10000) # Oe to T
        elif hasattr(self, 'magnet'):
            if self.magnet.p_switch:  # in driven mode
                B = self.magnet.Bsupply
            else:  # in persistent mode
                B = self.magnet.Bmagnet
            self.B = np.append(self.B, B)

        if hasattr(self, 'montana'):
            self.T = np.append(self.T, self.montana.temperature['platform'])
        elif hasattr(self, 'ppms'):
            self.T = np.append(self.T, self.ppms.temperature)
        elif hasattr(self, 'lakeshore'):
            self.T = np.append(self.T, self.lakeshore.T[6])

        if plot:
            self.plot()


    def plot(self):
        super().plot()

        for i, line in self.lines.items():
            line.set_xdata(getattr(self, self.something))
            line.set_ydata(self.R[i])

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()


    def run(self, plot=True, **kwargs):
        '''
        Run the measurement. Sets up plot label then uses Measurement.run
        '''
        self.setup_label()
        super().run(plot=plot, **kwargs)


    def setup_label(self):
        '''
        Add info about PPMS or Keithley status, if relevant.
        Fixed variables (e.g. temperature, field for a gatesweep) will show up
        in the plot legend as the legend title.
        '''
        self.legendtitle = None

        def add_text_to_legend(text):
            if self.legendtitle is None:
                self.legendtitle = text
            else:
                self.legendtitle += '\n'+text

        if hasattr(self, 'ppms'):
            if self.ppms is not None:
                if self.something != 'T': # if we're measuring vs many temperatures
                    add_text_to_legend('T = %.2f K' %self.ppms.temperature)
                if self.something != 'B':
                    add_text_to_legend('B = %.2f T' %(self.ppms.field/10000))

        if hasattr(self, 'magnet'):
            if self.magnet is not None:
                if self.something != 'B':
                    add_text_to_legend('B = %.2f T' %self.magnet.Bmagnet)

        if hasattr(self, 'keithley'):
            if self.keithley is not None:
                if self.something != 'Vg':
                    add_text_to_legend('Vg = %.1f V' %self.keithley.V)

    def setup_lockins(self):
        '''
        Set up lockins manually instead.
        '''
        pass
#         self.lockin_V1.input_mode = 'A-B'
#         self.lockin_I.input_mode = 'I (10^8)'
#         self.lockin_V1.reference = 'internal'
# #         self.lockin_V.frequency = 53.01
#         self.lockin_I.reference = 'external'


    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('%s (%s)' %(self.something, self.something_units), fontsize=20)
        self.ax.set_ylabel('R (Ohm)', fontsize=20)

        ## plot all the resistances
        self.lines = {}
        for j in range(self.num_lockins):
            line =  self.ax.plot(getattr(self, self.something), self.R[j])
            self.lines[j] = line[0]

        l = self.ax.legend(['R%i' %(i+1) for i in range(self.num_lockins)], loc='best', title=self.legendtitle)
        self.ax.set_title(self.filename)
        self.fig.tight_layout()


class RvsTime(RvsSomething):
    '''
    Alias for RvsSomething
    '''
    pass

class RvsT(RvsSomething):
    instrument_list = ['ppms', 'lockin_V1', 'lockin_I']
    something='T'
    something_units = 'K'

    def __init__(self, instruments = {}, Tstart = 300, Tend = 10, delay=1, sweep_rate=10):
        '''
        Sweep rate and temperature in K. Delay is in seconds. Rate is K/min
        '''
        super().__init__(instruments=instruments)

        self.Tstart = Tstart
        self.Tend = Tend
        self.delay = delay
        self.sweep_rate = sweep_rate

    def do(self, plot=True):
        ## Set initial temperature if not already there
        if abs(self.ppms.temperature - self.Tstart) > 1: # different by more than 1 K
            self.ppms.temperature_rate = 20 # sweep as fast as possible
            self.ppms.temperature = self.Tstart
            time.sleep(5) # let the temperature start ramping to Tstart
            print('Waiting for temperature to sweep to Tstart...')
            while self.ppms.temperature_status not in ('Stable'): # wait until stabilized
                time.sleep(5)

        if abs(self.Tstart-self.Tend) < 1:
            return # sweeping between the same two temperatures, no point in doing the measurement

        print('Starting temperature sweep...')

        ## Set sweep to final temperature
        self.ppms.temperature_rate = self.sweep_rate
        self.ppms.temperature_approach = 'FastSettle'
        self.ppms.temperature = self.Tend

        time.sleep(5) # wait for ppms to process command
        ## Measure while sweeping
        while self.ppms.temperature_status not in ('Near', 'Stable'):
            self.T = np.append(self.T, self.ppms.temperature)
            self.do_measurement(delay=self.delay, plot=plot)

class RvsT_RT_to_4K(Measurement):
    def __init__(self, instruments):
        self.instruments = instruments

    def do(self):
        r300_10 = RvsT(self.instruments, Tstart=305, Tend=10, delay=1, sweep_rate=20)
        r300_10.run()

        print('Waiting a half hour.')
        time.sleep(60*30)

        r10_4 = RvsT(self.instruments, Tstart=10, Tend=4, delay=1, sweep_rate=.2)
        r10_4.run()

class RvsT_RT_to_2K(Measurement):
    def __init__(self, instruments):
        self.instruments = instruments

    def do(self):
        r300_10 = RvsT(self.instruments, Tstart=300, Tend=10, delay=1, sweep_rate=10)
        r300_10.run()

        print('Waiting a half hour.')
        time.sleep(60*30)

        r10_4 = RvsT(self.instruments, Tstart=10, Tend=4, delay=1, sweep_rate=2)
        r10_4.run()

        print('Waiting 10 minutes.')
        time.sleep(60*10)

        r4_2 = RvsT(self.instruments, Tstart=4, Tend=2, delay=1, sweep_rate=1)
        r4_2.run()

class RvsT_Bluefors(RvsSomething):
    instrument_list = ['lakeshore', 'lockin_V1', 'lockin_I']
    something = 'T'
    something_units = 'K'

    def __init__(self, instruments = {}, channel=6, Tend = 10, delay=1):
        '''
        channel: lakeshore channel number to monitor
        Tend: target temperature (when to stop taking data)
        delay: time between measurements (seconds)
        '''
        super().__init__(instruments=instruments)

        self.channel = getattr(getattr(self, 'lakeshore'), 'chan%i' %channel)
        self.Tend = Tend
        self.delay = delay

    def do(self, plot=True):
        while self.channel.T > self.Tend:
            self.T = np.append(self.T, self.channel.T)
            self.do_measurement(delay=self.delay, plot=plot)


class RvsT_Montana(RvsSomething):
    instrument_list = ['montana', 'lockin_V1', 'lockin_I']
    something = 'T'
    something_units = 'K'

    def __init__(self, instruments = {}, Tend = 5, delay=1):
        '''
        Tend: target temperature (when to stop taking data)
        delay: time between measurements (seconds)
        '''
        super().__init__(instruments=instruments)

        self.Tend = Tend
        self.delay = delay

    def do(self, plot=True):
        while self.montana.temperature['platform'] > self.Tend:
            self.T = np.append(self.T, self.montana.temperature['platform'])
            self.do_measurement(delay=self.delay, plot=plot)

class RvsVg(RvsSomething):
    '''
    Monitor R = lockin_V.X/lockin_I.Y from two different lockins.
    Can supply additional lockin_V2, lockin_V3, etc to montior more voltages
    (plotted as resistance)
    '''
    instrument_list = ['keithley', 'lockin_V1', 'lockin_I']
    something = 'Vg'
    something_units = 'V'
    Igwarning = None

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1, delay=1, fine_range=None):
        '''
        Vstart: starting voltage (V)
        Vend: ending voltage (V)
        Vstep: voltage step size (V)
        delay: time delay between measurements (sec)
        fine_range: [Vmin, Vmax], a list of two voltages that define a range
        in which we will take N times as many data points. N=5.
        Note that Vmin is closer to Vstart and Vmax is closer to Vend,
        regardless of sweep direction.
        '''
        super().__init__(instruments=instruments)

        self.Vstart = Vstart
        self.Vend = Vend
        self.Vstep = Vstep
        self.delay = delay

        if fine_range is None:
            self.Vg_values = np.linspace(Vstart, Vend, round(abs(Vend-Vstart)/Vstep)+1)
        else:  # Use more points if a fine range specified
            Vmin = fine_range[0]
            Vmax = fine_range[1]
            numpts_sm = round(abs(Vmin-Vstart)/Vstep)+1  # sm = "start min"
            numpts_mm = round(abs(Vmin-Vmax)/Vstep*10)+1  # mm = "min max"
            numpts_me = round(abs(Vmax-Vend)/Vstep)+1  # me = "max end"
            self.Vg_values = np.concatenate((
                    np.linspace(Vstart, Vmin, numpts_sm, endpoint=False),
                    np.linspace(Vmin, Vmax, numpts_mm, endpoint=False),
                    np.linspace(Vmax, Vend, numpts_me)
                )
            )

        self.Ig = np.array([])


    def do(self, num_avg = 1, delay_avg = 0, zero=False, plot=True, auto_gain=False):
        # Sweep to Vstart
        self.keithley.sweep_V(self.keithley.V, self.Vstart)
        self.keithley.Vout_range = abs(self.Vg_values).max()
        time.sleep(self.delay*3)


        # Do the measurement sweep
        for i, Vg in enumerate(self.Vg_values):
            self.Vg = np.append(self.Vg, Vg)
            self.keithley.Vout = Vg
            self.Ig = np.append(self.Ig, self.keithley.I)

            self.do_measurement(self.delay, num_avg, delay_avg, plot=plot, auto_gain=auto_gain)

        # Sweep back to zero
        if zero:
            self.keithley.zero_V()


    def plot(self):
        '''
        Plots using superclass function and adds warning for Ig > 1 nA
        '''
        super().plot()
        if self.Igwarning is None:  # if no warning
            if len(self.Ig)>0:  # if have data
                if abs(self.Ig).max() >= 1e-9:  # if should be warning
                    self.Igwarning = self.ax.text(.02,.95,
                                        r'$|I_g| \geq 1$ nA!',
                                        transform=self.ax.transAxes,
                                        color = 'C3'
                                    )  # warning


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

        add_text_to_legend('Vstep = %.3f V' %self.Vstep)
        add_text_to_legend('delay = %.2f s' %self.delay)
        if self.Vstart < self.Vend:
            add_text_to_legend(r'sweep $\longrightarrow$')
        else:
            add_text_to_legend(r'sweep $\longleftarrow$')

    def setup_plots(self):
        super().setup_plots()

class RvsVg_Vtg(RvsVg):
    instrument_list = RvsVg.instrument_list + ['keithley_tg']

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1,
                delay=1, Vtgstart = -5, Vtgend = 5, Vtgstep=.1):
        '''
        Does gatesweeps at a series of topgate voltages.

        Vstart: start of gatesweep
        Vend: end of gatesweep
        Vstep: gatesweep voltage step size
        delay: gatesweep delay time
        Vtgstart: starting topgate voltage (V)
        Vtgend: end topgate voltage (V)
        Vtgstep: topgate voltage step between gatesweeps (V)
        '''
        raise Exception('Not tested')
        super().__init__(instruments=instruments, Vstart=Vstart, Vend=Vend, Vstep=Vstep, delay=delay)
        self.__dict__.update(locals()) # cute way to set attributes from arguments
        del self.self # but includes self, get rid of this!

        self.Vtg = np.linspace(Vtgstart, Vtgend, round(abs(Vtgstart-Vtgend)/Vtgstep)+1)
        self.gs = RvsVg(self.instruments, self.Vstart, self.Vend, self.Vstep, self.delay)

        self.Vg = self.gs.Vg_values

        self.R2D = {i: np.full((len(self.Vtg), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Vx2D = {i: np.full((len(self.Vtg), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Vy2D = {i: np.full((len(self.Vtg), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Ix2D = np.full((len(self.Vtg), len(self.Vg)), np.nan)
        self.Iy2D = np.full((len(self.Vtg), len(self.Vg)), np.nan)

        # remember: shape of matrix given in y,x. So Vtg is on the y axis and Vg on the x axis.

    def do(self, delay=0, auto_gain=False):
        '''
        delay: wait time after sweeping field
        '''
        for i, Vtg in enumerate(self.Vtg):
            # sweep topgate
            raise Exception('fix sweep!')
            self.keithley_tg.sweep_V(keithley_tg.V, Vtg)

            # reset arrays for gatesweep
            self.gs = RvsVg(self.instruments, self.Vstart, self.Vend, self.Vstep, self.delay)
            self.gs.run(auto_gain=auto_gain)

            for j in range(self.num_lockins):
                if self.Vstart > self.Vend:
                    #[::-1] reverses sweeps if we did them backwards
                    self.R2D[j][i, :] = self.gs.R[j][::-1]
                    self.Vx2D[j][i, :] = self.gs.Vx[j][::-1]
                    self.Vy2D[j][i, :] = self.gs.Vy[j][::-1]
                    self.Ix2D[i, :] = self.gs.Ix[::-1]
                    self.Iy2D[i, :] = self.gs.Iy[::-1]
                else:
                    # first index is voltage channel, second is Vtg, third is Vg
                    self.R2D[j][i, :] = self.gs.R[j]
                    self.Vx2D[j][i, :] = self.gs.Vx[j]
                    self.Vy2D[j][i, :] = self.gs.Vy[j]
                    self.Ix2D[i, :] = self.gs.Ix
                    self.Iy2D[i, :] = self.gs.Iy
            self.plot()


    def plot(self):
        Measurement.plot(self)  # don't want to do RvsVg plotting

        for i in range(len(self.ax.keys())):  # rows == different channels
            plot_mpl.update2D(self.im[i][0], np.abs(self.R2D[i]), equal_aspect=False)
            plot_mpl.update2D(self.im[i][1], np.log(np.abs(self.R2D[i])), equal_aspect=False)

        self.fig.tight_layout()
        self.fig.canvas.draw()


    def plot_linecut(self, idx=0):
        pass


    def setup_plots(self):
        self.fig, ax = plt.subplots(nrows = self.num_lockins, ncols=2, figsize=(10,10))
        self.fig.subplots_adjust(wspace=.5, hspace=.5)  # breathing room
        if self.num_lockins == 1 :
            self.ax = {0: {j: ax[j] for j in range(ax.shape[0])}}
            self.im = {0: {j: None for j in range(ax.shape[0])}}
        else:
            self.ax = {i: {j: ax[i][j] for j in range(ax.shape[1])} for i in range(ax.shape[0])}
            # first index is lockin #, second index is plot # (one for regular, one for log)
            self.im = {i: {j: None for j in range(ax.shape[1])} for i in range(ax.shape[0])}

        for i in range(self.num_lockins):  # different channels
            # Here we are plotting both |R| and log|R| for each channel
            ax = self.ax[i]
            self.im[i][0] = plot_mpl.plot2D(ax[0],
                                                self.Vg,
                                                self.Vtg,
                                                np.abs(self.R2D[i]),
                                                interpolation = 'none',
                                                cmap='viridis',
                                                xlabel='Vg (V)',
                                                ylabel= 'Vtg (V)',
                                                clabel='|R%s| (Ohm)' %i,
                                                equal_aspect=False)
            self.im[i][1] = plot_mpl.plot2D(ax[1],
                                                self.Vg,
                                                self.Vtg,
                                                np.log(np.abs(self.R2D[i])),
                                                interpolation = 'none',
                                                cmap='viridis',
                                                xlabel='Vg (V)',
                                                ylabel= 'Vtg (V)',
                                                clabel='log(|R%s (Ohm)|)' %i,
                                                equal_aspect=False)

            for j in range(2):
                ax[j].set_xlabel('Vg (V)', fontsize=20)
                ax[j].set_ylabel('Vtg (V)', fontsize=20)
                plot_mpl.aspect(ax[j], 1)
                ax[j].set_title(self.filename)

class RvsVg_T(RvsVg):
    instrument_list = list(set(RvsT.instrument_list) | set(RvsVg.instrument_list))

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1,
                delay=1, Tstart = 5, Tend = 300, Tstep=5, Tdelay=1,
                sweep_rate=5, wait=5, Vg_sweep=None):
        '''
        Does gatesweeps at a series of temperatures.
        Stores the full gatesweeps at each field, as well as a RvsT curve done
        at a particular gate voltage between gatesweeps.

        Vstart: start of gatesweep
        Vend: end of gatesweep
        Vstep: gatesweep voltage step size
        delay: gatesweep delay time
        Tstart: starting temperature (Kelvin)
        Tend: end temperature (Kelvin)
        Tstep: temperature step between gatesweeps (Kelvin)
        Tdelay: delay between resistance measurements during temperature sweep (seconds)
        sweep_rate: temperature sweep rate (K/min)
        wait: wait time once reach target temperature (min)
        Vg_sweep: gate voltage at which to do the temperature sweep (V). Leave at None if you don't care.
        '''
        super().__init__(instruments=instruments, Vstart=Vstart, Vend=Vend, Vstep=Vstep, delay=delay)
        self.__dict__.update(locals()) # cute way to set attributes from arguments
        del self.self # but includes self, get rid of this!

        self.T = np.linspace(Tstart, Tend, round(abs(Tstart-Tend)/Tstep)+1)
        self.gs = RvsVg(self.instruments, self.Vstart, self.Vend, self.Vstep, self.delay)

        self.Vg = self.gs.Vg_values

        self.R2D = {i: np.full((len(self.T), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Vx2D = {i: np.full((len(self.T), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Vy2D = {i: np.full((len(self.T), len(self.Vg)), np.nan) for i in range(self.num_lockins)}
        self.Ix2D = np.full((len(self.T), len(self.Vg)), np.nan)
        self.Iy2D = np.full((len(self.T), len(self.Vg)), np.nan)

        ## remember: shape of matrix given in y,x. So T is on the y axis and Vg on the x axis.

        # store full field sweep data
        self.Tfull = np.array([])
        for j in range(self.num_lockins):
            setattr(self, 'R%ifull' %j, np.array([]))


    def do(self, auto_gain=False):
        for i, T in enumerate(self.T):
            if self.Vg_sweep is not None:
                self.keithley.sweep_V(self.keithley.V, self.Vg_sweep) # set desired gate voltage for the temp sweep
            else: # otherwise we will go as quickly as possible and reverse every other gatesweep
                self.Vstart, self.Vend = self.Vend, self.Vstart

            ## reset temp sweep
            self.ts = RvsT(self.instruments, self.ppms.temperature, T, 1, self.sweep_rate)
            self.ts.run(plot=False)

            # Wait for cooling/stabilization
            print('Waiting %i minutes for thermalization.' %self.wait)
            time.sleep(self.wait*60)

            # store full temp sweep data
            self.Tfull = np.append(self.Tfull, self.ts.T)
            for j in range(self.num_lockins):
                r = getattr(self, 'R%ifull' %j)
                setattr(self, 'R%ifull' %j, np.append(r, self.ts.R[j]))

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
                    self.R2D[j][i, :] = self.gs.R[j] # first index is voltage channel, second is T, third is Vg. Reve
                    self.Vx2D[j][i, :] = self.gs.Vx[j]
                    self.Vy2D[j][i, :] = self.gs.Vy[j]
                    self.Ix2D[i, :] = self.gs.Ix
                    self.Iy2D[i, :] = self.gs.Iy
            self.plot()

    def plot(self):
        Measurement.plot(self) # don't want to do RvsVg plotting

        for i in range(len(self.ax.keys())): # rows == different channels
            plot_mpl.update2D(self.im[i][0], np.abs(self.R2D[i]), equal_aspect=False)
            plot_mpl.update2D(self.im[i][1], np.log(np.abs(self.R2D[i])), equal_aspect=False)

        self.fig.tight_layout()
        self.fig.canvas.draw()


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
                                                self.T,
                                                self.R2D[i],
                                                interpolation = 'none',
                                                cmap='RdBu',
                                                xlabel='Vg (V)',
                                                ylabel= 'T (K)',
                                                clabel='R%s (Ohm)' %i,
                                                equal_aspect=False)
            self.im[i][1] = plot_mpl.plot2D(ax[1],
                                                self.Vg,
                                                self.T,
                                                np.log(np.abs(self.R2D[i])),
                                                interpolation = 'none',
                                                cmap='RdBu',
                                                xlabel='Vg (V)',
                                                ylabel= 'T (K)',
                                                clabel='log(|R%s (Ohm)|)' %i,
                                                equal_aspect=False)

            for j in range(2):
                ax[j].set_xlabel('Vg (V)', fontsize=20)
                ax[j].set_ylabel('T (K)', fontsize=20)
                plot_mpl.aspect(ax[j], 1)
                ax[j].set_title(self.filename)

def PPMS_cool(instruments):
    r300_10 = RvsT(instruments, Tstart=instruments['ppms'].temperature, Tend=10, delay=1, sweep_rate=20)
    r300_10.run()
    time.sleep(60*30)
    r10_4 = RvsT(instruments, Tstart=10, Tend=4, delay=1, sweep_rate=.2)
    r10_4.run()
