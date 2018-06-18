from IPython import display
from scipy.stats import linregress
from scipy.optimize import curve_fit
from datetime import datetime
import time
import os
import matplotlib.pyplot as plt
import numpy as np
from ..Instruments import nidaq, preamp, montana
from ..Utilities.save import Measurement, get_todays_data_dir, get_local_data_path
from ..Utilities import conversions, logging
from ..Utilities.utilities import AttrDict

# TODO:
#   - add timestamp to all saved plots
#
#


_Z_PIEZO_STEP = 4  # V piezo
_Z_PIEZO_STEP_SLOW = 4  # V piezo
_CAPACITANCE_THRESHOLD = 1  # fF
_ATTO_TOWARDS_SAMPLE = -1

def piecewise_linear(x, x0, y0, m1, m2):
        '''A continuous piecewise linear function

        Args
        x (array-like): the domain of the function.
        x0 (float): the x-coordinate where the function changes slope.
        y0 (float): the y-coordinage where the function changes slope.
        m1 (float): the slope of the function for x < x0.
        m2 (float): the slope of the function for x > x0.

        Returns
        '''
        return np.piecewise(x,
                            [x < x0],
                            [lambda x: m1*x + y0 - m1*x0,
                             lambda x: m2*x + y0 - m2*x0])


