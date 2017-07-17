from IPython import display
from scipy.stats import linregress
from scipy.optimize import curve_fit
from datetime import datetime
import time, os
import matplotlib.pyplot as plt
import numpy as np
from ..Instruments import nidaq, preamp, montana
from ..Utilities.save import Measurement, get_todays_data_dir, get_local_data_path
from ..Utilities import conversions, logging
from ..Utilities.utilities import AttrDict


_Z_PIEZO_STEP = 4  # V piezo
_Z_PIEZO_STEP_SLOW = 4  # V piezo
_CAPACITANCE_THRESHOLD = 1  # fF
_VAR_THRESHOLD = 0.007

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

    lines_data = AttrDict(
        V_app = np.array([]),
        C_app = np.array([]),
        V_td = np.array([]),
        C_td = np.array([])
    )
    good_r_index = None
    title = ''

    numsteps = 100
    numfit = 5  # number of points to fit line to while collecting data
    attoshift = 40  # move this number of um if no touchdown detected
    Vz_max = 400
    start_offset = 0

    def __init__(self, instruments={}, planescan=False, Vz_max=None):
        '''
        Approach the sample to the SQUID while recording the capacitance
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
            self.atto.z.freq = 200
            self.configure_lockin()

        self.z_piezo_step = _Z_PIEZO_STEP

        self.Vz_max = Vz_max
        if Vz_max is None:
            if instruments:
                self.Vz_max = self.piezos.z.Vmax
            else:
                self.Vz_max = 200  # just for the sake of having something

        self._init_arrays()
        self.planescan = planescan

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
        Voltage must be less than V_unbalanced (V).
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
            if np.var(self.C[~np.isnan(self.C)]) > _VAR_THRESHOLD:
                return True
            # Check if the capacitance has been high enough (above 3 fF)
            if self.C[i - self.numfit] > _CAPACITANCE_THRESHOLD:
                # Check that the last numfit points are monotonically increasing
                for j in range(i - self.numfit, i):
                    if self.C[j + 1] - self.C[j] < 0:
                        return False
                # If the for loop passed, then touchdown
                return True
        # If we haven't taken enough points
        return False

    def configure_lockin(self):
        '''Set up lockin_cap amplifier for a touchdown.'''
        self.lockin_cap.amplitude = 1
        self.lockin_cap.frequency = 26759  # prime number
        self.lockin_cap.set_out(1, 'R')
        self.lockin_cap.set_out(2, 'theta')
        self.lockin_cap.sensitivity = 20e-6
        self.lockin_cap.time_constant = 0.300
        self.lockin_cap.reserve = 'Low Noise'
        self.lockin_cap.ac_coupling()
        self.lockin_cap.auto_phase

    def do(self, start=None, confirmation=False):
        '''
        Does the touchdown.
        Timestamp is determined at the beginning of this function.
        Can specify a voltage from which to start the sweep

        Args:
        start (float) -- Starting position (in voltage) of Z peizo.
        confirmation (bool) -- If True, the user is asked to determine the
        touchdown voltage from the capacitance vs. position plot.
        '''

        self.Vtd = None
        slow_scan = False
        td_array = []

        # Loop that does sweeps of z piezo
        # Z atto is moved up between iterations
        # Loop breaks when true touchdown detected.
        while not self.touchdown:
            # Determine where to start sweeping
            if slow_scan:
                start = self.Vtd - 50
                self.z_piezo_step = _Z_PIEZO_STEP_SLOW
                self._init_arrays()
                self.setup_plots()

            # Specify a starting voltage for the Z bender.
            # If the surface location is unknown, sweep all the way down
            if start is not None:
                self.piezos.z.V = start
            else:
                self.piezos.z.V = -self.Vz_max

            # Check balance of capacitance bridge
            time.sleep(2)  # wait for capacitance to stabilize
            self.check_balance()

            # Reset capacitance and correlation coefficient values
            self.C = np.array([np.nan] * self.numsteps)
            self.rs = np.array([np.nan] * self.numsteps)
            self.Cx = np.array([np.nan] * self.numsteps)
            self.Cy = np.array([np.nan] * self.numsteps)
            self.theta = np.array([np.nan] * self.numsteps)
            self.C0 = None  # offset: will take on value of the first point
            self.lines_data = AttrDict(
                V_app = np.array([]),
                C_app = np.array([]),
                V_td = np.array([]),
                C_td = np.array([])
            )
            # Inner loop to sweep z-piezo
            for i in range(self.numsteps):
                if self.interrupt:
                    break
                # Determine starting voltage
                if start is not None:
                    if self.V[i] < start:
                        self.C[i] = np.inf
                        # In the end, this is how many points we skipped
                        self.start_offset = i
                        continue  # skip all of these

                # Set the current voltage and wait
                self.piezos.z.V = self.V[i]  # Set the current voltage
                if slow_scan:
                    time.sleep(2)  # wait a long time

                # Get capacitance
                if self.C0 == None:
                    # Wait for the lockin reading to stabalize
                    time.sleep(2)
                # Read the voltage from the daq
                Vcap = self.daq.inputs['cap'].V
                # convert to a real capacitance
                Vcap = self.lockin_cap.convert_output(Vcap)
                Cap = Vcap * conversions.V_to_C
                if self.C0 == None:
                    self.C0 = Cap  # Sets the offset datum
                self.C[i] = Cap - self.C0  # remove offset
                # Record the X, Y and theta voltages
                self.Cx[i] = self.daq.inputs['capx'].V
                self.Cy[i] = self.daq.inputs['capy'].V
                self.theta[i] = self.daq.inputs['theta'].V

                # gotta cheat and take care of the infs by making them the same
                # as the first real data point... this is because we skipped them
                if start is not None:
                    if self.C[0] == np.inf:  # set at beginning of loop
                        if self.C[i] not in (np.inf, np.nan):
                            for j in range(len(self.C)):
                                if self.C[j] == np.inf:
                                    self.C[j] = self.C[i]  # replace

                self.plot()  # plot the new point
                self.touchdown = self.check_touchdown()

                if self.touchdown:
                    # Extract the touchdown voltage.
                    self.Vtd = self.get_td_v()

                    td_array.append([self.atto.z.pos, self.Vtd])

                    # Added 11/1/2016 to try to handle exceptions in calculating
                    # td voltage
                    if self.Vtd == -1:
                        self.touchdown = False
                        continue

                    self.plot()

                    # Don't want to move attos during planescan
                    if not self.planescan:
                        # Specify a percentage of the peizo range that the
                        # touchdown must fall within.
                        if slow_scan:
                            u = 0.55
                            l = 0.35
                        else:
                            u = 0.85  # touchdown is at a higher voltage for a not-slow scan
                            l = 0.45
                        if self.Vtd > u * self.Vz_max or self.Vtd < l * self.Vz_max:
                            self.touchdown = False
                            start = -self.Vz_max  # because we don't know where the td will be
                            self.title = 'Found touchdown, centering near %i Vpiezo' % int(self.Vz_max / 2)
                            self.plot()
                            self.attoshift = (self.Vtd - self.Vz_max / 2) * conversions.Vz_to_um
                            self.lines_data['V_app'] = []
                            self.lines_data['C_app'] = []
                            self.lines_data['V_td'] = []
                            self.lines_data['C_td'] = []
                            if slow_scan:
                                slow_scan = False
                                self.z_piezo_step = _Z_PIEZO_STEP
                                self._init_arrays()
                                self.setup_plots()

                    break  # stop approaching

            # end of inner loop

            # Move the attocubes
            if not self.planescan:
                if not self.touchdown:
                    # Sweep the pizeos away from the sample before
                    self.piezos.z.V = -self.Vz_max
                    start = -self.Vz_max  # we should start here next time
                    self.check_balance()  # make sure we didn't crash
                    self.atto.z.move(self.attoshift)
                    # Let lockin measurement stabalize
                    time.sleep(2)

                    # If the lockin is overloading after moving then we
                    # probably crashed - back off with attocubes and
                    # check again
                    while self.daq.inputs['cap'].V > 10:  # overloading
                        self.atto.z.move(-self.attoshift / 2)
                        time.sleep(2)

            # Do a slow scan next
            if self.touchdown:  # if this is a true touchdown
                if not self.planescan:  # but not a planescan
                    if not slow_scan:
                        # slow_scan = True
                        # self.touchdown = False
                        slow_scan = False
                        self.touchdown = True
        # End of outer loop

        # Ask the user to confirm the touchdown voltage
        if confirmation:
            self.touchdown = input('Touchdown voltage: ')

        self.piezos.z.V = 0  # bring the piezo back to zero


    def get_td_v(self):
        '''
        Determine the touchdown voltage

        Fit a continuous piecewise linear function to the capacitance trace. The
        point where the function transitions between the two lines is recorded
        as the touchdown voltage.

        Returns
        Vtd: touchdown voltage
        '''
        C = self.C[~np.isnan(self.C)]
        V = self.V[~np.isnan(self.C)]
        self.p, e = curve_fit(piecewise_linear, V, C)
        self.err = np.sqrt(np.diag(e))
        return self.p[0]


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

        if self.touchdown:
            self.ax.plot(self.V, piecewise_linear(self.V, *self.p))
            self.ax.axvline(self.p[0], color='r')
            self.title = 'touchdown: %.2f V, error: %.2f' % (self.Vtd, self.err[0])

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def save(self, savefig=True):
        '''
        Saves the touchdown object.
        Also saves the figure as a pdf, if wanted.
        '''

        filename_in_extras = os.path.join(get_local_data_path(),
                                          get_todays_data_dir(),
                                          'extras',
                                          self.filename)
        self._save(filename_in_extras, savefig)

    def setup_plots(self):
        display.clear_output(wait=True)
        self.fig, self.ax = plt.subplots()
        line = self.ax.plot(self.V, self.C, 'k.')
        self.line = line[0]

        self.ax.set_title(self.title, fontsize=12)
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')

        plt.xlim(self.V.min(), self.V.max())

        # Two lines for fitting
        line_td = self.ax.plot([], [], 'C0', lw=2)
        line_app = self.ax.plot([], [], 'C1', lw=2)
        self.line_td = line_td[0]  # plot gives us back an array
        self.line_app = line_app[0]

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
