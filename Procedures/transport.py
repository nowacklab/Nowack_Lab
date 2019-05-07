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
        if duration is None:
            while True:
                self.time = np.append(self.time, time.time()-self.time_start)
                self.do_measurement(delay, num_avg, delay_avg, plot, auto_gain=auto_gain)
                if duration is not None:
                    if self.time[-1] >= duration:
                        break


    def do_measurement(self, delay = 0, num_avg = 1, delay_avg = 0,
                                all_positive=False, plot=True, auto_gain=True):
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

            ## Take as many measurements as requested and average them
            vx = 0
            vy = 0
            r = 0
            for i in range(num_avg):
                if auto_gain:
                    getattr(self, 'lockin_V%i' %(j+1)).fix_sensitivity() # make sure we aren't overloading or underloading.
                    self.lockin_I.fix_sensitivity()
                vx += getattr(self, 'lockin_V%i' %(j+1)).X
                vy += getattr(self, 'lockin_V%i' %(j+1)).Y

                r += vx/self.Ix[-1]
                if i != num_avg-1: # no reason to sleep the last time!
                    time.sleep(delay_avg)
            vx /= num_avg
            vy /= num_avg
            r /= num_avg

            if all_positive:
                r = abs(r)

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
        plt.pause(1e-6) # live plotting outside notebooks


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

        if hasattr(self, 'keithley'):
            if self.keithley is not None:
                if self.something != 'Vg':
                    add_text_to_legend('Vg = %.1f V' %self.keithley.V)

    def setup_lockins(self):
        self.lockin_V1.input_mode = 'A-B'
        self.lockin_I.input_mode = 'I (10^8)'
        self.lockin_V1.reference = 'internal'
#         self.lockin_V.frequency = 53.01
        self.lockin_I.reference = 'external'


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


class BlueforsRvsT(RvsSomething):
    instrument_list = ['lakeshore','lockin_V1', 'lockin_I']
    something='T'
    something_units = 'K'

    def __init__(self, instruments = {}, duration=36000, interval=1,
                channel = 8):
        '''
        Bluefors R vs T.  No PID (no control).

        Parameters:
        instruments:    (dict) dict of instruments
        duration:       (int) time to measure in seconds
        interval:       (int) time to wait between each measurement
        '''
        super().__init__(instruments=instruments)
        self.duration = duration
        self.interval = interval
        self.channel  = channel
        self.lakeshore.enable_only(self.channel)

    def do(self, plot=True, auto_gain=False):
        self.startTime = time.time() #seconds since epoch
        self.lakeshoreR = [];
        while time.time() < self.startTime + self.duration:
            self.T = np.append(self.T, self.lakeshore.T[self.channel])
            self.lakeshoreR.append(self.lakeshore.R[self.channel])
            self.do_measurement(delay=0,plot=plot,auto_gain=auto_gain)
            time.sleep(self.interval)
        self.lakeshore.enable_all()


    def setup_lockins(self):
        '''
        Overload setup_lockins and just pass to allow user to set 
        lockins manually
        '''
        pass

class MonitorAttrs(Measurement):
    def __init__(self, instruments, attrs, duration, wait):
        super().__init__(instruments)
        self.wait = wait
        self.duration = duration
        self.data = {}
        self.callables = []
        for attr in attrs:
            self.callables.append(CallableAttribute(*attr))
            self.data[attr[2]] = []
        self.attrs = attrs
        self.time_data = []
        self.start = time.time()

    def do(self, plot=False):
        while ((self.start + self.duration) > time.time()):
            time.sleep(self.wait)
            # Record data\
            self.time_data.append(time.time())
            for call in self.callables:
                self.data[call.name].append(call())

    def save(self, filename=None, savefig=False, **kwargs):
        self.time_data = np.array(self.time_data)
        for call in self.callables:
            setattr(self, call.name, np.array(self.data[call.name]))
        try:
            self._save(filename, savefig, **kwargs)
        except:
            pass


