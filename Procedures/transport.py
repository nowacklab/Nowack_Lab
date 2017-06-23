import time, numpy as np, matplotlib.pyplot as plt
from ..Utilities.save import Measurement
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
    instrument_list = ['lockin_V', 'lockin_I']
    something='time'
    something_units = 's'
    legendtitle=None

    def __init__(self, instruments = {}):
        super().__init__(instruments=instruments)

        # Set up dictionaries for each voltage channel.
        self.Vx = {i: np.array([]) for i in range(self.num_lockins)}
        self.Vy = {i: np.array([]) for i in range(self.num_lockins)}
        self.Ix = np.array([])
        self.Iy = np.array([])
        self.B = np.array([]) # if we can record field, let's do it.
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
        if hasattr(self, 'ppms'):
            self.B = np.append(self.B, self.ppms.field/10000) # Oe to T
        elif hasattr(self, 'magnet'):
            self.B = np.append(self.B, self.magnet.B)
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
                    add_text_to_legend('B = %.2f T' %self.magnet.B)

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

class RvsTime(RvsSomething):
    '''
    Alias for RvsSomething
    '''
    pass

class RvsT(RvsSomething):
    instrument_list = ['ppms', 'lockin_V', 'lockin_I']
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
        ## Set initial field if not already there
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
        self.ppms.temperature = self.Tend # T to Oe

        time.sleep(5) # wait for ppms to process command
        ## Measure while sweeping
        while self.ppms.temperature_status not in ('Near', 'Stable'):
            self.T = np.append(self.T, self.ppms.temperature) # Oe to T
            self.do_measurement(delay=self.delay, plot=plot)


class RvsVg(RvsSomething):
    '''
    Monitor R = lockin_V.X/lockin_I.Y from two different lockins.
    Can supply additional lockin_V2, lockin_V3, etc to montior more voltages
    (plotted as resistance)
    '''
    instrument_list = ['keithley', 'lockin_V', 'lockin_I']
    something = 'Vg'
    something_units = 'V'
    Igwarning = None

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1, delay=1, fine_range=None):
        '''
        fine_range - [Vmin, Vmax], a list of two voltages that define a range
        in which we will take N times as many data points. N=5.
        Note that Vmin is closer to Vstart and Vmax is closer to Vend.
        '''
        super().__init__(instruments=instruments)

        self.Vstart = Vstart
        self.Vend = Vend
        self.Vstep = Vstep
        self.delay = delay

        if fine_range is None:
            self.Vg_values = np.linspace(Vstart, Vend, round(abs(Vend-Vstart)/Vstep)+1)
        else: # Use more points if a fine range specified
            Vmin = fine_range[0]
            Vmax = fine_range[1]
            numpts_sm = round(abs(Vmin-Vstart)/Vstep)+1 # sm = "start min"
            numpts_mm = round(abs(Vmin-Vmax)/Vstep*10)+1 # mm = "min max"
            numpts_me = round(abs(Vmax-Vend)/Vstep)+1 # me = "max end"
            self.Vg_values = np.concatenate((
                    np.linspace(Vstart, Vmin, numpts_sm, endpoint=False),
                    np.linspace(Vmin, Vmax, numpts_mm, endpoint=False),
                    np.linspace(Vmax, Vend, numpts_me)
                )
            )

        self.Ig = np.array([])
        self.T = np.array([])

        self.setup_keithley()

    def do(self, num_avg = 1, delay_avg = 0, zero=False, plot=True, auto_gain=False):