class Touchdown(Measurement):
    _daq_inputs = ['cap', 'capx', 'capy', 'theta']
    instrument_list = ['lockin_cap', 'atto', 'piezos', 'daq', 'montana']

    Vtd = None
    touchdown = False
    C = np.array([])
    V = np.array([])
    rs = np.array([])
    C0 = 0
    _VAR_THRESHOLD = 0.01

    # Time to wait before reading lockin to determine
    # capacitance.  Time > 5*time constant for 6dB

    # Time UNTIL capacitance bridge is BALanced.  When piezos move, the
    # capacitance shifts.  This time is supposed to wait for those shifts to
    # die down
    _T_UNTIL_BAL = 2;

    # Time UNTIL capacitance bridge is BALanced for the SLOW_scan.
    # when scanning slowly (after an initial touchdown was found), we wait
    # this long until we take a point, to ensure the any shifts in capacitance
    # dies out
    _T_UNTIL_BAL_SLOW = 2;

    lines_data = AttrDict(
        V_app=np.array([]),
        C_app=np.array([]),
        V_td=np.array([]),
        C_td=np.array([])
    )
    good_r_index = None
    title = ''

    numsteps = 100
    numfit = 5       # number of points to fit line to while collecting data
    attoshift = _ATTO_TOWARDS_SAMPLE*40 # move 20 um if no touchdown detected
    Vz_max = 400
    start_offset = 0

    def __init__(self, instruments={}, planescan=False, Vz_max=None, runonce=False):
        '''Approach the sample to the SQUID while recording the capacitance 
        of the cantelever in a lockin measurement to detect touchdown.

        Arguments:
        instruments -- dictionary containing instruments for the touchdown.
        planescan -- if set to True the attocubes will not move.
        Vz_max -- the maximum voltage that can be applied to the Z piezo.

        Required instruments:
        daq, lockin_cap, attocubes, piezos, montana

        Required daq inputs:
        'cap', 'capx', 'capy' 'theta'

        Required daq ouputs:
        'x', 'y', 'z'
        '''
        super().__init__(instruments=instruments)

        if instruments:
            #self.atto.z.freq = 200
            #self.configure_lockin()
            pass
        self.z_piezo_step = _Z_PIEZO_STEP
        self.Vz_max = Vz_max
        if Vz_max is None:
            if instruments:
                self.Vz_max = self.piezos.z.Vmax
            else:
                self.Vz_max = 200  # just for the sake of having something

        self._init_arrays()
        self.planescan = planescan
        self.flagged = False
        self.runonce=runonce

    def _init_arrays(self):
        ''' Generate arrays of NaN with the correct length for the touchdown'''
        self.numsteps = int(2 * self.Vz_max / self.z_piezo_step)
        self.V = np.linspace(-self.Vz_max, self.Vz_max, self.numsteps)

        # Capacitance (fF) - read as "R" from the lockin
        self.C = np.array([np.nan] * self.numsteps)

        # Also record the X, Y and theta measurements on the lockin
        self.Cx = np.array([np.nan] * self.numsteps)
        self.Cy = np.array([np.nan] * self.numsteps)
        self.theta = np.array([np.nan] * self.numsteps)

        # Correlation coefficients of each fit
        self.rs = np.array([np.nan] * self.numsteps)

    def check_balance(self, V_unbalanced=2e-6):
        '''
        Checks the balance of the capacitance bridge.
        Voltage must be less than V_unbalanced.
        '''
        # Read daq voltage and convert to real lockin voltage
        Vcap = self.daq.inputs['cap'].V
        Vcap = self.lockin_cap.convert_output(Vcap)

        if Vcap > V_unbalanced:
            inp = input(
                'Balance capacitance bridge. Press enter to continue, q to quit'
            )
            if inp == 'q':
                raise Exception('quit by user')

    def check_touchdown(self):
        '''Checks for a touchdown.

        If the last numfit points are monotically increasing and the 
        capacitance increases by an ammount larger than 
        _CAPACITANCE_THRESHOLD over the last numfit points then a 
        touchdown is detected

        Returns:
        bool : True when touchdown is detected
        '''
        # i is the index of last data point taken
        i = np.where(~np.isnan(self.C))[0][-1]  
        # Check that enough data has been collected to do a linear fit
        if i > self.numfit + self.start_offset:
            # Check if the variance of the capacitance trace is high enough.
            if np.var(self.C[~np.isnan(self.C)]) > self._VAR_THRESHOLD:
                return True
            # Check if the capacitance has been high enough (above 3 fF)
            if self.C[i - self.numfit] > _CAPACITANCE_THRESHOLD:
                # Check that the last numfit points are monotonically increasing
                for j in range(i - self.numfit, i):
                    if self.C[j + 1] - self.C[j] < 0:
                        return False
                # If the for loop passed, then touchdown
                print("level condition")
                return True
        # If we haven't taken enough points
        return False            

    def configure_lockin(self):
        '''Set up lockin_cap amplifier for a touchdown.'''
        self.lockin_cap.amplitude = 1
        self.lockin_cap.frequency = 26759  # prime number
        self.lockin_cap.set_out(1, 'R')
        self.lockin_cap.set_out(2, 'theta')
        #self.lockin_cap.sensitivity = 20e-6
        #self.lockin_cap.time_constant = 0.300
        self.lockin_cap.reserve = 'Low Noise'
        self.lockin_cap.ac_coupling()
        self.lockin_cap.auto_phase

    def _reset_cap_and_corr(self):
        '''
        Helper function for do():
        Copied directly from do() at 2017-05-30 by dhl88
        to make code prettier

        Reset capacitance and correlation coefficient values
        '''
        self.C = np.array([np.nan] * self.numsteps)
        self.rs = np.array([np.nan] * self.numsteps)
        self.Cx = np.array([np.nan] * self.numsteps)
        self.Cy = np.array([np.nan] * self.numsteps)
        self.theta = np.array([np.nan] * self.numsteps)
        self.C0 = None # offset: will take on value of the first point
        self.lines_data = AttrDict(
            V_app=np.array([]),
            C_app=np.array([]),
            V_td=np.array([]),
            C_td=np.array([])
        )


    def _record_cap(self, i):
        '''
        Helper function for do():
        Copied directly from do() at 2017-05-30 by dhl88
        to make code prettier

        1) Wait for capacitance to stabilize
        2) read with daq from lockin
        3) convert V to C
        4) set capacitance offset (using Cap if not the first point)
        5) record X,Y,theta capacitance

        '''
        # Get capacitance
        if self.C0 == None:
            # Wait for the lockin reading to stabalize
            time.sleep(self._T_UNTIL_BAL)

        # Read the voltage from the daq
        Vcap = self.daq.inputs['cap'].V

        # convert to a real capacitance
        Vcap = self.lockin_cap.convert_output(Vcap)
        Cap = Vcap * conversions.V_to_C

        if self.C0 == None:
            self.C0 = Cap # Sets the offset datum
        self.C[i] = Cap - self.C0 # remove offset

        # Record the X, Y and theta voltages
        self.Cx[i] = self.daq.inputs['capx'].V
        self.Cy[i] = self.daq.inputs['capy'].V
        self.theta[i] = self.daq.inputs['theta'].V

    def _replace_inf(self, i):
        '''
        Helper Function for do():
        Copied directly from do() at 2017-05-30 by dhl88
        to make code prettier

        When taking the slow touchdowns, we start at some piezo voltage.
        The data for this touchdown at lower piezo voltages must be replaced
        with something.  We choose ... dhl88 is not sure why we do this each
        time (for every i) but is leaving it alone because it works...
        '''
        # gotta cheat and take care of the infs by making them the same
        # as the first real data point... this is because we skipped them
        if self.C[0] == np.inf: # set at beginning of loop
            if self.C[i] not in (np.inf, np.nan):
                for j in range(len(self.C)):
                    if self.C[j] == np.inf:
                        self.C[j] = self.C[i] # replace

    def _cntr_td_w_atto(self, slow_scan, Vtd, start):
        '''
        Helper function for do():
        Copied directly from do() at 2017-05-30 by dhl88
        to make code prettier

        Determines the piezo voltage to set before doing another touchdown.
        The goal is to move the attocubes into a position where the z bender
        can easily bring the sample and squid into contact.

        If the touchdown voltage is within the bender range (set by
        constants inside this function), then nothing is done.  Else,
        sets start to the lowest possible value and sets the self.attoshift
        to the best guess as to where the scanner should be.

        Returns [slow_scan, start]
        '''
        # Specify a percentage of the peizo range that the
        # touchdown must fall within.
        if slow_scan:
            u = 0.55 # percentages of the total voltage range to aim touchdown to be within
            l = 0.35
        else:
            u = 0.85 # touchdown is at a higher voltage for a not-slow scan
            l = 0.45
        if Vtd > u * self.Vz_max or Vtd < l * self.Vz_max:
            self.touchdown = False
            start = -self.Vz_max # because we don't know where the td will be
            self.title = 'Found touchdown, centering near %i Vpiezo' %int(
                self.Vz_max/2)
            self.plot()
            self.attoshift = (
                _ATTO_TOWARDS_SAMPLE * (Vtd-self.Vz_max/2)*conversions.Vz_to_um
            )
            self.lines_data['V_app'] = []
            self.lines_data['C_app'] = []
            self.lines_data['V_td'] = []
            self.lines_data['C_td'] = []
            if slow_scan:
                slow_scan = False
                self.z_piezo_step = _Z_PIEZO_STEP
                self._init_arrays()
                self.setup_plots()
        return [slow_scan, start]

    def _move_attocubes(self):
        '''
        Helper function for do():
        Copied directly from do() at 2017-05-30 by dhl88
        to make code prettier

        1) moves piezos to the lowest possible value
        2) sets start to that value (-self.Vz_max)
        3) check balance, make sure we didn't crash
        4) move attocubes to the position self.attoshift
        5) sleep until capacitance settles
        6) if capacitance is overloading, backoff

        returns start = -self.Vz_max
        '''
        # before moving attos, make sure we're far away from the sample!
        self.piezos.z.V = -self.Vz_max

        # we should start here next time
        start = -self.Vz_max

        # make sure we didn't crash
        self.check_balance()

        msg = input(
                "Ok to move {0} ums? q to quit, m to move automatically".format(
                    self.attoshift));
        if (msg is 'q'):
            raise KeyboardInterrupt;
        if (msg is 'm'):
            self.atto.z.move(self.attoshift)
        else:
            pass

        # wait until capacitance settles
        time.sleep(self._T_UNTIL_BAL)

        # While capacitance measurement is overloading:
        while self.daq.inputs['cap'].V > 10:
            # we probably moved too far
            move = -_ATTO_TOWARDS_SAMPLE*self.attoshift/2
            msg = input(
                    "Ok to move {0} um? q to quit, m to move automatically".format(move));
            if (msg is 'q'):
                raise KeyboardInterrupt;
            if (msg is 'm'):
                self.atto.z.move(move)
            else:
                pass

            # wait until capacitance settles
            time.sleep(self._T_UNTIL_BAL)

        return start;
    def do(self, start=None, user=False):
        '''
        Does the touchdown.
        Timestamp is determined at the beginning of this function.
        Can specify a voltage from which to start the sweep

        Args:
        start (float) -- Starting position (in voltage) of Z peizo.
        user (bool) -- If True, the user is asked to determine the
        touchdown voltage from the capacitance vs. position plot.
        '''

        Vtd = None
        slow_scan = False
        # td_array = [] # looks like we never used this...

        # start = {None          if you are planescanning /
        #                        if attocubes never moved
        #          some voltage  if you have previously scanned and are
        #                           scanning slowly from a set point


        # Loop that does sweeps of z piezo
        # Z atto is moved up between iterations
        # Loop breaks when true touchdown detected.
        while not self.touchdown:
            # Determine where to start sweeping
            if slow_scan:
                start = Vtd - 50
                self.z_piezo_step = _Z_PIEZO_STEP_SLOW
                self._init_arrays()
                self.setup_plots()

            # Specify a starting voltage for the Z bender.
            # If the surface location is unknown, sweep all the way down
            if start is not None:
                self.piezos.z.V = start
            else:
                self.piezos.z.V = -self.Vz_max
            # Wait for capacitance to settle, then
            # check balance of capacitance bridge
            time.sleep(self._T_UNTIL_BAL)
            self.check_balance()

            # Reset capacitance and correlation coefficient values
            self._reset_cap_and_corr()

            # Inner loop to sweep z-piezo
            for i in range(self.numsteps):
                if self.interrupt:
                    break

                # Determine starting voltage
                if (start is not None and self.V[i] < start):
                    self.C[i] = np.inf
                    # In the end, this is how many points we skipped
                    self.start_offset = i 
                    continue # skip all of these

                # Set the current voltage and wait
                self.piezos.z.V = self.V[i] # Set the current voltage

                # If a slow_scan, wait between points
                if slow_scan:
                    time.sleep(self._T_UNTIL_BAL_SLOW)

                self._record_cap(i);

                # gotta cheat and take care of the infs by making them the same
                # as the first real data point... this is because we skipped them
                if start is not None:
                    self._replace_inf(i);

                self.plot() # plot the new point

                self.touchdown = self.check_touchdown()
                
                if self.touchdown:
                    # Extract the touchdown voltage.
                    self.p, self.e = self.get_td_v()
                    Vtd = self.p[0]
                    self.err = np.sqrt(np.diag(self.e))

                    # Check if the fit is "good" if not, flag the touchdown.
                    if self.err[0] > 4.:
                        self.flagged = True
                    
                    self.ax.plot(self.V, piecewise_linear(self.V, *self.p))
                    self.ax.axvline(self.p[0], color='r')

                    # Added 11/1/2016 to try to handle exceptions in calculating
                    # td voltage
                    if Vtd == -1:
                        self.touchdown = False
                        continue

                    self.title = 'touchdown: %.2f V, error: %.2f' % (Vtd, self.err[0])
                    self.plot()

                    # Don't want to move attos during planescan
                    if not self.planescan:
                        # Check if touchdown near center of z piezo +V range
                        [slow_scan, start] = self._cntr_td_w_atto(slow_scan,
                                                                  Vtd, start);

                    break  # stop approaching

            # end of inner loop (sweep z piezo)

            if (self.runonce==True):
                break


            # Move the attos;
            # either we're too far away for a touchdown or TD voltage not centered
            if (self.planescan is False and self.touchdown is False):
                # don't want to move attos if in a planescan!
                start = self._move_attocubes();

            # Do a slow scan next
            if (self.touchdown is True and  # this is a true touchdown
                self.planescan is False and # this is not a planescan
                slow_scan      is False ):  # we have not done a slow scan
                slow_scan = True
                self.touchdown = False

        # Ask the user to confirm the touchdown voltage
        if user:
            self.touchdown = input("Touchdown voltage: ")

        self.piezos.z.V = 0  # bring the piezo back to zero

        self.Vtd = Vtd

    
    def get_td_v(self):
        '''Determine the touchdown voltage
        
        Fit a continuous piecewise linear function to the capacitance trace. The
        point where the function transitions between the two lines is recorded
        as the touchdown voltage.

        Returns
        p (array): Best fit parameters x0, y0, m1 and m2 (see piecewise_linear)
        '''
        C = self.C[~np.isnan(self.C)]
        V = self.V[~np.isnan(self.C)]
        p, e = curve_fit(piecewise_linear, V, C)
        return p, e

    def get_touchdown_voltage(self):
        '''
        Determines the touchdown voltage.

        1. Finds the best fit for the touchdown curve fitting from i to 
        the last point.
        2. Finds the best fit for the approach curve fitting from j to 
        the best i. Considers minimizing slope in determining good 
        approach fit.
        3. Returns the intersection of these two lines.
        '''
        try:
            # Find the location of the first nan (i.e. the last point taken)
            i3 = np.where(np.isnan(self.C))[0][0]
            V = self.V[:i3]
            C = self.C[:i3]

            # How many lines to try to fit
            # last number is minimum number of points to fit
            N2 = len(C) + 1 - 5
            r2 = np.array([np.nan] * N2)  # correlation coefficients go here

            # Loop over fits of the touchdown curve
            start = 1
            for i in range(start, N2):
                _, _, r2[i], _, _ = linregress(V[i:], C[i:])

            # Find touchdown index and perform final fit
            # this is where touchdown probably is,
            # gave it a couple of extra points; it always seemed to need them
            i = np.nanargmax(r2) - 2

            # Figure out how many lines to try to fit for approach curve
            N1 = i + 1 - 3  # last number is minimum number of points to fit for the approach curve
            r1 = np.array([np.nan] * N1)  # correlation coefficients go here
            m1 = np.array([np.nan] * N1)  # slopes go here

            # Approach curve
            k = i - 3  # fit the approach curve ending this 2 points away from the touchdown curve
            N1 = N1 - 3  # must adjust N1 by this same amount
            for j in range(start, N1):
                m1[j], b1, r1[j], _, _ = linregress(V[j:k], C[j:k])

            # Determine best approach curve
            # Two weight factors: how much we care that it's a good fit
            # and how much we care that the slope is near zero.
            minimize_this = (1 - r1) * 1 + abs(m1) * 100
            j = np.nanargmin(minimize_this)

            # Recalculate slopes and intercepts
            m2, b2, r2, _, _ = linregress(V[i:], C[i:])
            m1, b1, r1, _, _ = linregress(V[j:k], C[j:k])

            self.lines_data['V_app'] = V[j:k]
            self.lines_data['C_app'] = m1 * V[j:k] + b1
            self.lines_data['V_td'] = V[i:]
            self.lines_data['C_td'] = m2 * V[i:] + b2

            Vtd = -(b2 - b1) / (m2 - m1)  # intersection point of two lines

            self.title = '%s\nTouchdown at %.2f V' % (self.filename, Vtd)

            return Vtd
        except Exception as e:
            print('Error getting touchdown voltage. Continuing...')
            print('Exception details: ', e)
            time.sleep(3)
            return -1

    def plot(self):
        super().plot()

        # Update plot with new capacitance values
        self.line.set_ydata(self.C)
        self.ax.set_ylim(-0.5, max(np.nanmax(self.C), 1))

        self.line_app.set_xdata(self.lines_data['V_app'])
        self.line_app.set_ydata(self.lines_data['C_app'])

        self.line_td.set_xdata(self.lines_data['V_td'])
        self.line_td.set_ydata(self.lines_data['C_td'])

        self.ax.set_title(self.title, fontsize=12)

        #self.fig.tight_layout()
        plt.pause(0.01) #  helps with not responding plots outside notebooks
        self.fig.canvas.draw()

    def save(self, savefig=True, **kwargs):
        '''
        Saves the touchdown object.
        Also saves the figure as a pdf, if wanted.
        '''

        filename_in_extras = os.path.join(get_local_data_path(),
                                          get_todays_data_dir(),
                                          'extras',
                                          self.filename)
        self._save(filename_in_extras, savefig, **kwargs)

    def setup_plots(self):
        display.clear_output(wait=True)
        self.fig, self.ax = plt.subplots()
        line = self.ax.plot(self.V, self.C, 'k.')
        self.line = line[0]

        self.ax.set_title(self.title, fontsize=12)
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')

        plt.xlim(self.V.min(), self.V.max())

        self.ax.annotate("X:{0:2.2f}, Y:{1:2.2f}".format(self.piezos.x.V, self.piezos.y.V), 
                xy=(0.05, 0.05),
                  xycoords="axes fraction", fontsize=8)

        # Two lines for fitting
        orange = '#F18C22'
        blue = '#47C3D3'

        line_td = self.ax.plot([], [], blue, lw=2)
        line_app = self.ax.plot([], [], orange, lw=2)
        self.line_td = line_td[0]  # plot gives us back an array
        self.line_app = line_app[0]


    def gridplot(self, axes):
        '''Compact plot of touchdown for use when taking planes'''
        C = self.C[~np.isnan(self.C)]
        V = self.V[~np.isnan(self.C)]
        axes.plot(V, C, '.', color='k', markersize=2)

        if self.touchdown:
            axes.plot(V, piecewise_linear(V, *self.p))
            axes.axvline(self.p[0], color='r')
            axes.annotate("{0:.2f}".format(self.p[0]), xy=(0.05, 0.90),
                      xycoords="axes fraction", fontsize=8)
        
