from IPython import display
from scipy.stats import linregress
from scipy.optimize import curve_fit
from datetime import datetime
import time, os
import matplotlib.pyplot as plt
import numpy as np
from ..Instruments import nidaq, preamp, montana
from ..Utilities.save import Measurement, get_todays_data_path
from ..Utilities import conversions, logging

_home = os.path.expanduser("~")
DATA_FOLDER = get_todays_data_path()

class Touchdown(Measurement):
    Vtd = None
    C = np.array([])
    V = np.array([])
    rs = np.array([])
    numsteps = 100
    numfit = 5       # number of points to fit line to while collecting data
    attoshift = 20 # move 20 um if no touchdown detected
    Vz_max = 400
    touchdown = False
    lines_data = dict(
        V_app = np.array([]),
        C_app = np.array([]),
        V_td = np.array([]),
        C_td = np.array([])
    )
    good_r_index = None
    start_offset = 0
    title = ''

    def __init__(self, instruments=None, cap_input=None, planescan=False, Vz_max = None):

        self.load_instruments(instruments)
        if instruments:
            self.atto.z.freq = 200
            self.configure_lockin(cap_input)

        if planescan:
            self.z_piezo_step = 8 #may be able to go to 4
        else:
            self.z_piezo_step = 1 # for update_c, etc. Do a really slow scan.

        self.Vz_max = Vz_max
        self.numsteps = int(2*self.Vz_max/self.z_piezo_step)
        self.V = np.linspace(-self.Vz_max, self.Vz_max, self.numsteps)
        self.C = np.array([np.nan]*self.numsteps) # Capacitance (fF)
        self.rs = np.array([np.nan]*self.numsteps) # correlation coefficients of each fit

        if self.Vz_max is None and instruments is not None:
            self.Vz_max = self.piezos.z.Vmax

        self.planescan = planescan
        self.title = ''
        self.filename = ''
        self.timestamp = ''

    def __getstate__(self):
        super().__getstate__() # from Measurement superclass,
                               # need this in every getstate to get save_dict
        self.save_dict.update({"timestamp": self.timestamp,
                          "lockin": self.lockin,
                          "atto": self.atto,
                          "piezos": self.piezos,
                          "daq": self.daq,
                          "montana": self.montana,
                          "V": self.V,
                          "C": self.C
                      })
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

    def do(self, start=None):
        '''
        Does the touchdown.
        Timestamp is determined at the beginning of this function.
        Can specify a voltage from which to start the sweep
        '''
        append = 'td'
        if self.planescan:
            append += '_planescan'
        super().make_timestamp_and_filename(append)

        Vtd = None
        slow_scan = False

        ## Loop that does sweeps of z piezo
        ## Z attocube is moved up between iterations
        ## Loop breaks when true touchdown detected.
        while not self.touchdown:
            ## Determine where to start sweeping
            if slow_scan:
                start = Vtd-30 # once it finds touchdown, will try again slower
            if start is not None:
                self.piezos.z.V = start
            else:
                self.piezos.z.V = -self.Vz_max # if we have no idea where the surface is.


            ## Check balance of capacitance bridge
            time.sleep(2) # wait for capacitance to stabilize
            self.check_balance()

            ## Reset capacitance and correlation coefficient values
            self.C = np.array([np.nan]*self.numsteps)
            self.rs = np.array([np.nan]*self.numsteps)
            self.C0 = None # offset: will take on value of the first point
            self.lines_data = dict(
                V_app = np.array([]),
                C_app = np.array([]),
                V_td = np.array([]),
                C_td = np.array([])
            )
            ## Inner loop to sweep z-piezo
            for i in range(self.numsteps):
                # Determine starting voltage
                if start is not None:
                    if self.V[i] < start:
                        self.C[i] = np.inf
                        self.start_offset = i # in the end, this is how many points we skipped
                        continue # skip all of these

                ## Set the current voltage and wait
                self.piezos.z.V = self.V[i] # Set the current voltage
                if slow_scan:
                    time.sleep(2) # wait a long time

                ## Get capacitance
                if self.C0 == None:
                    time.sleep(2) # wait for stabilization, was getting weird first values
                Vcap = getattr(self.daq, self.lockin.ch1_daq_input) # Read the voltage from the daq
                Vcap = self.lockin.convert_output(Vcap) # convert to a lockin voltage
                Cap = Vcap*conversions.V_to_C # convert to true capacitance (fF)
                if self.C0 == None:
                    self.C0 = Cap # Sets the offset datum
                self.C[i] = Cap - self.C0 # remove offset

                ## gotta cheat and take care of the infs by making them the same
                ## as the first real data point... this is because we skipped them
                if start is not None:
                    if self.C[0] == np.inf: # set at beginning of loop
                        if self.C[i] not in (np.inf, np.nan):
                            for j in range(len(self.C)):
                                if self.C[j] == np.inf:
                                    self.C[j] = self.C[i] # replace

                self.plot() # plot the new point
                self.touchdown = self.check_touchdown()

                if self.touchdown:
                    Vtd = self.get_touchdown_voltage()
                    self.title = 'Touchdown detected at %.2f V!' %Vtd
                    logging.log(self.title)
                    self.plot()

                    if not self.planescan: # Don't want to move attocubes during planescan
                        ## Check if touchdown near center of z piezo +V range
                        if Vtd > 0.65*self.Vz_max or Vtd < 0.35*self.Vz_max:
                            self.touchdown = False
                            slow_scan = False
                            start = -self.Vz_max # because we don't know where the td will be
                            self.title = 'Found touchdown, centering near %i Vpiezo' %int(self.Vz_max/2)
                            self.plot()
                            self.attoshift = (Vtd-self.Vz_max/2)*conversions.Vpiezo_to_attomicron/4 # quarter of how far it should move if conversion is exact (accounts for when the conversion is not exact)
                            self.lines_data['V_app'] = []
                            self.lines_data['C_app'] = []
                            self.lines_data['V_td'] = []
                            self.lines_data['C_td'] = []

                    break # stop approaching

            ## end of inner loop

            ## Move the attocubes; either we're too far away for a touchdown or TD voltage not centered
            if not self.planescan: # don't want to move attocubes if in a planescan!
                if not self.touchdown:
                    self.piezos.z.V = -self.Vz_max # before moving attocubes, make sure we're far away from the sample!
                    start = -self.Vz_max # we should start here next time
                    self.atto.z.move(self.attoshift)
                    time.sleep(2) # was getting weird capacitance values immediately after moving; wait a bit
                    while getattr(self.daq, self.lockin.ch1_daq_input) > 10: # overloading
                        self.atto.z.move(-self.attoshift/2) # we probably moved too far
                        time.sleep(2)

            ## Do a slow scan next
            if self.touchdown: # if this is a true touchdown
                if not self.planescan: # but not a planescan
                    if not slow_scan: # and if we haven't done a slow scan yet
                        slow_scan = True
                        self.touchdown = False

        ## end of outer loop

        self.piezos.z.V = 0 # bring the piezo back to zero

        self.Vtd = Vtd
        self.save()

        return Vtd


    def check_touchdown(self, corr_coeff_thresh=0.95):
        '''
        Checks for touchdown.
        Fits a line including the last five data points taken.
        If the correlation coefficient of the last three fits is better than
        corr_coeff_thresh, returns True. Otherwise, we have not touched down.
        '''
        i = np.where(~np.isnan(self.C))[0][-1] # index of last data point taken
        if i > self.numfit + self.start_offset:
            m,b,r,_,_ = linregress(self.V[i-self.numfit:i], self.C[i-self.numfit:i])
            self.rs[i] = r # assigns correlation coefficient for the last data point
            for j in range(4):
                if self.rs[i-j] < 0.95: #if any of the last four fits are bad...
                    return False # no touchdown
                self.good_r_index = i-j # where good correlation starts
            if self.C[i] != np.nanmax(self.C):
                return False #the last point taken should be the maximum
            return True
        return False


    def configure_lockin(self, cap_input=None):
        '''
        Set up lockin amplifier for a touchdown.
        '''
        self.lockin.ch1_daq_input = 'ai%s' %cap_input
        self.lockin.amplitude = 1
        self.lockin.frequency = 24989 # prime number ^_^
        self.lockin.set_out(1, 'R') # Possibly X is better?
        self.lockin.set_out(2, 'theta') # not used, but may be good to see
        self.lockin.sensitivity = 10e-6
        self.lockin.time_constant = 0.100
        self.lockin.reserve = 'Low Noise'
        self.lockin.ac_coupling()
        self.lockin.auto_phase()


    def get_touchdown_voltage(self):
        i2 = self.good_r_index - self.numfit # start of well-correlated data
        i3 = np.where(np.isnan(self.C))[0][0] # finds the location of the first nan (i.e. the last point taken)
        i1 = max(0, i2 - self.numfit*5) # fit approach curve from further back, but don't go to negative values!

        ## Approach curve
        m1, b1, r1, _, _ = linregress(self.V[i1:i2], self.C[i1:i2])

        ## Touchdown curve
        m2, b2, r2, _, _ = linregress(self.V[i2:i3], self.C[i2:i3])

        self.lines_data['V_app'] = self.V[i1:i2]
        self.lines_data['C_app'] = m1*self.V[i1:i2] + b1
        self.lines_data['V_td'] = self.V[i2:i3]
        self.lines_data['C_td'] = m2*self.V[i2:i3] + b2

        Vtd = -(b2 - b1)/(m2 - m1) # intersection point of two lines

        self.title = '%s\nTouchdown at %.2f V' %(self.filename, Vtd)

        return Vtd


    @staticmethod
    def load(json_file, instruments=None):
        '''
        Load a touchdown with or without any instruments.
        '''
        unwanted_keys = ['daq', 'lockin', 'atto', 'piezos']
        obj = Measurement.load(json_file, unwanted_keys)
        obj.load_instruments(instruments)
        return obj


    def load_instruments(self, instruments):
        if instruments:
            self.piezos = instruments['piezos']
            self.atto = instruments['attocube']
            self.lockin = instruments['lockin_cap']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
        else:
            self.piezos = None
            self.atto = None
            self.lockin = None
            self.daq = None
            self.montana = None
            print('Instruments not loaded... can only plot!')


    def plot(self):
        if not hasattr(self, 'fig'):# see if this exists in the namespace
            self.setup_plot()

        self.line.set_ydata(self.C) #updates plot with new capacitance values
        self.ax.set_ylim(top=max(np.nanmax(self.C), 5))

        self.line_app.set_xdata(self.lines_data['V_app'])
        self.line_app.set_ydata(self.lines_data['C_app'])

        self.line_td.set_xdata(self.lines_data['V_td'])
        self.line_td.set_ydata(self.lines_data['C_td'])

        self.ax.set_title(self.title, fontsize=20)
        self.fig.canvas.draw()


    def save(self, savefig=True):
        '''
        Saves the planefit object to json in .../TeamData/Montana/Planes/
        Also saves the figure as a pdf, if wanted.
        '''

        self.tojson(DATA_FOLDER, self.filename)

        if savefig:
            self.fig.savefig(os.path.join(DATA_FOLDER, self.filename+'.pdf'), bbox_inches='tight')


    def setup_plot(self):
        self.fig, self.ax = plt.subplots()
        line = self.ax.plot(self.V, self.C, 'k.')
        self.line = line[0]

        self.ax.set_title(self.title, fontsize=20)
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')

        plt.xlim(self.V.min(), self.V.max())
        plt.ylim(-1,5)

        ## Two lines for fitting
        orange = '#F18C22'
        blue = '#47C3D3'

        line_td = self.ax.plot([], [], blue, lw=2)
        line_app = self.ax.plot([], [], orange, lw=2)
        self.line_td = line_td[0] # plot gives us back an array
        self.line_app = line_app[0]