class PID_T(Measurement):
    """PID control temperature while monitoring instrument attributes.
    """
    instrument_list = ['lakeshore']
    def __init__(self, instruments, temps, attributes, tol):
        """Record the values of the attributes while tuning temperature.

        Args:
        attributes (iterable): Iterable of (instrument, attribute, name) pairs
        temps (iterable): Temperature setpoints for the experiment.
        instruments (dict): Instruments used for the experiment.
        tol (float): Temperature tolerance 

        Ideally the instruments specified in attribues are also in the
        instruments dictionary so the configuration of all instrumens in the
        experiment is saved in the json file.
        """
        super().__init__(instruments)
        self.temps = temps
        self.callables = [CallableAttribute(self.lakeshore.chan6, "T", "T")]
        self.data = {"T": []}
        for attr in attributes:
            self.callables.append(CallableAttribute(*attr))
            self.data[attr[2]] = []
        self.attributes = attributes
        self.tol = tol
        self.temp_data = []

    def do(self, plot=False, auto_gain=False):
        for temp in self.temps:
            # Adjust the temperature
            self.lakeshore.pid_setpoint = temp
            # Wait for temperature stability
            ret = RvTPID.check_stability(self.lakeshore, self.tol, 10, 300)
            self.temp_data.append(ret)
            time.sleep(10)
            # Record the data for 
            for call in self.callables:
                self.data[call.name].append(call())

    def save(self, filename=None, savefig=False, **kwargs):
        """Ignore reloading failed exception."""
        try:
            self._save(filename, savefig, **kwargs)
        except:
            pass
            
    @staticmethod
    def check_stability(lakeshore, tol, monitor_time, max_time):
        """Return when all points within last monitor_time are within tol"""
        data = []
        start = time.time()
        # Sample the temperature
        while ((start + monitor_time) > time.time()):
            time.sleep(1)
            data.append(lakeshore.chan6.T)

        # Check if temperature is stable
        while ((start + max_time) > time.time()):
            time.sleep(1)
            done = False
            for t in data:
                # If a point is not within tol take another point
                if (np.abs(t - lakeshore.pid_setpoint) > tol):
                    data.append(lakeshore.chan6.T)
                    del data[0]
                    break
                else:
                    done = True
            if done:
                break
        return data



class CallableAttribute(object):
    """Make an instrument attribute a callable function."""
    def __init__(self, instrument, attribute, name):
        self.instrument = instrument
        self.attribute = attribute
        self.name = name.

    def __call__(self):
        """Return the attribute of the instrument."""
        return getattr(self.instrument, self.attribute)

    
class SimpleRvsTime(Measurement):
    def __init__(self, instruments={}, duration=100, delay=1):
        super().__init__(instruments=instruments)
        self.duration = duration
        self.delay=delay
        
    def do(self):
        self.starttime = time.time()
        self.V1xs = np.zeros(int(self.duration/self.delay)+1)
        self.V1ys = np.zeros(int(self.duration/self.delay)+1)
        self.V2xs = np.zeros(int(self.duration/self.delay)+1)
        self.V2ys = np.zeros(int(self.duration/self.delay)+1)
        self.Ixs = np.zeros(int(self.duration/self.delay)+1)
        self.Iys = np.zeros(int(self.duration/self.delay)+1)
        self.time = np.zeros(int(self.duration/self.delay)+1)
        i = 0
        while (self.starttime + self.duration > time.time() ):
            self.time[i] = time.time()
            self.V1xs[i] = self.lockin_V1.X
            self.V1ys[i] = self.lockin_V1.Y
            self.V2xs[i] = self.lockin_V2.X
            self.V2ys[i] = self.lockin_V2.Y
            self.Ixs[i]  = self.lockin_I.X
            self.Iys[i]  = self.lockin_I.Y
            print(
                    "{0}/{1}: [V1x,V1y,V2x,V2y,Ix,Iy] = [{2:2.2e},{3:2.2e},{4:2.2e},{5:2.2e},{6:2.2e},{7:2.2e}]".format(
                i, int(self.duration/self.delay),
                self.V1xs[i], self.V1ys[i], self.V2xs[i], self.V2ys[i],self.Ixs[i], self.Iys[i]
                ))
            print(
                    "[R1x,R1y,R2x,R2y] = [{0:2.2e}, {1:2.2e}, {2:2.2e},{3:2.2e}]".format(
                self.V1xs[i]/self.Ixs[i], self.V1ys[i]/self.Iys[i],
                self.V2xs[i]/self.Ixs[i], self.V2ys[i]/self.Iys[i]
                ))
            time.sleep(self.delay)
            i += 1

        

    def plot(self):
        pass

    def setup_plots(self):
        pass


