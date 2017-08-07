from IPython import display
from scipy.optimize import curve_fit
import time, os, matplotlib, matplotlib.pyplot as plt, numpy as np
from ..Utilities.save import Measurement, get_todays_data_dir, get_local_data_path
from ..Utilities import conversions
from ..Utilities.utilities import AttrDict

_Z_PIEZO_STEP = 4  # V piezo
_Z_PIEZO_STEP_SLOW = 4  # V piezo
_CAPACITANCE_THRESHOLD = 1  # fF
_VAR_THRESHOLD = 0.005

# Time UNTIL capacitance bridge is BALanced.  When piezos move, the
# capacitance shifts.  This time is supposed to wait for those shifts to
# die down
_TIME_UNTIL_STABLE = 2 # sec

def piecewise_linear(x, x0, y0, m1, m2):
    '''
    A continuous piecewise linear function.
    nan values in the input array are ignored.

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
    instrument_list = ['lockin_cap', 'atto', 'piezos', 'daq']

    Vtd = None
    touchdown = False

    numsteps = 100
    numfit = 5  # number of points to fit line to while collecting data
    attoshift = 40  # move this number of um if no touchdown detected
    Vz_max = 400
    start_offset = 0

    baseline = 0

    def __init__(self, instruments={}, disable_attocubes=False, Vz_max=None):
        '''
        Approach the sample to the SQUID while recording the capacitance
        of the cantelever in a lockin measurement to detect touchdown.

        Arguments:
        instruments -- dictionary containing instruments for the touchdown.
        disable_attocubes -- if set to True the attocubes will not move.
        Vz_max -- the maximum voltage that can be applied to the Z piezo.

        Required instruments:
        daq, lockin_cap, atto, piezos

        Required daq inputs:
        'cap', 'capx', 'capy', 'theta'

        Required daq ouputs:
        'x', 'y', 'z'
        '''
        super().__init__(instruments=instruments)

        if instruments:
            self.configure_lockin()
        self.z_piezo_step = _Z_PIEZO_STEP
        self.Vz_max = Vz_max
        if Vz_max is None:
            if instruments:
                self.Vz_max = self.piezos.z.Vmax
            else:
                self.Vz_max = 200  # just for the sake of having something

        self._init_arrays()
        self.disable_attocubes = disable_attocubes
        self.error_flag = False


    def _determine_attoshift_to_center(self):
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
        '''
        # Specify a percentage of the piezo range that the
        # touchdown must fall within.
        u = 0.75
        l = 0.25
        if not l * self.Vz_max < self.Vtd < u * self.Vz_max:
            self.touchdown = False
            self._set_title('Found touchdown, centering near %i Vpiezo' %int(
                self.Vz_max/2))
            self.plot()
            self.attoshift = (self.Vtd-self.Vz_max/2)*conversions.Vz_to_um


    def _init_arrays(self):
        '''
        Generate arrays of NaN with the correct length for the touchdown
        '''
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

        self.C0 = None # offset: will take on value of the first point


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
        '''
        if (self.disable_attocubes is False and
            self.touchdown is False and
            self.error_flag is False):
            # Confirm that the attocubes should move
            inp = input(
'[y]: Sweep z piezo down, move attocubes by %s um, and redo touchdown\n \
n: Sweep z piezo down and redo without moving attocubes.\n \
#: Enter custom attocube movement. ' %self.attoshift)
            try:
                float(inp)
                is_number = True
            except:
                is_number = False
            if inp in ('y', '', 'Y') or is_number:
                if is_number:
                    self.attoshift = float(inp)

                # before moving attos, make sure we're far away from the sample!
                self.piezos.z.V = -self.Vz_max

                # make sure we didn't crash
                self.check_balance()

                self.atto.z.move(self.attoshift)

                # wait until capacitance settles
                time.sleep(_TIME_UNTIL_STABLE)

                # While capacitance measurement is overloading:
                while self.daq.inputs['cap'].V > 10:
                    # we probably moved too far
                    self.atto.z.move(-attoshift/2)

                    # wait until capacitance settles
                    time.sleep(_TIME_UNTIL_STABLE)


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
        if self.C0 == None:
            # Wait for the lockin reading to stabalize
            time.sleep(_TIME_UNTIL_STABLE)
        else:
            time.sleep(0.5)

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


    def _set_title(self, title):
        '''
        Sets the plot title to an informative message.
        '''
        if not hasattr(self, 'ax'):
            self.setup_plots()
        self.ax.set_title(title, fontsize=12)
        self.fig.canvas.draw()


    def check_balance(self, V_unbalanced=2e-6):
        '''
        Checks the balance of the capacitance bridge.
        Voltage must be less than V_unbalanced (V).
        '''
        # Read daq voltage and convert to real lockin voltage
        Vcap = self.daq.inputs['cap'].V
        Vcap = self.lockin_cap.convert_output(Vcap)

        if Vcap > V_unbalanced:
            inp = input(
            'Balance capacitance bridge to slightly below balance point. Press enter to continue, q to quit'
            )
            if inp == 'q':
                raise Exception('quit by user')

    def check_touchdown(self):
        '''
        Checks for a touchdown.

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
            var_diff = np.nanvar(self.C) - self.baseline
            if var_diff > _VAR_THRESHOLD:
                return True

            # Check if the capacitance has been high enough
            if self.C[i - self.numfit] > _CAPACITANCE_THRESHOLD:
                # Check that the last numfit points are monotonically increasing
                for j in range(i - self.numfit, i):
                    if self.C[j + 1] - self.C[j] < 0:
                        return False
                # If the for loop passed, then touchdown
                print('level condition')
                return True
        # If we haven't taken enough points
        return False


    def configure_lockin(self):
        '''
        Set up lockin_cap amplifier for a touchdown.
        '''
        self.lockin_cap.amplitude = 3
        self.lockin_cap.frequency = 26759  # prime number
        self.lockin_cap.set_out(1, 'R')
        self.lockin_cap.set_out(2, 'theta')
        self.lockin_cap.sensitivity = 2e-6
        self.lockin_cap.time_constant = 0.300
        self.lockin_cap.reserve = 'Low Noise'
        self.lockin_cap.ac_coupling()
        # self.lockin_cap.auto_phase

    def do(self, start=None):
        '''
        Does the touchdown.
        Timestamp is determined at the beginning of this function.
        Can specify a voltage from which to start the sweep

        Args:
        start (float) -- Starting position (in voltage) of Z peizo.
        '''

        self.Vtd = None
        # If the surface location is unknown, sweep all the way down
        if start is None:
            start = -self.Vz_max

        # Loop that does sweeps of z piezo
        # Z atto is moved up between iterations
        # Loop breaks when true touchdown detected.
        while not self.touchdown:
            # Specify a starting voltage for the Z bender.
            self.piezos.z.V = start

            # Wait for capacitance to settle, then
            # check balance of capacitance bridge
            time.sleep(_TIME_UNTIL_STABLE)

            # Get a baseline measurement of the variance
            self.get_baseline()
            self.check_balance()

            # Reinitialize arrays
            self._init_arrays()

            # Inner loop to sweep z-piezo
            self.do_sweep(start)

            # Move the attocubes
            # Either we're too far away for a touchdown or Vtd not centered
            self._move_attocubes()
            start = -self.Vz_max # start far away next time

            self.piezos.z.V = 0  # bring the piezo back to zero


    def do_sweep(self, start):
        '''
        Inner loop separated to do the piezo sweep

        Args:
        start (float) -- Starting position (in voltage) of Z peizo.
        '''
        for i in np.argwhere(self.V >= start):
            if self.interrupt:
                break

            i = int(i) # i is a list

            # Set the current voltage and wait
            self.piezos.z.V = self.V[i]
            self._record_cap(i)

            # Fill in the missing data points up until the start
            if np.all(np.isnan(self.C)): # first iteration
                self.start_offset = i-1 # how many points we skipped
                self.C[:i] = self.C[i]

            self.plot()

            self.touchdown = self.check_touchdown()

            if self.touchdown:
                # Extract the touchdown voltage.
                self.Vtd = self.get_td_v()

                # If the fit is not "good", flag the touchdown.
                if self.err[0] > 10.:
                    self.error_flag = True

                # Added 11/1/2016 to try to handle exceptions in calculating
                # td voltage
                if self.Vtd == -1:
                    self.touchdown = False
                    continue

                self.plot_td()

                # Don't want to move attos during planescan or bad fit
                if not self.disable_attocubes and not self.error_flag:
                    # Check if touchdown near center of z piezo +V range
                    self._determine_attoshift_to_center()
                    start = -self.Vz_max # start far away next time
                break


    def get_baseline(self):
        '''
        Get a baseline for noise in capacitance measurement.
        '''
        trace = []
        # Compute the variance of 50 points
        for i in range(50):
            # Read the voltage from the daq
            Vcap = self.daq.inputs['cap'].V
            # convert to a real capacitance
            Vcap = self.lockin_cap.convert_output(Vcap)
            Cap = Vcap * conversions.V_to_C
            trace.append(Cap)
            time.sleep(self.lockin_cap.time_constant)
        self.baseline = np.var(trace)


    def get_td_v(self):
        '''
        Determine the touchdown voltage

        Fit a continuous piecewise linear function to the capacitance trace. The
        point where the function transitions between the two lines is recorded
        as the touchdown voltage.

        Variables stored:
        p (array): Best fit parameters x0, y0, m1 and m2 (see piecewise_linear)
        err (array): Error in fitting parameters

        Returns
        Vtd: touchdown voltage
        '''
        C = self.C[~np.isnan(self.C)]
        V = self.V[~np.isnan(self.C)]
        # Try to fit with no initial parameters
        self.p, e = curve_fit(piecewise_linear, V, C)
        if e[0,0] == np.inf:
            Cp = np.gradient(C)
            Cpp = np.gradient(Cp)
            i = np.nanargmax(Cpp)  # spike in second derivative = slope change
            p0 = [self.V[i], 0, 0, 0]  # x0, y0, m1, m2
            self.p, e = curve_fit(piecewise_linear, V, C, p0=p0)
            if e[0,0] == np.inf:
                print('Could not fit touchdown!')
        # Calculate one standard deviation errors in the fit parameters
        self.err = np.sqrt(np.abs(np.diag(e)))
        return self.p[0]


    def gridplot(self, ax):
        '''
        Compact plot of touchdown for use when taking planes
        '''
        C = self.C[~np.isnan(self.C)]
        V = self.V[~np.isnan(self.C)]
        ax.plot(V, C, '.', color='k', markersize=2)
        ax.plot(V, piecewise_linear(V, *self.p))
        ax.axvline(self.p[0], color='r')
        ax.annotate("{0:.2f}".format(self.p[0]), xy=(0.05, 0.90),
                      xycoords="axes fraction", fontsize=8)


    def plot(self):
        super().plot()

        self.plot_threshold()

        # Update plot with new capacitance values
        self.line.set_ydata(self.C)
        self.ax.set_ylim(-0.5, max(np.nanmax(self.C), 1))

        self.fig.tight_layout()
        # Do not pause for inline or notebook backends
        inline = 'module://ipykernel.pylab.backend_inline'
        if matplotlib.get_backend() not in ('nbAgg', inline):
            plt.pause(1e-6)
        self.fig.canvas.draw()


    def plot_threshold(self):
        std_diff = np.sqrt(np.nanvar(self.C) - self.baseline)
        if not hasattr(self, 'line_var1'):
            std = np.sqrt(_VAR_THRESHOLD)
            self.ax.axhline(std, color='C9', linestyle='--')
            self.ax.axhline(-std, color='C9', linestyle='--')
            self.line_var1 = self.ax.axhline(std_diff, color='C8', ls='--')
            self.line_var2 = self.ax.axhline(-std_diff, color='C8', ls='--')
        else:
            self.line_var1.set_ydata(std_diff)
            self.line_var2.set_ydata(-std_diff)


    def plot_td(self):
        self.ax.plot(self.V, piecewise_linear(self.V, *self.p))
        self.ax.axvline(self.p[0], color='r')
        # Plot the touchdown voltage with the 1 standard deviation error
        self._set_title('touchdown: %.2f V, error: %.2f' % (self.Vtd, self.err[0]))
        self.plot()


    def save(self, savefig=True, extras=True):
        '''
        Saves the touchdown object.
        Also saves the figure as a pdf, if wanted.
        '''
        self._save(savefig=savefig, extras=extras)


    def setup_plots(self):
        if not hasattr(self, 'ax'): # for _set_title
            self.fig, self.ax = plt.subplots()
            line = self.ax.plot(self.V, self.C, 'k.')
            self.line = line[0]

            plt.xlabel('Piezo voltage (V)')
            plt.ylabel(r'$C - C_{balance}$ (fF)')

            plt.xlim(self.V.min(), self.V.max())
