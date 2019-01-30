import re, time, numpy as np, matplotlib.pyplot as plt
from .measurement import Measurement
from .transport import RvsSomething, RvsT, RvsVg
from .magnetotransport import RvsB_Phil

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

    def do(self, **kwargs):
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



    def do(self, plot=True, **kwargs):
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

class RvsSomething_DC(RvsSomething):
    '''
    Monitor R by taking DC voltage input of Zurich and dividing by a bias current
    applied using a keithley.
    This is a superclass for measuring resistance vs different things
    (e.g. gate voltage, temperature, field...)
    By default, this class measures vs. time (useful for timing subclasses!)

    Make sure to change the name of the "something" you're measuring vs!

    Tee off the voltage to do a two-point measurement
    Run through a high impedance preamp then connect to Zurich aux 2
    This will be recorded as R2p

    Preamp may be used before the Zurich input. Specify preamp_gain manually.
    NOTE the preamp_gain parameter only affects the signal received from the Zurich's normal inputs.

    two_point: 'aux' or 'keithley'. 'aux' will take an average as described above
    'keithley' will record the keithley voltage output.
    '''
    instrument_list = ['zurich', 'keithleybias']
    something='time'
    something_units = 's'
    legendtitle=None

    def __init__(self, instruments = {}, preamp_gain=1, two_point='aux'):
        Measurement.__init__(self, instruments=instruments)

        # Set up empty arrays
        self.V = np.array([])
        self.V2p = np.array([])
        self.I = np.array([])
        self.B = np.array([]) # if we can record field, let's do it.
        self.T = np.array([]) # if we can record temperature

        self.R = np.array([])
        self.R2p = np.array([])
        setattr(self, self.something, np.array([]))

        self.preamp_gain = preamp_gain
        assert two_point in ('keithley', 'aux')
        self.two_point = two_point

    def do(self, *args, **kwargs):
        return RvsSomething.do(self, auto_gain=True, **kwargs)

    def do_measurement(self, delay = 0, num_avg = 1, delay_avg = 0,
                                plot=True, auto_gain=True):
        '''
        Take a resistance measurement. Usually this will happen in a loop.
        Optional argument to set a delay before the measurement happens.
        plot argument determines whether data is plotted or not
        num_avg is the number of data points to be averaged
        delay_avg is the time delay (seconds) between averages
        auto_gain: automatically adjust lockin gain for small or OL signals
            This adds a default delay of 5 seconds

        Doesn't make a whole lot of sense to average for a measurement vs time,
        but the averaging could be useful for a subclass.
        '''

        if delay > 0:
            time.sleep(delay)

        self.I = np.append(self.I, self.keithleybias.I)

        if auto_gain:
            self.zurich.autorange(force=False) # takes 5 seconds by default!!

        # Take as many measurements as requested and average them
        v = 0
        v2p = 0
        r = 0
        r2p = 0
        for i in range(num_avg):
            if self.two_point == 'aux':
                t, V = self.zurich.get_scope_trace(self.zurich.freq_opts[10], input_ch=9) # aux in 2
                v2p += V.mean()
                r2p += v2p/self.I[-1]
            elif self.two_point == 'keithley':
                v2p += self.keithleybias.V
                r2p += v2p/self.I[-1]

            t, V = self.zurich.get_scope_trace(self.zurich.freq_opts[10])
            v += V.mean()
            r += v/self.I[-1]
            if i != num_avg-1: # no reason to sleep the last time!
                time.sleep(delay_avg)
        v /= num_avg
        r /= num_avg
        v2p /= num_avg
        r2p /= num_avg

        self.V = np.append(self.V, v / self.preamp_gain)
        self.R = np.append(self.R, r / self.preamp_gain)
        self.V2p = np.append(self.V2p, v2p)
        self.R2p = np.append(self.R2p, r2p)


        # Get temperature and field (if available)
        self.get_temperature_field()

        if plot:
            self.plot()


    def plot(self):
        Measurement.plot(self)

        self.line.set_xdata(getattr(self, self.something))
        self.line.set_ydata(self.R)

        self.line2p.set_xdata(getattr(self, self.something))
        self.line2p.set_ydata(self.R2p)

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()


    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('%s (%s)' %(self.something, self.something_units), fontsize=20)
        self.ax.set_ylabel('R (Ohm)', fontsize=20)

        ## plot all the resistances
        line =  self.ax.plot(getattr(self, self.something), self.R)
        self.line = line[0]

        line2p = self.ax.plot(getattr(self, self.something), self.R2p)
        self.line2p = line2p[0]

        self.ax.set_title(self.filename)
        self.fig.tight_layout()


