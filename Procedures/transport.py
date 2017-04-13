import time, numpy as np, matplotlib.pyplot as plt
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict
from matplotlib import cm

## Constants here
e = 1.60217662e-19 #coulombs
h = 6.626e-34 # m^2*kg/s

class IV(Measurement):
    '''
    UNDER CONSTRUCTION
    '''
    instrument_list = ['lockin_V', 'lockin_I']
#     I_compliance = 1e-6 # 1 uA

    def __init__(self, instruments = {}, Vstart = 0, Vend = 1, Vstep=.1, delay=1):
        '''
        Vstart: starting amplitude output from lockin
        Vend: ending amplitude output from lockin
        Vstep: amplitude step
        delay: time between changing voltage. Make sure this is 5x longer than time constant or 1/frequency)

        Use one lockin to source a voltage to a bias resistor. This lockin also measures voltage.
        The second lockin is synced to the first and measures current.
        '''
        super().__init__()
        self._load_instruments(instruments)

        self.Vstart = Vstart
        self.Vend = Vend
        self.Vstep = Vstep
        self.delay = delay

        self.Vs = np.linspace(Vstart, Vend, round(abs(Vend-Vstart)/Vstep)+1)

        self.Vx = np.full(self.Vs.shape, np.nan)
        self.Vy = np.full(self.Vs.shape, np.nan)
        self.Ix = np.full(self.Vs.shape, np.nan)
        self.Iy = np.full(self.Vs.shape, np.nan)
        self.R = np.full(self.Vs.shape, np.nan)

        self.setup_lockins()
        print('David')


    def do(self, plot=True, zero = True):
        print("begin do")
        #if self.fig == None:
        #    self.setup_plots()
        if(plot):
            self.setup_plots();

        ## Sweep to Vstart
        self.lockin_V.sweep(self.lockin_V.amplitude, self.Vstart, .01, .1)

        ## Do the measurement sweep
        print("Begin Measurement")
        for i, Vs in enumerate(self.Vs):
            self.lockin_V.amplitude = Vs
            #while self.lockin_V.is_OL():
                #self.lockin_V.sensitivity = 
            # if self.lockin_V.is_OL() or i==0: # only do auto gain if we're overloading or if it's the first measurement
            #     self.lockin_V.auto_gain()
            # if self.lockin_I.is_OL() or i==0:
            #     self.lockin_I.auto_gain()
            #time.sleep(self.delay)

            self.Vx[i] = self.lockin_V.X
            self.Vy[i] = self.lockin_V.Y
            self.Ix[i] = self.lockin_I.X
            self.Iy[i] = self.lockin_I.Y

        if(plot):
            self.plot()

        self.R = np.array([self.Vx[i]/self.Ix[i] for i in range(2,len(self.Vx))]);
        self.Rstd = np.std(self.R);
        self.Rave = np.mean(self.R);
        print(self.Rave, self.Rstd)
        self.save()

        if(zero):
            self.lockin_V.zero();

    def plot(self):
        super().plot()
        self.ax['x'].plot(self.Ix*1e6,self.Vx*1e6);
        self.ax['y'].plot(self.Iy*1e9,self.Vy*1e9);

        #self.line.set_xdata(self.Ix*1e6)
        #self.line.set_ydata(self.Vx*1e3)

        #self.ax.relim()
        #self.ax.autoscale_view(True,True,True)

        #self.fig.tight_layout()
        #self.fig.canvas.draw()


    def setup_lockins(self):
        self.lockin_V.input_mode = 'A-B'
        self.lockin_I.input_mode = 'I (10^6)'
        self.lockin_V.reference = 'internal'
#         self.lockin_V.frequency = 53.01
        self.lockin_I.reference = 'external'
        self.lockin_V.alarm_off()
        self.lockin_I.alarm_off()


    def setup_plots(self):
        self.fig = plt.figure(figsize=(12,6))
        self.ax = AttrDict()
        self.ax['x'] = self.fig.add_subplot(121)
        self.ax['y'] = self.fig.add_subplot(122)
        self.ax['x'].set_xlabel('I (uA)')
        self.ax['x'].set_ylabel('V (uV)')
        self.ax['y'].set_xlabel('I (nA)')
        self.ax['y'].set_ylabel('V (nV)')

        #line = self.ax.plot(self.Ix*1e6, self.Vx*1e3)
        #self.line = line[0]
        self.ax['x'].annotate(self.timestamp, xy=(0.02,.98), xycoords='axes fraction',
            fontsize=10, ha='left', va = 'top', family='monospace'
        )
        #self.ax.set_title(self.filename)


