from IPython import display
from scipy.stats import linregress
from scipy.optimize import curve_fit
import time, os
import matplotlib.pyplot as plt
import numpy as np
from ..Utilities import dummy
from ..Instruments import nidaq, preamp, montana
from .save import Measurement

class Touchdown(Measurement):
    def __init__(self, instruments=None, cap_input=None, planescan=False, Vz_max = None):
        self.touchdown = False
        self.V_to_C = 2530e3 # 2530 pF/V * (1e3 fF/pF), calibrated 20160423 by BTS, see ipython notebook
        self.attosteps = 200 #number of attocube steps between sweeps
        self.numfit = 10       # number of points to fit line to while collecting data
        self.numextra = 3

        if instruments:
            self.piezos = instruments['piezos']
            self.atto = instruments['attocube']
            self.lockin = instruments['lockin']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.atto = dummy.Dummy(attocube.Attocube)
            self.lockin = dummy.Dummy(lockin.SR830)
            self.daq = dummy.Dummy(nidaq.NIDAQ)
            self.montana = dummy.Dummy(montana.Montana)

        self.lockin.ch1_daq_input = 'ai%s' %cap_input

        if self.montana.temperature['platform'] < 10:
            self.low_temp = True
        else:
            self.low_temp = False

        self.planescan = planescan

        if Vz_max == None:
            self.Vz_max = self.piezos.Vmax['z']
        else:
            self.Vz_max = Vz_max

        self.configure_attocube()
        self.configure_piezo() # Need this to set up time constant of lockin properly
        self.configure_lockin()

        ## voltage sweep is from -Vz_max to Vz_max, step size determined in configure_piezo. 4 V looks good.
        self.numsteps = int(2*self.Vz_max/self.z_piezo_step)
        self.V = np.linspace(-self.Vz_max, self.Vz_max, self.numsteps)
        self.C = [None]*self.numsteps # Capacitance (fF)
        self.V_td = -1000.0

        self.title = ''
        self.filename = ''
        self.timestamp = ''

    def __getstate__(self):
        self.save_dict = {"timestamp": self.timestamp,
                          "lockin": self.lockin,
                          "atto": self.atto,
                          "piezos": self.piezos,
                          "daq": self.daq,
                          "montana": self.montana,
                          "V": self.V,
                          "C": self.C}
        return self.save_dict

    def check_balance(self, V_unbalanced=2e-6):
        '''
        Checks the balance of the capacitance bridge.
        Voltage must be less than V_unbalanced.
        By default, this is heuristically 2 uV.
        '''
        # Read daq voltage and conver to real lockin voltage
        Vcap = getattr(self.daq, self.lockin.ch1_daq_input)
        Vcap = self.lockin.convert_output(Vcap)

        if Vcap > V_unbalanced:
            inp = input('Check balance of capacitance bridge! Press enter to continue, q to quit')
            if inp == 'q':
                raise Exception('quit by user')

    def do(self):
        '''
        Does the touchdown.
        Timestamp is determined at the beginning of this function.
        '''
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_td'
        self.timestamp = time.strftime("%Y-%m-%d @ %I:%M:%S%p")
        if self.planescan:
            self.filename = self.filename + '_planescan'

        V_td = None
        attosteps = self.attosteps # Number of steps attocubes move if no td.
        if self.planescan:
            attosteps = None # don't move the attocubes if doing a planescan

        ## Loop that does sweeps of z piezo
        ## Z attocube is moved up between iterations
        ## Loop breaks when true touchdown detected.
        while not self.touchdown:
            self.check_balance() # Make sure capacitance bridge is well-balanced

            # Reset capacitance values
            self.C = [None]*self.numsteps # Capacitance (fF)
            self.C0 = None # Cap offset: will take on value of the first point
            self.extra = 0 # Counter to keep track of extra points after touchdown (for fitting the line)

            # Inner loop to sweep z-piezo
            for i in range(self.numsteps):
                time_start = time.time()

                self.piezos.V = {'z': self.V[i]} # Set the current voltage

                ## Get capacitance
                if self.C0 == None:
                    time.sleep(1) # wait for stabilization, was getting weird first values
                Vcap = getattr(self.daq, self.lockin.ch1_daq_input) # Read the voltage from the daq
                Vcap = self.lockin.convert_output(Vcap) # convert to a lockin voltage
                Cap = Vcap*self.V_to_C # convert to true capacitance (fF)
                if self.C0 == None:
                    self.C0 = Cap # Sets the offset datum
                self.C[i] = Cap - self.C0 # remove offset

                if i >= self.numfit: # after a few points, check for touchdown
                    self.check_touchdown(i)
                self.plot_cap(i) # plot the new point

                if self.touchdown:
                    if self.extra < self.numextra: # take three extra points for fit
                        self.extra = self.extra + 1
                        if i == self.numsteps - 1: # special case; there was a bug where if last extra point was last point taken, touchdown would be detected as true
                            self.touchdown = False

                    else:
                        V_td = self.get_touchdown_voltage(i, plot=False)
                        if not self.planescan: # Don't want to move attocubes during planescan
                            # For central touchdown of plane, we want to get the touchdown voltage near the center of the piezo's positive voltage range.
                            if V_td > 0.65*self.Vz_max:
                                self.touchdown = False
                                attosteps = self.attosteps/4 #make sure we don't crash! Don't keep on updating attosteps, otherwise it will go to zero eventually, and that means continuous!!!
                            elif V_td < 0.35*self.Vz_max:
                                self.touchdown = False
                                attosteps = -self.attosteps/4 #move the other direction to bring V_td closer to midway #make sure we don't crash! Don't keep on updating attosteps, otherwise it will go to zero eventually, and that means continuous!!!
                        elif V_td < 0: # This is obviously a false touchdown; for planescan only
                            self.touchdown=False
                        elif self.extra == self.numextra: # last extra step
                            rsquared = self.line_corr_coef(self.V[i-self.numextra:i+1], self.C[i-self.numextra:i+1]) #check fit of last few points
                            if rsquared < 0.90:
                                self.touchdown=False # false touchdown
                        break

            if self.extra != self.numextra: # did not take enough extra steps, TD is at end of range
                self.touchdown = False

            self.piezos.V = {'z': 0} # bring the piezo back to zero

            ## Move the attocubes; either we're too far away for a touchdown or TD voltage not centered
            if not self.planescan: # don't want to move attocubes if in a planescan!
                if not self.touchdown:
                    self.piezos.V = {'z': -self.Vz_max} # before moving attocubes, make sure we're far away from the sample!
                    self.atto.z.step(attosteps)
                    time.sleep(2) # was getting weird capacitance values immediately after moving; wait a bit

        V_td = self.get_touchdown_voltage(i, plot=True) # we didn't plot the intersecting lines before, so let's do that now.

        self.V_td = V_td
        self.save()

        return V_td


    def check_touchdown(self, i):
        '''
        
        '''
        std = np.std(self.C[1:i]) # standard deviation of all points so far
        deviation = abs(self.C[i] - np.mean(self.C[i+1-int(self.numfit):i+1])) # deviation of the ith point from average of last self.numfit points, including i

        if deviation > 4*std and abs(self.C[i]-self.C[i-1]) > 0.4: # Touchdown if further than 4 standard deviations away and capacitance change between last two points above 0.4 fF.. will also account for dip
            self.touchdown = True

    def configure_attocube(self):
        """ Set up z attocube """
        self.atto.z.freq = 200

    def configure_lockin(self):
        """ Set up lockin amplifier for capacitance detection """
        self.lockin.amplitude = 1
        self.lockin.frequency = 24989 # prime number ^_^
        # self.lockin.amplitude = 1
        # self.lockin.frequency = 5003
        self.lockin.set_out(1, 'R') # Possibly X is better?
        self.lockin.set_out(2, 'theta') # not used, but may be good to see
        self.lockin.sensitivity = 50e-6 # set this relatively high to make sure get good reading of lockin.R
        self.lockin.time_constant = 0.100 # we found 100 ms was good on 7/11/2016 (yay slurpees) #1/(5*self.z_piezo_freq) # time constant five times shorter than dwell time for measurement
        self.lockin.reserve = 'Low Noise'
        self.lockin.ac_coupling()
        self.lockin.auto_phase()

    def configure_piezo(self):
        """ Set up z piezo parameters """
        # As of 5/3/2016, only z_piezo_step is used, and the daq sends points one at a time as fast as possible. But this seems fast enough. Might as well just hard-code a time constant.
        self.z_piezo_max_rate = 30 #V/s
        self.z_piezo_step = 2 # 1V at RT, 2V at low T works? # For full 120 V to -120 V sweep, 1 V step is 480 points
        self.z_piezo_freq = self.z_piezo_max_rate/self.z_piezo_step

    def line_fit(self, x, y):
        """ Fits a line given x data, y data. Not sure if curve_fit or linregress is better, or if there is no difference. """
        # m, b, r, _, _ = linregress(x,y)
        # return m,b
        def f(x, m, b):
            return m*x + b
        popt, _ = curve_fit(f, x, y)
        return popt[0], popt[1] # m, b

    def line_corr_coef(self, x,y):
        m, b, r, _, _ = linregress(x,y)
        return r**2

    def get_touchdown_voltage(self, i, plot=False):
        minfit = self.numextra # at minimum, fit 3 points from the end
        j = i-minfit # lower index of touchdown line
        k = j-minfit  # upper index of approach line, a little buffer added to avoid fitting actual touchdown points
        m_td, b_td = self.line_fit(self.V[j:i+1], self.C[j:i+1])
        m_app, b_app = self.line_fit(self.V[int(0.5*k):k+1], self.C[int(0.5*k):k+1]) # fit the last half of points
        V_td = (b_td - b_app)/(m_app - m_td) # intersection of two lines. Remember high school algebra?

        if plot:
            self.line_td.set_xdata(self.V[j-2:i+1]) # 2 is arbitrary, just wanted some more points drawn
            self.line_td.set_ydata(m_td*np.array(self.V[j-2:i+1])+b_td) # 2 is arbitrary, just wanted some more points drawn

            self.line_app.set_xdata(self.V[int(0.5*k):i+1])
            self.line_app.set_ydata(m_app*np.array(self.V[int(0.5*k):i+1])+b_app)

            self.ax.set_title('%s\nTouchdown at %.2f V' %(self.filename, V_td), fontsize=20)
            self.fig.canvas.draw()

        return V_td

    def plot_cap(self, i):
        try:
            self.fig # see if this exists in the namespace
        except:
            self.setup_plot()

        self.line.set_ydata(self.C) #updates plot with new capacitance values

        td_title = 'Touchdown detected!'
        if self.touchdown:
            self.title = td_title
            self.ax.set_title(self.title, fontsize=20)
        else:
            if self.title == td_title:
                self.title = ''
        self.fig.canvas.draw()


    def save(self):
        home = os.path.expanduser("~")
        data_folder = os.path.join(home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'Touchdowns')

        filename = os.path.join(data_folder, self.filename)
        with open(filename+'.csv', 'w') as f:
            f.write('V_td = %f\n' %self.V_td)
            f.write('V_to_C conversion in fF/V = %f\n' %self.V_to_C)
            f.write('Lockin parameters\n')
            f.write(self.lockin.get_all())
            f.write('\n')
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('V (V)\tC (fF)\n')
            for i in range(len(self.V)):
                if self.C[i] != None:
                    f.write('%f' %self.V[i] + ',' + '%f' %self.C[i] + '\n')

        plt.savefig(filename+'.pdf', bbox_inches='tight')

    def setup_plot(self):
        self.fig, self.ax = plt.subplots()
        line = plt.plot(self.V, self.C, 'k.')
        self.line = line[0]

        self.ax.set_title(self.title, fontsize=20)
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')
        plt.xlim(-self.Vz_max, self.Vz_max)
        plt.ylim(-1,10)

        ## Two lines for fitting
        orange = '#F18C22'
        blue = '#47C3D3'

        line_td = plt.plot([], [], blue, lw=2)
        line_app = plt.plot([], [], orange, lw=2)
        self.line_td = line_td[0] # gives us back an array
        self.line_app = line_app[0]