#         self.keithley.output = 'on' #NO! will cause a spike!

        ## Sweep to Vstart
        self.keithley.sweep_V(self.keithley.V, self.Vstart, .1, 1)
        time.sleep(self.delay*3)

        ## Do the measurement sweep
        for i, Vg in enumerate(self.Vg_values):
            self.Vg = np.append(self.Vg, Vg)
            self.keithley.Vout = Vg
            self.Ig = np.append(self.Ig, self.keithley.I)
            if hasattr(self, 'montana'):
                self.T = np.append(self.T, self.montana.temperature['platform'])
            elif hasattr(self, 'ppms'):
                self.T = np.append(self.T, self.ppms.temperature)

            self.do_measurement(self.delay, num_avg, delay_avg, plot=plot, auto_gain=auto_gain)

        ## Sweep back to zero at 1V/s
        if zero:
            self.keithley.zero_V(1)


    def calc_mobility(self, num_squares=1):
        '''
        Calculate the carrier mobility from the carrier density n and the device
         resistivity. Since we measured resistance, this function divides by the
         number of squares to calculate a 2D resistivity (sheet resistance).

        mu = sigma/(ne), sigma = 1/Rs, Rs = R/(number of squares)

        Units are cm^2/(V*s)
        '''
        if not hasattr(self, 'n'):
            raise Exception('need to calculate carrier density using calc_n')
        Rs = self.R[0]/num_squares
        sigma = 1/Rs
        self.mobility = abs(sigma/(self.n*e))

    def calc_n_conversion(self, c):
        '''
        Converts gate voltage to carrier density using a conversion, given in
        cm^-2/V. Centers CNP at 0.
        '''
        CNP = self.find_CNP()
        self.n = c*(self.Vg-self.Vg[CNP])

    def calc_n_geo(self, t_ox = 300, center_CNP=True):
        '''
        Converts gate voltage to an approximate carrier density using geometry.
        Carrier density is stored as the attribute n.
        t_ox is the thickness of the oxide in nm. Default 300 nm.
        Charge neutrality point centered by default.
        Units are cm^-2
        '''
        eps_SiO2 = 3.9
        eps0 = 8.854187817e-12 #F/m
        self.n = self.Vg*eps0*eps_SiO2/(t_ox*1e-9*e)/100**2 # convert to cm^-2
        if center_CNP:
            CNP = self.find_CNP()
            self.n -= self.n[CNP] # set CNP = 0 carrier density

    def calc_n_LL(self, B_LL, nu, Vg=0):
        '''
        Converts gate voltage to a carrier density using conversion factor
        determined by location of center of quantum Hall plateaux.
        n = nu*e*B_LL/h, where e and h are electron charge and Planck constant,
        B_LL is the field at the center of the Landau Level, and nu is the
        filling factor.
        B_LL and nu should be arrays of landau level centers and filling factors.
        Vg is the gate voltage at which the measurements were taken.
        '''
        if type(B_LL) is not np.ndarray:
            B_LL = np.array(B_LL)

        if type(nu) is not np.ndarray:
            nu = np.array(nu)

        n_at_Vg = np.mean(nu*e*B_LL/h/100**2) # convert to cm^2

        CNP = self.find_CNP()
        if Vg < CNP: ## TYPO??
            n_at_Vg *= -1 # fix the sign if we are below CNP
        self.n = n_at_Vg*(self.Vg-self.Vg[CNP])/(Vg-self.Vg[CNP])

    def calc_n_QHE(self, Vg, n):
        '''
        Calibrate carrier density using density determined via QHE (vs. B) at
        a particular gate voltage.
        '''
        CNP = self.find_CNP()
        VgCNP = self.Vg[CNP]

        self.n = n*(self.Vg-VgCNP)/(Vg-VgCNP)
        return n/(Vg-VgCNP)

    def find_CNP(self):
        '''
        Finds the index of gate voltage corresponding to charge neutrality point
        '''
        return np.where(self.R[0]==np.nanmax(self.R[0]))[0] # find CNP


    def plot(self):
        '''
        Plots using superclass function and adds warning for Ig > 0.5 nA
        '''
        super().plot()
        if self.Igwarning is None: # if no warning
            if len(self.Ig)>0: # if have data
                if abs(self.Ig).max() >= 0.5e-9: # if should be warning
                    self.Igwarning = self.ax.text(.02,.95,
                                        r'$|I_g| \geq 0.5$ nA!',
                                        transform=self.ax.transAxes,
                                        color = 'C3'
                                    ) # warning

    def setup_keithley(self):
        pass
        # self.keithley.zero_V(1) # 1V/s
        # self.keithley.source = 'V'
        # self.keithley.I_compliance = 1e-6
        # self.keithley.Vout_range = max(abs(self.Vstart), abs(self.Vend))


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

        add_text_to_legend('Vstep = %.2f V' %self.Vstep)
        add_text_to_legend('delay = %.2f s' %self.delay)
        if self.Vstart < self.Vend:
            add_text_to_legend(r'sweep $\longrightarrow$')
        else:
            add_text_to_legend(r'sweep $\longleftarrow$')

    def setup_plots(self):
        super().setup_plots()