class IVvsVg(Measurement):
    instrument_list = ['keithley', 'lockin_V', 'lockin_I']
    I_compliance = 1e-6 # 1 uA

    def __init__(self, instruments = {}, Vstart = 0, Vend = 1, Vstep=.1, delay=1, Vgmin=0, Vgmax=1, Vgstep=.1):
        '''
        Vstart: starting amplitude output from lockin
        Vend: ending amplitude output from lockin
        Vstep: amplitude step

        Vgmin: smallest backgate voltage
        Vgmax: largest backgate voltage
        Vgstep: backgate voltage step

        delay: time between changing voltage. Make sure this is 5x longer than time constant or 1/frequency)

        Use one lockin to source a voltage to a bias resistor. This lockin also measures voltage.
        The second lockin is synced to the first and measures current.
        '''
        super().__init__()
        self._load_instruments(instruments)

        self.IV = IV(instruments, Vstart, Vend, Vstep, delay)

        self.Vgmin = Vgmin
        self.Vgmax = Vgmax
        self.Vgstep = Vgstep

        self.Vg = np.linspace(Vgmin, Vgmax, round(abs(Vgmax-Vgmin)/Vgstep)+1)

        self.setup_keithley()


    def do(self):
        self.keithley.sweep_V(0, self.Vgmin, .1, 1)

        colors = [cm.coolwarm(x) for x in np.linspace(0,1,len(self.Vg))]
        self.IV.setup_plots()

        for i, Vg in enumerate(self.Vg):
            self.keithley.sweep_V(self.keithley.Vout, Vg, .1, 1)

            self.IV.Ix[:] = np.nan
            self.IV.Vx[:] = np.nan

            self.IV.line = self.IV.ax.plot(self.IV.Ix*1e6, self.IV.Vx*1e3, color=colors[i])[0]
            self.IV.do()

        ## Sweep back to zero at 1V/s
        self.keithley.zero_V(1)
        self.save()

    def setup_keithley(self):