class RvsSomething_DC_KeithleyYoko(RvsSomething_DC):
    '''
    Monitor R by taking DC voltage input on a Keithley 2000 multimeter
    and dividing by a bias current applied using a Yokogawa (not programmed).
    This is a superclass for measuring resistance vs different things
    (e.g. gate voltage, temperature, field...)
    By default, this class measures vs. time (useful for timing subclasses!)

    Make sure to change the name of the "something" you're measuring vs!

    Tee off the voltage to do a two-point measurement
    Run through a high impedance preamp then connect to Zurich aux 2
    This will be recorded as R2p
    '''
    instrument_list = ['keithleyV']
    something='time'
    something_units = 's'
    legendtitle=None

    def __init__(self, instruments = {}, Ibias=20e-6, preamp_gain=1):
        Measurement.__init__(self, instruments=instruments)

        # Set up empty arrays
        self.V = np.array([])
        self.I = np.array([])
        self.B = np.array([]) # if we can record field, let's do it.
        self.T = np.array([]) # if we can record temperature

        self.R = np.array([])
        setattr(self, self.something, np.array([]))

        self.Ibias = 20e-6
        self.preamp_gain = preamp_gain


    def do_measurement(self, delay = 0, num_avg = 1, delay_avg = 0,
                                plot=True, auto_gain=True):
        '''
        Take a resistance measurement. Usually this will happen in a loop.
        Optional argument to set a delay before the measurement happens.
        plot argument determines whether data is plotted or not
        num_avg is the number of data points to be averaged
        delay_avg is the time delay (seconds) between averages
        auto_gain: automatically adjust lockin gain for small or OL signals
            This adds a default delay of 5 seconds

        Doesn't make a whole lot of sense to average for a measurement vs time,
        but the averaging could be useful for a subclass.
        '''

        if delay > 0:
            time.sleep(delay)

        self.I = np.append(self.I, self.Ibias)

        # Take as many measurements as requested and average them
        v = 0
        r = 0
        r2p = 0
        for i in range(num_avg):
            V = self.keithleyV.V
            v += V
            r += v/self.I[-1]
            if i != num_avg-1: # no reason to sleep the last time!
                time.sleep(delay_avg)
        v /= num_avg
        r /= num_avg

        self.V = np.append(self.V, v / self.preamp_gain)
        self.R = np.append(self.R, r / self.preamp_gain)

        # Get temperature and field (if available)
        self.get_temperature_field()

        if plot:
            self.plot()


    def plot(self):
        Measurement.plot(self)

        self.line.set_xdata(getattr(self, self.something))
        self.line.set_ydata(self.R)

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()


    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('%s (%s)' %(self.something, self.something_units), fontsize=20)
        self.ax.set_ylabel('R (Ohm)', fontsize=20)

        ## plot all the resistances
        line =  self.ax.plot(getattr(self, self.something), self.R)
        self.line = line[0]

        self.ax.set_title(self.filename)
        self.fig.tight_layout()


class RvsB_Phil_DC(RvsSomething_DC, RvsB_Phil):
    '''
    DC version of RvsB_Phil
    '''
    instrument_list = ['zurich', 'keithleybias', 'magnet']
    something = 'B'
    something_units = 'T'

    def __init__(self, instruments = {}, Bend = 1, delay=1, sweep_rate=.1,
                persistent=True, **kwargs):
        '''
        Sweep rate and field in T. Delay is in seconds. Rate is T/min
        persistent: whether to enter persistent mode after the measurement
        '''
        RvsB_Phil.__init__(self, instruments, Bend, delay, sweep_rate)
        RvsSomething_DC.__init__(self, instruments, **kwargs)
        self.persistent = persistent


class RvsTime_DC(RvsSomething_DC):
    '''
    Alias for RvsSomething_DC
    '''
    pass


class RvsT_DC(RvsSomething_DC, RvsT):
    '''
    DC version of RvsT
    '''
    instrument_list = ['ppms', 'zurich', 'keithleybias']
    something = 'T'
    something_units = 'K'

    def __init__(self, instruments = {}, Tstart = 300, Tend = 10, delay=1,
        sweep_rate=10, **kwargs):
        '''
        Sweep rate and temperature in K. Delay is in seconds. Rate is K/min
        **kwargs for RvsSomething_DC
        '''
        RvsSomething_DC.__init__(self, instruments=instruments, **kwargs)

        self.Tstart = Tstart
        self.Tend = Tend
        self.delay = delay
        self.sweep_rate = sweep_rate

class RvsVg_DC(RvsSomething_DC, RvsVg):
    '''
    DC version of RvsVg
    '''
    instrument_list = ['keithley', 'zurich', 'keithleybias']
    something = 'Vg'
    something_units = 'V'

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1,
        delay=1, fine_range=None, **kwargs):
        '''
        Vstart: starting voltage (V)
        Vend: ending voltage (V)
        Vstep: voltage step size (V)
        delay: time delay between measurements (sec)
        fine_range: [Vmin, Vmax], a list of two voltages that define a range
        in which we will take N times as many data points. N=5.
        Note that Vmin is closer to Vstart and Vmax is closer to Vend,
        regardless of sweep direction.

        **kwargs for RvsSomething_DC
        '''
        RvsSomething_DC.__init__(self, instruments=instruments, **kwargs)

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

    def do(self, *args, **kwargs):
        return RvsVg.do(self, auto_gain=True, **kwargs)


class RvsVg_DC_KeithleyYoko(RvsSomething_DC_KeithleyYoko, RvsVg):
    '''
    DC version of RvsVg
    '''
    instrument_list = ['keithley', 'keithleyV']
    something = 'Vg'
    something_units = 'V'

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1,
        delay=1, fine_range=None, **kwargs):
        '''
        Vstart: starting voltage (V)
        Vend: ending voltage (V)
        Vstep: voltage step size (V)
        delay: time delay between measurements (sec)
        fine_range: [Vmin, Vmax], a list of two voltages that define a range
        in which we will take N times as many data points. N=5.
        Note that Vmin is closer to Vstart and Vmax is closer to Vend,
        regardless of sweep direction.

        **kwargs for RvsSomething_DC_KeithleyYoko
        '''
        RvsSomething_DC_KeithleyYoko.__init__(self, instruments=instruments, **kwargs)

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
