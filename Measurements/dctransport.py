import re, time, numpy as np, matplotlib.pyplot as plt
from .measurement import Measurement

class DAQ_IV(Measurement):
    _daq_inputs = ['V1'] # e.g. V1, V2, ... provide an arbitrary number
    _daq_outputs = ['out']
    instrument_list = ['daq','ppms']

    def __init__(self, instruments={}, Vstart = -1, Vend = 1, Vstep=.01, Rbias=1e3, rate=9, bipolar=False):
        '''
        Vstart: Starting voltage (V)
        Vend: Ending voltage (V)
        Vstep: Step size (V)
        Rbias: size of bias resistor (Ohm). Assuming Ibias = Vout/Rbias
        rate: measurement rate (Hz)
        bipolar: sweep up and then back down?
        '''
        self.daq = instruments['daq']
        self.setup_inputs()

        super().__init__(instruments=instruments)

        self.Vstart = Vstart
        self.Vend = Vend
        self.Vstep = Vstep
        self.Rbias = Rbias

        self.rate = rate # Hz # measurement rate of the daq
        self.bipolar = bipolar

        self.V = {i: np.array([]) for i in self._daq_inputs}
        self.Vout = np.array([])

        print('Ibias from %.4f to %.4f mA' %(Vstart/Rbias*1e3, Vend/Rbias*1e3))

    def do(self):
        self.numpts = round(abs(self.Vend-self.Vstart)/self.Vstep)+1
        self.Vout = np.linspace(self.Vstart, self.Vend, self.numpts)

        self.daq.sweep({'out': 0},
           {'out': self.Vout[0]},
           chan_in=self._daq_inputs,
           sample_rate=self.rate,
           numsteps=int(self.numpts/2)
        )

        output_data, received = self.daq.sweep({'out': self.Vout[0]},
                                       {'out': self.Vout[-1]},
                                       chan_in=self._daq_inputs,
                                       sample_rate=self.rate,
                                       numsteps=self.numpts
                                   )

        for inp in self._daq_inputs:
            self.V[inp] = np.array(received[inp])


        self.plot()

        if not self.bipolar:

            self.daq.sweep({'out': self.Vout[-1]},
               {'out': 0},
               chan_in=self._daq_inputs,
               sample_rate=self.rate,
               numsteps=int(self.numpts/2)
            )
        else: # if bipolar
            output_data, received = self.daq.sweep({'out': self.Vout[-1]},
                                           {'out': self.Vout[0]},
                                           chan_in=self._daq_inputs,
                                           sample_rate=self.rate,
                                           numsteps=self.numpts
                                       )

            for inp in self._daq_inputs:
                self.Vout = np.append(self.Vout, self.Vout[::-1])
                self.V[inp] = np.append(self.V[inp], np.array(received[inp]))

            self.plot()

            self.daq.sweep({'out': self.Vout[0]},
               {'out': 0},
               chan_in=self._daq_inputs,
               sample_rate=self.rate,
               numsteps=int(self.numpts/2)
            )

    def plot(self):
        super().plot()

        for inp, line in self.lines.items():
            line.set_xdata(self.Vout/self.Rbias*1e3)
            line.set_ydata(self.V[inp]*1e3)

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def plot_diff(self, i, j):
        '''
        Plot the difference between two voltage channel numbers i,j
        '''
        fig, ax = plt.subplots()
        ax.set_xlabel('V_{out}/R_{bias} (mA)', fontsize=20)
        ax.set_ylabel('Voltage difference %i-%i (mV)' %(i,j), fontsize=20)
        ax.plot(self.Vout/self.Rbias*1e3, (self.V['V%i' %i] - self.V['V%i' %j])*1e3)

    def setup_inputs(self):
        '''
        Search for inputs named 'V*', where * is an integer used to label pin numbers.
        self._daq_inputs will be modified to be a list of these inputs.
        '''
        self._daq_inputs = []
        for label, inp in self.daq.inputs.items():
            if re.match('^V[0-9]+$', label):
                self._daq_inputs.append(label)

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('V_{out}/R_{bias} (mA)', fontsize=20)
        self.ax.set_ylabel('Voltage (mV)', fontsize=20)

        ## plot all the resistances
        self.lines = {}
        for inp in self._daq_inputs:
            line = self.ax.plot(self.Vout/self.Rbias*1e3, self.V[inp]*1e3)
            self.lines[inp] = line[0]

        l = self.ax.legend([i for i in self._daq_inputs], loc='best')
        self.ax.set_title(self.filename)