#         self.keithley.zero_V(1) # 1V/s
        self.keithley.source = 'V'
        self.keithley.I_compliance = self.I_compliance
        self.keithley.Vout_range = abs(self.Vg).max()

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

    def __init__(self, instruments = {}):
        super().__init__()
        self._load_instruments(instruments)

        self.Vx = {str(i): np.array([]) for i in range(self.num_lockins)} # one for each voltage channel
        self.Vy = {str(i): np.array([]) for i in range(self.num_lockins)} # use a dictionary to enable saving
        self.Ix = np.array([])
        self.Iy = np.array([])
        self.R = {str(i): np.array([]) for i in range(self.num_lockins)} 
        setattr(self, self.something, np.array([]))

        self.setup_lockins()

    def _load_instruments(self, instruments={}):
        '''
        Loads instruments from a dictionary.
        Specify instruments needed using self.instrument_list.
        This is unique for this class because you can supply up to two
        additional lockins to monitor inputs from.
        '''
        for instrument in self.instrument_list:
            if instrument in instruments:
                setattr(self, instrument, instruments[instrument])
            else:
                setattr(self, instrument, None)
        for name, handle in instruments.items():
            if name[:-1] == 'lockin_V': # e.g. lockin_V2, cut off the "2"
                setattr(self, name, handle)

    @property
    def num_lockins(self):
        num_lockins=0
        for name, handle in self.__dict__.items():
            if name[:-1] == 'lockin_V': # e.g. lockin_V2, cut off the "2"
                num_lockins += 1
        self._num_lockins = num_lockins
        return self._num_lockins

    def do(self, duration=None, delay=1, num_avg = 1, delay_avg = 0, plot=True):
        '''
        Duration and delay both in seconds.
        Use do_measurement() for each resistance measurement.
        '''
        self.do_before(plot)

        if duration is None:
            try:
                while True:
                    self.time = np.append(self.time, time.time()-self.time_start)
                    self.do_measurement(delay, num_avg, delay_avg, plot)
            except KeyboardInterrupt:
                pass
        else:
            while True:
                self.time = np.append(self.time, time.time()-self.time_start)
                self.do_measurement(delay, num_avg, delay_avg, plot)
                if self.time[-1] >= duration:
                    break

        self.do_after()


    def do_before(self, plot=True):
        '''
        Standard things to do before the loop.
        '''
        if plot:
            self.setup_plots()
        self.time_start = time.time()


    def do_after(self):
        '''
        Standard things to do after the loop.
        '''

        # # Make sure arrays in ascending order
        # if getattr(self, self.something)[-1] < getattr(self, self.something)[0]:
        #      getattr(self, self.something) = getattr(self, self.something)[-1]
        #      for j in range(self.num_lockins):
        #         self.R[str(j)] = self.R[str(j)][-1]

        time_end = time.time()
        self.time_elapsed = time_end-self.time_start
        print('Measurement took %.1f minutes' %(self.time_elapsed/60))
        self.save()


    def do_measurement(self, delay=0, num_avg = 1, delay_avg = 0, plot=True):
        '''
        Take a resistance measurement. Usually this will happen in a loop.
        Optional argument to set a delay before the measurement happens.
        plot argument determines whether data is plotted or not
        num_avg is the number of data points to be averaged
        delay_avg is the time delay (seconds) between averages

        Doesn't make a whole lot of sense to average for a measurement vs time, 
        but the averaging could be useful for a subclass.
        '''

        if delay > 0:
            time.sleep(delay)

        self.Ix = np.append(self.Ix, self.lockin_I.X)
        self.Iy = np.append(self.Iy, self.lockin_I.Y)
        for j in range(self.num_lockins):
            J = j # J is int, j is string (for dictionary)
            j = str(j)

            ## Take as many measurements as requested and average them
            vx = 0
            vy = 0
            r = 0
            for i in range(num_avg):
                getattr(self, 'lockin_V%i' %(J+1)).fix_sensitivity() # make sure we aren't overloading or underloading.
                vx += getattr(self, 'lockin_V%i' %(J+1)).X
                vy += getattr(self, 'lockin_V%i' %(J+1)).Y
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
            j = str(j)
            line =  self.ax.plot(getattr(self, self.something), self.R[j])
            self.lines[j] = line[0]

        self.ax.legend(['R%i' %(i+1) for i in range(self.num_lockins)], loc='best')
        self.ax.set_title(self.filename)


class RvsVg(RvsSomething):
    '''
    Monitor R = lockin_V.X/lockin_I.Y from two different lockins.
    Can supply additional lockin_V2, lockin_V3, etc to montior more voltages
    (plotted as resistance)
    '''
    instrument_list = ['keithley', 'lockin_V', 'lockin_I']
    something = 'Vg'
    something_units = 'V'

    def __init__(self, instruments = {}, Vstart = -40, Vend = 40, Vstep=.1, delay=1):
        super().__init__(instruments)

        self.Vstart = Vstart
        self.Vend = Vend
        self.Vstep = Vstep
        self.delay = delay

        self.Vg_values = np.linspace(Vstart, Vend, round(abs(Vend-Vstart)/Vstep)+1)
        self.Ig = np.array([])

        self.setup_keithley()

    def do(self, num_avg = 1, delay_avg = 0, zero=False, plot=True):
        self.do_before(plot)