class VvsF(Measurement):
    instrument_list = ['lockin_V']

    def __init__(self, instruments={}, freqs = [], dwelltime = 1):
        '''
        Measure voltage on lockin as a funtion of lockin frequency

        parameters:
        instruments:    (dict) dict of instruments, only 1 lockin
        freqs:          (list) list of frequencies to scan with lockin
        dwelltime       (float) time to wait between measurements (s)
        '''
        super().__init__(instruments=instruments)
        self.freqs = freqs
        self.dwelltime = dwelltime
    
    def do(self):
        self.Vxs = []
        self.Vys = []
        i = 0
        for f in self.freqs:
            self.lockin_V.frequency = f
            time.sleep(self.dwelltime)
            self.Vxs.append(self.lockin_V.X)
            self.Vys.append(self.lockin_V.Y)
            print("{0}/{1}: [f, Vx, Vy] = [{2}, {3}, {4}]".format(
                i, len(self.freqs), f, self.Vxs[-1], self.Vys[-1]))
            i+=1

    def setup_plots(self):
        pass

    def plot(self):
        pass



class VvsIdc(Measurement):
    instrument_list = ['nidaq', 'keithley', 'preamp']

    def __init__(self, daqchannel, instruments={}, iouts=[], dwelltime=.01):
        '''
        '''
        super().__init__(instruments=instruments)
        self.iouts=iouts
        self.dwelltime=dwelltime
        self.daqchannel = daqchannel

    def __repr__(self):
        return 'VvsIdc({0},instruments,{1},{2})'.format(
                repr(self.daqchannel),
                repr(self.iouts),
                repr(self.dwelltime))

    def do(self, slowsweeprate = 200e-6, slowsweeppts=50, 
            plot=True, removeplot=True):
        self.Vmea = np.zeros(len(self.iouts))
        self.Isrc = np.zeros(len(self.iouts))
        self.gain = self.preamp.gain

        # slowly sweep to the starting voltage
        self.slowsweep(self.iouts[0], numpts=slowsweeppts, ipers=slowsweeprate)

        # Sweep keithley, wait dwelltime, and record voltage at each point
        for i in range(len(self.iouts)):
            starttime = time.time()
            self.keithley.Iout = self.iouts[i] 
            self.Isrc[i] = self.keithley.Iout
            VvsIdc.wait(starttime, self.dwelltime)
            self.Vmea[i] = self.daqchannel.V/self.gain

        # fit the voltages / applied currents to a line to extract R and error
        [p,covar] = np.polyfit(self.Isrc, self.Vmea, deg=1, cov=True)
        self.Rfits = p
        self.covar = covar
        self.R = self.Rfits[0]

        if plot:
            self.plot()
        if removeplot:
            plt.close()

    def slowsweep(self, itarget, ipers=100e-6, numpts = 10):
        istart = self.keithley.Iout
        iend = itarget
        currents = np.linspace(istart, iend, numpts)
        timesleep = abs(currents[1]-currents[0])/ipers
        for c in currents:
            self.keithley.Iout = c
            VvsIdc.wait(time.time(), timesleep)
            
    @staticmethod           
    def wait(starttime, dwelltime):
        if (starttime + dwelltime > time.time()):
            time.sleep(starttime + dwelltime - time.time())

    def setup_plots(self):
        self.fig = 0
        self.ax = 0

    def plot(self, **plot_kwargs):
        self.fig, self.ax = plt.subplots()
        self.ax.ticklabel_format(style='sci', axis='both', scilimits=(0,0), useMathText=True)
        self.ax.plot(self.Isrc, self.Vmea, 
                label='Data',
                marker='o', linestyle='', markersize=5, **plot_kwargs)
        extra = abs(self.Isrc.max() - self.Isrc.min())*.1
        xs = np.linspace(self.Isrc.min() - extra, self.Isrc.max() + extra, 100) 
        p = np.poly1d(self.Rfits)
        err = np.diag(self.covar)**.5
        self.ax.plot(xs, p(xs), linestyle='-', marker='', 
        label=r'Fit: V = ({0:2.2e}$\pm${2:2.2e})I + ({1:2.2e}$\pm${3:2.2e})'.format( 
                                                              self.Rfits[0], 
                                                              self.Rfits[1],
                                                              err[0], 
                                                              err[1]))
        self.ax.legend(fontsize=8)
        self.ax.set_xlabel('I (A)')
        self.ax.set_ylabel('V (V)')
        return [self.fig,self.ax]


