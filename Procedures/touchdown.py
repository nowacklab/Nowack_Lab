from IPython import display
from scipy.stats import linregress
from scipy.optimize import curve_fit
from datetime import datetime
import time, os
import matplotlib.pyplot as plt
import numpy as np
from ..Instruments import nidaq, preamp, montana
from ..Utilities.save import Measurement, get_todays_data_path
from ..Utilities import conversions

_home = os.path.expanduser("~")
DATA_FOLDER = get_todays_data_path()

class Touchdown(Measurement):
    Vtd = None
    C = np.array([])
    V = np.array([])
    rs = np.array([])
    numsteps = 100
    numfit = 5       # number of points to fit line to while collecting data
    attoshift = 40 # move 40 um if no touchdown detected
    Vz_max = 400
    touchdown = False
    lines_data = dict(
        V_app = np.array([]),
        C_app = np.array([]),
        V_td = np.array([]),
        C_td = np.array([])
    )

    def __init__(self, instruments=None, cap_input=None, planescan=False, Vz_max = None):

        self.load_instruments(instruments)
        if instruments:
            self.atto.z.freq = 200
            self.configure_lockin(cap_input)

        if planescan:
            self.z_piezo_step = 4
        else:
            self.z_piezo_step = 1 # for update_c, etc. Do a really slow scan.

        self.numsteps = int(2*self.Vz_max/self.z_piezo_step)
        self.V = np.linspace(-self.Vz_max, self.Vz_max, self.numsteps)
        self.C = np.array([np.nan]*self.numsteps) # Capacitance (fF)
        self.rs = np.array([np.nan]*self.numsteps) # correlation coefficients of each fit

        if Vz_max is None and instruments is not None:
            self.Vz_max = self.piezos.z.Vmax
        else:
            self.Vz_max = Vz_max

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

    def do(self):
        '''
        Does the touchdown.
        Timestamp is determined at the beginning of this function.
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
                self.piezos.z.V = Vtd-30 # once it finds touchdown, will try again slower
            elif self.planescan:
                self.piezos.z.V = 0 # planes need to stay above 0 volts anyway
            else:
                self.piezos.z.V = -self.Vz_max # if we have no idea where the surface is.

            ## Check balance of capacitance bridge
            time.sleep(2) # wait for capacitance to stabilize
            self.check_balance()

            ## Reset capacitance and correlation coefficient values
            self.C = np.array([np.nan]*self.numsteps)
            self.rs = np.array([np.nan]*self.numsteps)
            self.C0 = None # offset: will take on value of the first point

            ## Inner loop to sweep z-piezo
            for i in range(self.numsteps):
                # skip a few if doing a slow scan
                if slow_scan:
                    if self.V[i] < Vtd-30:
                        self.C[i] = np.inf
                        continue # skip all of these
                if self.planescan:
                    if self.V[i] < 0:
                        self.C[i] = np.inf
                        continue

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
                if slow_scan or self.planescan:
                    if self.C[0] == np.inf: # set at beginning of loop
                        if self.C[i] not in (np.inf, np.nan):
                            for j in range(len(self.C)):
                                if self.C[j] == np.inf:
                                    self.C[j] = self.C[i] # replace

                self.plot() # plot the new point
                self.touchdown = self.check_touchdown()

                if self.touchdown:
                    self.Vtd = self.get_touchdown_voltage()
                    if not self.planescan: # Don't want to move attocubes during planescan
                        ## Check if touchdown near center of z piezo +V range
                        if Vtd > 0.65*self.Vz_max or Vtd < 0.35*self.Vz_max:
                            self.touchdown = False
                            self.title = 'Found touchdown, centering near %i Vpiezo' %int(self.Vz_max/2)
                            self.plot()
                            self.attoshift = (Vtd-self.Vz_max/2)*conversions.Vpiezo_to_attomicron
                    break # stop approaching

            ## end of inner loop

            ## Move the attocubes; either we're too far away for a touchdown or TD voltage not centered
            if not self.planescan: # don't want to move attocubes if in a planescan!
                if not self.touchdown:
                    self.piezos.z.V = -self.Vz_max # before moving attocubes, make sure we're far away from the sample!
                    self.atto.z.move(self.attoshift)
                    time.sleep(2) # was getting weird capacitance values immediately after moving; wait a bit

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
        if i >= self.numfit:
            i = np.where(np.isnan(self.C))[0][0] # index just above last data point taken
            m,b,r,_,_ = linregress(self.V[i-self.numfit:i], self.C[i-self.numfit:i])
            self.rs[i-1] = r # assigns correlation coefficient for the last data point
            if self.rs[i-3] > 0.95: # make sure there are at least three good Fits
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
        i1 = 0
        i2 = np.where(np.array(self.rs) > 0.95)[0][0] # index where good correlation starts
        i3 = np.where(np.isnan(self.C))[0][0] # finds the location of the first nan (i.e. the last point taken)

        ## Approach curve
        m1, b1, r1, _, _ = linregress(self.V[i1:i2], self.C[i1:i2])

        ## Touchdown curve
        m2, b2, r2, _, _ = linregress(self.V[i2:i3], self.C[i2:i3])

        self.lines_data['V_app'] = self.V[i1:i2]
        self.lines_data['C_app'] = self.C[i1:i2]
        self.lines_data['V_td'] = self.V[i2:i3]
        self.lines_data['C_td'] = self.C[i2:i3]

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
            self.lockin = instruments['cap_lockin']
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
        if not hasattr(self, fig):# see if this exists in the namespace
            self.setup_plot()

        self.line.set_ydata(self.C) #updates plot with new capacitance values

        td_title = 'Touchdown detected!'
        if self.touchdown:
            self.title = td_title
            self.ax.set_title(self.title, fontsize=20)
        else:
            if self.title == td_title:
                self.title = ''

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
        line = plt.plot(self.V, self.C, 'k.')
        self.line = line[0]

        self.ax.set_title(self.title, fontsize=20)
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')

        plt.xlim(-self.Vz_max, self.Vz_max)
        plt.ylim(-1,13)

        ## Two lines for fitting
        orange = '#F18C22'
        blue = '#47C3D3'

        line_td = plt.plot([], [], blue, lw=2)
        line_app = plt.plot([], [], orange, lw=2)
        self.line_td = line_td[0] # gives us back an array
        self.line_app = line_app[0]