#         self.keithley.output = 'on' #NO! will cause a spike!

        ## Sweep to Vstart
        self.keithley.sweep_V(self.keithley.V, self.Vstart, .1, 1)

        ## Do the measurement sweep
        for i, Vg in enumerate(self.Vg_values):
            self.Vg = np.append(self.Vg, Vg)
            self.keithley.Vout = Vg
            self.Ig = np.append(self.Ig, self.keithley.I)
            self.do_measurement(self.delay, num_avg, delay_avg, plot)

        ## Sweep back to zero at 1V/s
        if zero:
            self.keithley.zero_V(1)

        self.do_after()


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
        if Vg < CNP:
            n_at_Vg *= -1 # fix the sign if we are below CNP
        self.n = n_at_Vg*(self.Vg-self.Vg[CNP])/(Vg-self.Vg[CNP])


    def find_CNP(self):
        '''
        Finds the index of gate voltage corresponding to charge neutrality point
        '''
        return np.where(self.R[0]==self.R[0].max())[0] # find CNP


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

    def setup_plots(self):
        super().setup_plots()

        self.axIg = self.ax.twinx()
        self.axIg.set_ylabel('Ig (nA)', fontsize=20, color='r', alpha=0.2)

        lineIg = self.axIg.plot(self.Vg, self.Ig*1e9, 'r', alpha=0.2)
        self.lineIg = lineIg[0]


class FourProbeResSweep(Measurement):
    '''class to return four probe resistance using lockin_V and lockin_I'''
    '''set up lock-in before doing this measurement - the setup info is in the transport.py file'''
    '''set up primary measurement parameters:
       voltage bias range - Vbi (an array)'''

    instrument_list = ['lockin_V', 'lockin_I']
    I_compliance = 1e-6 # 1 uA


    def __init__(self, instruments = {},Vbi = 0.1, delay=1):

        super().__init__()
        self._load_instruments(instruments)

        self.Vs = Vbi;
        self.Vx = np.full(self.Vs.shape, np.nan)
        self.Vy = np.full(self.Vs.shape, np.nan)
        self.Ix = np.full(self.Vs.shape, np.nan)
        self.Iy = np.full(self.Vs.shape, np.nan)
        self.R = np.full(self.Vs.shape, np.nan)
        self.R2p = np.full(self.Vs.shape, np.nan)
        self.delay = delay


        self.setup_lockins()

    def do(self):
        if self.fig == None:
            self.setup_plots()
            self.sumR = 0
        ## Sweep to Vstart
        ## self.lockin_V.sweep(self.lockin_V.amplitude, self.Vstart, .01, .1)
        ## Do the measurement sweep
        for i, Vs in enumerate(self.Vs):
            self.lockin_V.amplitude = Vs
            # if self.lockin_V.is_OL() or i==0: # only do auto gain if we're overloading or if it's the first measurement
            #     self.lockin_V.auto_gain()
            # if self.lockin_I.is_OL() or i==0:
            #     self.lockin_I.auto_gain()
            time.sleep(self.delay)




            self.Vx[i] = self.lockin_V.X # unit: V
            self.Vy[i] = self.lockin_V.Y
            self.Ix[i] = self.lockin_I.X # unit: A, read value from SR 830 is A
            self.Iy[i] = self.lockin_I.Y
            self.R[i] = self.Vx[i]/self.Ix[i]
            self.R2p[i] = self.Vs[0]/self.Ix[i]
            self.plot()

            print  ("Applied voltage is %.3e V." % self.lockin_V.amplitude)
            print  ("Current is %.3e A." % self.lockin_I.X)
            print  ("delta voltage is %.3e V." % self.lockin_V.X)
            print  ("Four-probe R: %.3e ohm." % self.R[i])
            print  ("Two-probe R: %.3e ohm.\n" % self.R2p[i])
            self.sumR = self.sumR + self.R[i]

        return (self.sumR)/self.Vs.shape


        # self.save()


    def plot(self):
        super().plot()

        self.line.set_xdata(self.Vx)
        self.line.set_ydata(self.Ix)

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()


    def setup_lockins(self):
        '''if you comment any commands here, then please set them up manually on SR830
        '''
        self.lockin_V.input_mode = 'A-B'
        self.lockin_I.input_mode = 'I (10^8)'

        self.lockin_V.reference = 'internal'
        self.lockin_V.frequency = 67.8
        self.lockin_I.reference = 'external'

        self.lockin_V.time_constant = '300 ms'
        self.lockin_I.time_constant = '300 ms'

        # self set up by lock ins?
        #self.lockin_V.sensitivity = 0.1 # unit: V
        #self.lockin_I.sensitivity = 0.1 # unit: uA

        #self.lockin_V.alarm_off()
        #self.lockin_I.alarm_off()


    def setup_plots(self):
        self.fig, self.ax = plt.subplots(figsize=(5, 5))
        self.ax.set_xlabel('V (V)', fontsize=20)
        self.ax.set_ylabel('I (A)', fontsize=20)
        self.ax.autoscale_view(True,True,True)

        line = self.ax.plot(self.Vx, self.Ix, 'k')
        self.line = line[0]

        self.ax.set_title(self.filename)