class VvsIdc_daq(VvsIdc):

    instrument_list = ['nidaq', 'preamp']
    _daq_inputs = ['iv']
    _daq_outputs= ['iv']

    def __init__(self, instruments={}, iouts=[], 
                 iv_Rbias = 3165, dwelltime=.01):
        super().__init__(instruments=instruments)
        self.iouts=np.array(iouts)
        self.iv_Rbias = iv_Rbias
        self.vouts= self.iouts * self.iv_Rbias
        self.dwelltime=dwelltime
        self.dwelltime = dwelltime
        self.rate = 1/self.dwelltime

    def do(self, plot=True, removeplot=True):

        _,_ = self.nidaq.singlesweep(self._daq_outputs[0], 
                                     self.vouts[0], 
                                     numsteps = int(len(self.iouts)/2),
                                     rate = self.rate*2)

        vmeas = []
        for v in self.vouts:
            self.nidaq.outputs[self._daq_outputs[0]].V = v
            time.sleep(self.dwelltime)
            self.vmeas.append(self.nidaq.inputs[self._daq_inputs[0]].V)


        _,_ = self.nidaq.singlesweep(self._daq_outputs[0], 
                                     0,
                                     numsteps = int(len(self.iouts)/2),
                                     rate = self.rate*2)


        # So I don't have to write another plotting routine
        self.Vmea = np.array(vmeas)
        self.Isrc = np.array(self.iouts)
            
        if plot:
            self.plot()
        if removeplot:
            plt.close()



class RvsVg(RvsSomething):
    '''
    Monitor R = lockin_V.X/lockin_I.Y from two different lockins.
    Can supply additional lockin_V2, lockin_V3, etc to montior more voltages
    (plotted as resistance)
    '''
    instrument_list = ['keithley', 'lockin_V', 'lockin_I']
    something = 'Vg'
    something_units = 'V'

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
            numpts_sm = round(abs(Vmin-Vstart)/Vstep)+1
            numpts_mm = round(abs(Vmin-Vmax)/Vstep*10)+1
            numpts_me = round(abs(Vmax-Vend)/Vstep)+1
            self.Vg_values = np.concatenate((
                    np.linspace(Vstart, Vmin, numpts_sm, endpoint=False),
                    np.linspace(Vmin, Vmax, numpts_mm, endpoint=False),
                    np.linspace(Vmax, Vend, numpts_me)
                )
            )

        self.Ig = np.array([])
        self.T = np.array([])

        self.setup_keithley()

    def do(self, num_avg = 1, delay_avg = 0, zero=False, all_positive=False, plot=True, auto_gain=False):
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

            self.do_measurement(self.delay, num_avg, delay_avg, all_positive=all_positive, plot=plot, auto_gain=auto_gain)

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
        super().plot()

        self.lineIg.set_xdata(self.Vg)
        self.lineIg.set_ydata(self.Ig*1e9)
        self.axIg.relim()
        self.axIg.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()

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

        self.axIg = self.ax.twinx()
        self.axIg.set_ylabel('Ig (nA)', fontsize=20, color='r', alpha=0.2)

        lineIg = self.axIg.plot(self.Vg, self.Ig*1e9, 'r', alpha=0.2)
        self.lineIg = lineIg[0]