#made by Phillip Dang - very rudimentary!
class RvsSomethingDC(Measurement):
    '''
    Monitor R = keithley_V.V/keithley_I.I from two different keithleys.
    Can supply additional keithley_V2, keithley_V3, etc to montior more voltages
    (plotted as resistance)
    This is a superclass for measuring resistance vs different things
    (e.g. gate voltage, temperature, field...)
    By default, this class measures vs. time (useful for timing subclasses!)

    Make sure to change the name of the "something" you're measuring vs!
    '''
    instrument_list = ['keithley_V1', 'keithley_I']
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
            if name[:-1] == 'keithley_V': # e.g. lockin_V2, cut off the "2"
                setattr(self, name, handle)

    @property
    def num_lockins(self):
        num_lockins=0
        for name, handle in self.__dict__.items():
            if name[:-1] == 'keithley_V': # e.g. lockin_V2, cut off the "2"
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


        self.Ix = np.append(self.Ix, self.keithley_I.I)

        for j in range(self.num_lockins):
            if auto_gain:
                getattr(self, 'keithley_V%i' %(j+1)).fix_sensitivity() # make sure we aren't overloading or underloading.
                self.keithley_I.fix_sensitivity()

            ## Take as many measurements as requested and average them
            vx = 0
            vy = 0
            r = 0
            for i in range(num_avg):
                vx += getattr(self, 'keithley_V%i' %(j+1)).V

                r += vx/self.Ix[-1]
                if i != num_avg-1: # no reason to sleep the last time!
                    time.sleep(delay_avg)
            vx /= num_avg
            vy /= num_avg
            r /= num_avg

            self.Vx[j] = np.append(self.Vx[j], vx)
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

class RvsVg_DC(RvsSomethingDC):
    '''
    Monitor R = keithley2000_V.V/keithley2400_I.I from two different keithley multimeters.
    Can supply additional keithley2000_V2, keithley2000_V3, etc to montior more voltages
    (plotted as resistance)
    '''
    instrument_list = ['keithley', 'keithley_V1', 'keithley_I']
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

class RvsT_Montana_Keithley(Measurement):
    instrument_list = ['montana', 'keithley']
    something = 'T'
    something_units = 'K'

    def __init__(self, instruments = {}, Ibias=100, Tend = 4.5, delay=5, numavg=5):
        '''
        Measurement will test voltage at +Ibias and -Ibias uA (changing instantaneously!)
        Keithley in 4-wire mode.
        Ibias: current bias (uA).
        Tend: target temperature (when to stop taking data)
        delay: time between measurements (seconds)
        numavg: number of averages
        '''
        super().__init__(instruments=instruments)

        self.Ibias = Ibias*1e-6
        self.Tend = Tend
        self.delay = delay
        self.numavg = numavg

        self.Vp = np.array([])
        self.Vz = np.array([])
        self.Vn = np.array([])
        self.Ra = np.array([]) # (Vp-Vz)/I
        self.Rb = np.array([]) # (Vz-Vn)/I
        self.Rc = np.array([]) # (Vp-Vn)/(2I)
        self.T = np.array([])



    def do(self, plot=True):
        while self.montana.temperature['platform'] > self.Tend:
            time.sleep(self.delay)

            self.T = np.append(self.T, self.montana.temperature['platform'])

            self.keithley.Iout = 0
            self.Vz = np.append(self.Vz, self.get_avg_voltage())

            self.keithley.Iout = self.Ibias
            self.Vp = np.append(self.Vp, self.get_avg_voltage())

            self.keithley.Iout = -self.Ibias
            self.Vn = np.append(self.Vn, self.get_avg_voltage())

            self.keithley.Iout = 0

            self.Ra = np.append(self.Ra, (self.Vp[-1] - self.Vz[-1])/self.Ibias)
            self.Rb = np.append(self.Rb, (self.Vz[-1] - self.Vn[-1])/self.Ibias)
            self.Rc = np.append(self.Rc, (self.Vp[-1] - self.Vn[-1])/self.Ibias/2)

            self.plot()

    def get_avg_voltage(self):
        V = 0
        for i in range(self.numavg):
            V += self.keithley.V
        return V / self.numavg


    def plot_update(self):
        self.la.set_xdata(self.T)
        self.lb.set_xdata(self.T)
        self.lc.set_xdata(self.T)
        self.la.set_ydata(self.Ra)
        self.lb.set_ydata(self.Rb)
        self.lc.set_ydata(self.Rc)

        self.ax.relim()
        self.ax.autoscale_view()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.la = self.ax.plot(self.T, self.Ra, label = '+')[0]
        self.lb = self.ax.plot(self.T, self.Rb, label = '-')[0]
        self.lc = self.ax.plot(self.T, self.Rc, label = 'full')[0]
        self.ax.set_xlabel('Temperature (K)')
        self.ax.set_ylabel('Resistance (Ohm)')

        l = self.ax.legend(loc='best')