class FourProbeRes(Measurement):
    '''class to return four probe resistance using lockin_V and lockin_I'''
    '''do 5 times measurements and return avaraged R '''
    '''set up lock-in before doing this measurement - the setup info is in the transport.py file'''
    '''set up primary measurement parameters:
       voltage bias range - Vbi (an array)'''

    instrument_list = ['lockin_V', 'lockin_I']
    I_compliance = 1e-6 # 1 uA


    def __init__(self, instruments = {},Vbi = 0.1, delay=1):

        super().__init__()
        self._load_instruments(instruments)

        self.Vs = Vbi;
        self.Vx = np.full(5, np.nan)
        self.Vy = np.full(5, np.nan)
        self.Ix = np.full(5, np.nan)
        self.Iy = np.full(5, np.nan)
        self.R = np.full(5, np.nan)
        self.R2p = np.full(5, np.nan)
        self.delay = delay


        self.setup_lockins()

    def do(self):
        if self.fig == None:
            # self.setup_plots()
            self.sumR = 0
        ## Sweep to Vstart
        ## self.lockin_V.sweep(self.lockin_V.amplitude, self.Vstart, .01, .1)
        ## Do the measurement sweep
        for i  in [0,1,2,3,4]:
            self.lockin_V.amplitude = self.Vs
            # if self.lockin_V.is_OL() or i==0: # only do auto gain if we're overloading or if it's the first measurement
            #     self.lockin_V.auto_gain()
            # if self.lockin_I.is_OL() or i==0:
            #     self.lockin_I.auto_gain()
            time.sleep(self.delay)

            self.Vx[i] = self.lockin_V.X # unit: V
            self.Vy[i] = self.lockin_V.Y
            self.Ix[i] = self.lockin_I.X # unit: A, read value from SR 830 is A
            self.Iy[i] = self.lockin_I.Y
            #self.R[i] = self.Vx[i]/self.Ix[i]
            self.R[i] = self.lockin_V.R/self.lockin_I.R
            self.R2p[i] = self.Vs/self.Ix[i]
            # self.plot()

            # print  ("Applied voltage is %.3e V." % self.lockin_V.amplitude)
            # print  ("Current is %.3e A." % self.lockin_I.X)
            # print  ("delta voltage is %.3e V." % self.lockin_V.X)
            print  ("Four-probe R: %.3e ohm." % self.R[i])
            # print  ("Two-probe R: %.3e ohm.\n" % self.R2p[i])
            self.sumR = self.sumR + self.R[i]

        return (self.sumR-self.R[0])/4


        # self.save()


    def plot(self):
        super().plot()

        self.line.set_xdata(self.Vx)
        self.line.set_ydata(self.Ix)

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()


    def setup_lockins(self):
        self.lockin_V.input_mode = 'A-B'
        self.lockin_I.input_mode = 'I (10^8)'

        self.lockin_V.reference = 'internal'
        self.lockin_I.reference = 'external'

        # self.lockin_V.frequency = 67.8
        # self.lockin_V.time_constant = '100 ms'
        # self.lockin_I.time_constant = '100 ms'

        # self set up by lock ins?
        #self.lockin_V.sensitivity = 0.1 # unit: V
        #self.lockin_I.sensitivity = 0.1 # unit: uA

        #self.lockin_V.alarm_off()
        #self.lockin_I.alarm_off()


    def setup_plots(self):
        self.fig, self.ax = plt.subplots(figsize=(5, 5))
        self.ax.set_xlabel('V (V)', fontsize=20)
        self.ax.set_ylabel('I (A)', fontsize=20)
        self.ax.autoscale_view(True,True,True)

        line = self.ax.plot(self.Vx, self.Ix, 'k')
        self.line = line[0]

        self.ax.set_title(self.filename)
