import numpy as np
import matplotlib.pyplot as plt
import os, time
from datetime import datetime

# from importlib import reload
# from scipy.interpolate import UnivariateSpline
# from ..Utilities.plotting import plot_mpl
# from mpl_toolkits.axes_grid1 import make_axes_locatable
# from scipy.signal import savgol_filter

# Nowack_Lab imports
from ..Utilities import dataset
from ..Instruments.VNA import VNA8722ES
from ..Instruments.nidaq import NIDAQ
from ..Instruments.keithley import Keithley2400

from IPython.display import clear_output


class RFTakeSpectrum:
    """
    Take a single spectrum (gain/attenuation as function of frequency)
    """
    def __init__(self, v_freqmin, v_freqmax, v_power, v_avg_factor, v_numpoints,
                 filepath, v_smoothing_state=0, v_smoothing_factor=1,
                 notes="No notes", plot=False, network_param='S21'):

        # Set object variables
        self.v_freqmax = v_freqmax
        self.v_freqmin = v_freqmin
        self.v_power = v_power
        self.v_avg_factor = v_avg_factor

        self.filepath = filepath
        self.v_smoothing_state = v_smoothing_state
        self.v_smoothing_factor = v_smoothing_factor
        self.notes = notes
        self.plot = plot
        self.v_networkparam = network_param

        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        self.v_numpoints = v_numpoints

        if v_numpoints not in self.valid_numpoints:
            index = (np.abs(self.valid_numpoints - v_numpoints)).argmin()
            closest_valid_numpoint = self.valid_numpoints[index]
            print("%f is not a valid point number. Setting to %d instead." %(v_numpoints, closest_valid_numpoint))
            self.v_numpoints = closest_valid_numpoint
        else:
            self.v_numpoints = v_numpoints

        self.v1 = VNA8722ES(16)  # initialize VNA (Instrument object)

    def do(self):
        """
        Run measurement
        """
        # Set up VNA settings
        self.v1.networkparam = self.v_networkparam  # Set to measure forward transmission
        self.v1.power = self.v_power
        self.v1.powerstate = 1  # turn vna source power on
        self.v1.averaging_state = 1  # Turn averaging on
        self.v1.averaging_factor = self.v_avg_factor
        self.v1.freqmax = self.v_freqmax
        self.v1.freqmin = self.v_freqmin
        self.v1.sweepmode = "LIN"
        self.v1.numpoints = self.v_numpoints  # set num freq pnts for VNA
        self.v1.smoothing_state = self.v_smoothing_state  # turn smoothing on
        self.v1.smoothing_factor = self.v_smoothing_factor

        # creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        # initialize empty array to store data in TODO: change from empty to NAN?
        # re_im = np.empty((2, int(self.v1.numpoints)))
        time.sleep(5)
        power_range = self.v1.ask('POWR?')
        vna_power = self.v1.ask('POWE?')
        print(power_range)
        print(vna_power)
        re_im = self.v1.save_re_im()  # get real and imaginary parts
        self.save_data(timestamp, re_im)  # save data to h5

        self.v1.powerstate = 0  # turn off VNA source power

        # plot TODO: only plots foward attenuation atm
        if self.plot:
            RFSweepCurrent.plotdB1D(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")

    def save_data(self, timestamp, re_im):
        name = timestamp + '_rf_sweep'
        path = os.path.join(self.filepath, name + '.hdf5')
        info = dataset.Dataset(path)
        info.append(path + '/freqmin', self.v_freqmin)
        info.append(path + '/freqmax', self.v_freqmax)
        info.append(path + '/power', self.v_power)
        info.append(path + '/avg_factor', self.v_avg_factor)
        info.append(path + '/numpoints', self.v_numpoints)
        info.append(path + '/smoothing_state', self.v_smoothing_state)
        info.append(path + '/smoothing_factor', self.v_smoothing_factor)
        info.append(path + '/re_im/data', re_im)
        info.append(path + '/re_im/description', "shape [Data, Re Im]")
        info.append(path + '/notes', self.notes)


class PowerFrequencySweep:
    """ Heatmap: power on one axis, frequency on other axis, gain/db is heat/color
    E.g. will use for copper powder filter characterization"""
    def __init__(self, v_freqmin, v_freqmax, v_powermin, v_powermax, v_powersteps, filepath, v_avg_factor=3,
                 v_numpoints=1601, v_smoothing_state=0, v_smoothing_factor=1, notes="No notes", network_param='S21',
                 plot=True):
        self.v_freqmin = v_freqmin
        self.v_freqmax = v_freqmax
        self.v_powermin = v_powermin
        self.v_powermax = v_powermax
        self.v_powersteps = v_powersteps
        self.filepath = filepath
        self.v_avg_factor = v_avg_factor
        self.v_smoothing_state = v_smoothing_state
        self.v_smoothing_factor = v_smoothing_factor
        self.notes = notes
        self.v_network_param = network_param
        self.plot = plot

        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        self.v_numpoints = v_numpoints

        self.fig = None
        self.ax = None

        if v_numpoints not in self.valid_numpoints:
            index = (np.abs(self.valid_numpoints - v_numpoints)).argmin()
            closest_valid_numpoint = self.valid_numpoints[index]
            print("%f is not a valid point number. Setting to %d instead." % (v_numpoints, closest_valid_numpoint))
            self.v_numpoints = closest_valid_numpoint
        else:
            self.v_numpoints = v_numpoints

        self.v1 = VNA8722ES(16)  # initialize VNA (Instrument object)

    def do(self):
        """
        Run measurement
        """
        # Set up VNA settings
        self.v1.networkparam = self.v_network_param  # Set to measure forward transmission
        self.v1.power = self.v_powermin
        self.v1.powerstate = 1  # turn vna source power on
        self.v1.averaging_state = 1  # Turn averaging on
        self.v1.averaging_factor = self.v_avg_factor
        self.v1.maxfreq = self.v_freqmax
        self.v1.minfreq = self.v_freqmin
        self.v1.sweepmode = "LIN"
        self.v1.numpoints = self.v_numpoints  # set num freq pnts for VNA
        self.v1.smoothing_state = self.v_smoothing_state  # turn smoothing on
        self.v1.smoothing_factor = self.v_smoothing_factor

        # creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        re_im = np.empty((self.v_powersteps, 2, self.v_numpoints))

        powers_list = np.linspace(self.v_powermin, self.v_powermax, self.v_powersteps)
        for index in range(self.v_powersteps):
            self.v1.power = powers_list[index]
            re_im[index] = self.v1.save_re_im()

        self.v1.powerstate = 0

        self.save_data(timestamp, re_im)

        if self.plot:
            PowerFrequencySweep.plotdB(self.filepath + "\\" + timestamp + "_PowerFrequencySweep.hdf5")

    def save_data(self, timestamp, re_im):
        name = timestamp + '_PowerFrequencySweep'
        path = os.path.join(self.filepath, name + '.hdf5')
        print("Saving to path: " + path)
        info = dataset.Dataset(path)
        info.append(path + '/freqmin', self.v_freqmin)
        info.append(path + '/freqmax', self.v_freqmax)
        info.append(path + '/powermin', self.v_powermin)
        info.append(path + '/powermax', self.v_powermax)
        info.append(path + '/powersteps', self.v_powersteps)
        info.append(path + '/avg_factor', self.v_avg_factor)
        info.append(path + '/numpoints', self.v_numpoints)
        info.append(path + '/smoothing_state', self.v_smoothing_state)
        info.append(path + '/smoothing_factor', self.v_smoothing_factor)
        info.append(path + '/re_im/data', re_im)
        info.append(path + '/re_im/description', "shape [Current, Data, Re Im]")
        info.append(path + '/notes', self.notes)
        info.append(path + '/network_param', self.v_network_param)

    @staticmethod
    def plotdB(filename):
        print("test abacasdfadsf")
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        power = np.linspace(data.get(filename + '/powermin'),
                                  data.get(filename + '/powermax'),
                                  data.get(filename + '/powersteps'))
        freq = np.linspace(data.get(filename + '/freqmin') / 1e9,
                           data.get(filename + '/freqmax') / 1e9,
                           data.get(filename + '/numpoints'))
        x, y = np.meshgrid(freq, power)
        dB = PowerFrequencySweep.dB_data(filename)
        im = ax.pcolor(x, y, dB, cmap="viridis", vmin=-100, vmax=-10)
        cbar = fig.colorbar(im)
        ax.set_ylabel('VNA power (dBm)')
        ax.set_xlabel('VNA frequency (GHz)')
        ax.set_title(filename + "\nNotes: " +
                         str(data.get(filename + '/notes')))

        cbar.set_label('Gain [dB]')
        graph_path = filename.replace(".hdf5", "db.png")
        fig.savefig(graph_path)

    @staticmethod
    def dB_data(filename):
        data = dataset.Dataset(filename)
        re_im_info = data.get(filename + '/re_im/data')
        attenuation = np.empty((data.get(filename + '/powersteps'),
                                int(data.get(filename + '/numpoints'))))
        n = 0
        for array in re_im_info:
            attenuation[n] = VNA8722ES.Re_Im_to_dB(array)
            n += 1
        return attenuation


class RFSweepCurrentDAQ:
    """Class for sweeping current with DAQ (and bias resistor) and recording
    data from the VNA8722ES at each current step"""

    """Initiates a RF_sweep_current_daq object with parameters about the sweep"""

    def __init__(self, Rbias, Ibias_start, Ibias_stop, Ibias_steps, v_freqmin, v_freqmax,
                 v_power, filepath, DAQ_range=1, v_avg_factor=2, v_numpoints=1601, v_smoothing_state=0,
                 v_smoothing_factor=1, notes="No notes", hysteresis=False, plot=True):
        print("Make sure bias resistor is attached (don't blow up SQUID)")
        # set object vars
        self.Rbias = Rbias  # ohms
        # ensure that current values not dangerously large
        if max(abs(Ibias_start), abs(Ibias_stop)) > 1:
            print("Current values too high: changing to zero")
            self.Ibias_start = 0
            self.Ibias_stop = 0
            self.Ibias_steps = 1
        else:
            self.Ibias_start = Ibias_start  # amps
            self.Ibias_stop = Ibias_stop  # amps
            self.Ibias_steps = Ibias_steps
        self.v_freqmin = v_freqmin  # Hz
        self.v_freqmax = v_freqmax  # Hz
        self.v_power = v_power  # dBm
        self.filepath = filepath
        self.v_avg_factor = v_avg_factor
        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]

        if v_numpoints not in self.valid_numpoints:
            index = (np.abs(self.valid_numpoints - v_numpoints)).argmin()
            closest_valid_numpoint = self.valid_numpoints[index]
            print("%f is not a valid point number. Setting to %d instead." % (v_numpoints, closest_valid_numpoint))
            self.v_numpoints = closest_valid_numpoint
        else:
            self.v_numpoints = v_numpoints
        self.v_numpoints = v_numpoints
        self.v_smoothing_state = v_smoothing_state
        self.v_smoothing_factor = v_smoothing_factor
        self.notes = notes
        self.hysteresis = hysteresis
        self.plot = plot

        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        self.daq = NIDAQ()
        self.vna = VNA8722ES(16)

        if v_numpoints not in self.valid_numpoints:
            index = (np.abs(self.valid_numpoints - v_numpoints)).argmin()
            closest_valid_numpoint = self.valid_numpoints[index]
            print("%f is not a valid point number. Setting to %d instead." % (v_numpoints, closest_valid_numpoint))
            self.v_numpoints = closest_valid_numpoint
        else:
            self.v_numpoints = v_numpoints

    def do(self):
        """Run measurement"""
        # first find the necessary voltage values
        Ibias_range = np.linspace(self.Ibias_start, self.Ibias_stop, self.Ibias_steps)
        Vbias_range = self.Rbias * Ibias_range  # These are the voltage settings to use
        """TODO finish stuff here; should use np.linspace"""

        # set up DAQ "current source" settings
        self.daq.ao0.V = self.Ibias_start*self.Rbias

        # Set up VNA settings
        self.vna.networkparam = 'S21'  # Set to measure forward transmission
        self.vna.power = self.v_power
        self.vna.powerstate = 1  # turn vna source power on
        self.vna.averaging_state = 1  # Turn averaging on
        self.vna.averaging_factor = self.v_avg_factor
        self.vna.freqmax = self.v_freqmax
        self.vna.freqmin = self.v_freqmin
        self.vna.sweepmode = "LIN"
        self.vna.numpoints = self.v_numpoints  # set num freq pnts for VNA
        self.vna.smoothing_state = self.v_smoothing_state  # turn smoothing on
        self.vna.smoothing_factor = self.v_smoothing_factor

        time.sleep(3)  # ensure that VNA has enough time to change settings

        # print estimated_runtime
        sleep_length = float(self.vna.ask('SWET?'))*(self.vna.averaging_factor+3)
        estimated_runtime = sleep_length*self.Ibias_steps
        print('Minimum estimated runtime: ' + str(int(estimated_runtime/60)) + ' minutes')

        I_stepsize = (float(self.Ibias_stop-self.Ibias_start))/self.Ibias_steps
        print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')
        V_stepsize = self.Rbias*I_stepsize

        # creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        # initialize empty array to store data in TODO: change from empty to NAN?
        re_im = np.empty((self.Ibias_steps, 2, self.v_numpoints))
        if self.hysteresis:
            re_im_rev = np.empty((self.Ibias_steps, 2, self.v_numpoints))

        # sweep forward in current
        index = 0
        for step in range(0, self.Ibias_steps):
            if step % 10 == 0:
                # clear_output()
                print("Current source step #" + str(step + 1) + " out of " + str(self.Ibias_steps))
            self.daq.ao0.V += V_stepsize  # increment voltage/current
            self.vna.averaging_restart()
            re_im[index] = self.vna.save_re_im()
            index += 1

        # sweep backward in current
        if self.hysteresis:
            for step in range(0, self.Ibias_steps):
                if step % 10 == 0:
                    clear_output()
                    print("Current source step #" + str(step + 1) + " out of " + str(self.Ibias_steps))
                self.daq.ao0.V += -V_stepsize
                self.vna.averaging_restart()
                re_im_rev[index] = self.vna.save_re_im()
                index += 1
            self.save_data(timestamp, re_im, re_im_rev=re_im_rev)
        else:
            self.save_data(timestamp, re_im)

        self.daq.ao0 = 0  # set daq voltage to 0
        self.vna.powerstate = 0  # turn off VNA source power

        if self.plot:
            RFSweepCurrentDAQ.plotdB(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")
            RFSweepCurrentDAQ.plot_phase(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")
            if self.hysteresis:
                RFSweepCurrentDAQ.plotdB(self.filepath+"\\" + timestamp + "_rf_sweep.hdf5")
                RFSweepCurrentDAQ.plot_phase(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")

    @staticmethod
    def plotdB(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart') * 1000,
                                  data.get(filename + '/Istop') * 1000,
                                  data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop') * 1000,
                                  data.get(filename + '/Istart') * 1000,
                                  data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin') / 1e9,
                           data.get(filename + '/freqmax') / 1e9,
                           data.get(filename + '/numpoints'))
        y, x = np.meshgrid(freq, current)
        dB = RFSweepCurrentDAQ.dB_data(filename, rev=rev)
        im = ax.pcolor(x, y, dB, cmap="viridis")
        cbar = fig.colorbar(im)
        ax.set_xlabel('field coil current (mA)')
        ax.set_ylabel('frequency (GHz)')
        if not rev:
            ax.set_title(filename + "\nPower from VNA = " +
                         str(data.get(filename + '/power')) + " dBm")
        else:
            ax.set_title(filename + "\nSweep back in current" +
                         "\nPower from VNA = " + str(data.get(filename + '/power'))
                         + " dBm")
        cbar.set_label('Gain [dB]')
        if not rev:
            graph_path = filename.replace(".hdf5", "db.png")
        else:
            graph_path = filename.replace(".hdf5", "db_rev.png")
        fig.savefig(graph_path)

    @staticmethod
    def dB_data(filename, rev=False):
        data = dataset.Dataset(filename)
        if not rev:
            re_im_info = data.get(filename + '/re_im/data')
        else:
            re_im_info = data.get(filename + '/re_im_rev/data')
        attenuation = np.empty((data.get(filename + '/Isteps'),
                                int(data.get(filename + '/numpoints'))))
        n = 0
        for array in re_im_info:
            attenuation[n] = VNA8722ES.Re_Im_to_dB(array)
            n += 1
        return attenuation

    @staticmethod
    def phase_data(filename, rev=False):
        data = dataset.Dataset(filename)
        if not rev:
            re_im_info = data.get(filename + '/re_im/data')
        else:
            re_im_info = data.get(filename + '/re_im_rev/data')
        phase = np.empty((data.get(filename + '/Isteps'),
                          int(data.get(filename + '/numpoints'))))
        n = 0
        for array in re_im_info:
            phase[n] = VNA8722ES.Re_Im_to_phase(array)
            n += 1
        return phase

    @staticmethod
    def plotdB1D(filename):
        """Plot and save single VNA freq sweep. x-axis is frequency, y-axis is dB"""
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        freq = np.linspace(data.get(filename + '/freqmin') / 1e9,
                           data.get(filename + '/freqmax') / 1e9,
                           data.get(filename + '/numpoints'))
        dB = VNA8722ES.Re_Im_to_dB(data.get(filename + '/re_im/data'))
        im = ax.plot(freq, dB[0])
        ax.set_ylabel('attenuation (dB)')
        ax.set_xlabel('frequency (GHz)')
        ax.set_title(filename + "\nPower from VNA = " +
                     str(data.get(filename + '/power')) + " dBm" + "\n" + data.get(filename + '/notes'))
        graph_path = filename.replace(".hdf5", "db.png")
        fig.savefig(graph_path)

    @staticmethod
    def plot_phase(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart') * 1000,
                                  data.get(filename + '/Istop') * 1000,
                                  data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop') * 1000,
                                  data.get(filename + '/Istart') * 1000,
                                  data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin') / 1e9,
                           data.get(filename + '/freqmax') / 1e9,
                           data.get(filename + '/numpoints'))
        y, x = np.meshgrid(freq, current)
        phase = RFSweepCurrentDAQ.phase_data(filename, rev=rev)
        im = ax.pcolor(x, y, phase, cmap="viridis")
        cbar = fig.colorbar(im)
        ax.set_xlabel('field coil current (mA)')
        ax.set_ylabel('frequency (GHz)')
        if not rev:
            ax.set_title(filename + "\nPower from VNA = " +
                         str(data.get(filename + '/power')) + " dBm")
        else:
            ax.set_title(filename + "\nSweep back in current" +
                         "\nPower from VNA = " + str(data.get(filename + '/power'))
                         + " dBm")
        cbar.set_label('Phase [degrees]')
        if not rev:
            graph_path = filename.replace(".hdf5", "phase.png")
        else:
            graph_path = filename.replace(".hdf5", "phase_rev.png")
        fig.savefig(graph_path)

    def save_data(self, timestamp, re_im, re_im_rev = None):
        name = timestamp + '_rf_sweep'
        path = os.path.join(self.filepath, name + '.hdf5')
        info = dataset.Dataset(path)
        info.append(path + '/Istart', self.Ibias_start)
        info.append(path + '/Istop', self.Ibias_stop)
        info.append(path + '/Isteps', self.Ibias_steps)
        info.append(path + '/freqmin', self.v_freqmin)
        info.append(path + '/freqmax', self.v_freqmax)
        info.append(path + '/power', self.v_power)
        info.append(path + '/avg_factor', self.v_avg_factor)
        info.append(path + '/numpoints', self.v_numpoints)
        info.append(path + '/smoothing_state', self.v_smoothing_state)
        info.append(path + '/smoothing_factor', self.v_smoothing_factor)
        info.append(path + '/re_im/data', re_im)
        info.append(path + '/re_im/description', "shape [Current, Data, Re Im]")
        info.append(path + '/re_im_rev/data', re_im_rev)
        info.append(path + '/re_im_rev/description', "shape [Current, Data, Re Im]")
        info.append(path + '/notes', self.notes)
        info.append(path + '/hysteresis', self.hysteresis)


class RFSweepCurrentDAQREV:
    """Class for sweeping current with DAQ (and bias resistor) and recording
    data from the VNA8722ES at each current step
    MEASURES S12 INSTEAD OF S21 - be careful! Because VNA not quite working other way"""

    """Initiates a RF_sweep_current_daq object with parameters about the sweep"""

    def __init__(self, Rbias, Ibias_start, Ibias_stop, Ibias_steps, v_freqmin, v_freqmax,
                 v_power, filepath, DAQ_range=1, v_avg_factor=2, v_numpoints=1601, v_smoothing_state=0,
                 v_smoothing_factor=1, notes="No notes", hysteresis=False, plot=True):
        print("Make sure bias resistor is attached (don't blow up SQUID)")
        # set object vars
        self.Rbias = Rbias  # ohms
        # ensure that current values not dangerously large
        if max(abs(Ibias_start), abs(Ibias_stop)) > 1:
            print("Current values too high: changing to zero")
            self.Ibias_start = 0
            self.Ibias_stop = 0
            self.Ibias_steps = 1
        else:
            self.Ibias_start = Ibias_start  # amps
            self.Ibias_stop = Ibias_stop  # amps
            self.Ibias_steps = Ibias_steps
        self.v_freqmin = v_freqmin  # Hz
        self.v_freqmax = v_freqmax  # Hz
        self.v_power = v_power  # dBm
        self.filepath = filepath
        self.v_avg_factor = v_avg_factor
        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]

        if v_numpoints not in self.valid_numpoints:
            index = (np.abs(self.valid_numpoints - v_numpoints)).argmin()
            closest_valid_numpoint = self.valid_numpoints[index]
            print("%f is not a valid point number. Setting to %d instead." % (v_numpoints, closest_valid_numpoint))
            self.v_numpoints = closest_valid_numpoint
        else:
            self.v_numpoints = v_numpoints
        self.v_numpoints = v_numpoints
        self.v_smoothing_state = v_smoothing_state
        self.v_smoothing_factor = v_smoothing_factor
        self.notes = notes
        self.hysteresis = hysteresis
        self.plot = plot

        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        self.daq = NIDAQ()
        self.vna = VNA8722ES(16)

        if v_numpoints not in self.valid_numpoints:
            index = (np.abs(self.valid_numpoints - v_numpoints)).argmin()
            closest_valid_numpoint = self.valid_numpoints[index]
            print("%f is not a valid point number. Setting to %d instead." % (v_numpoints, closest_valid_numpoint))
            self.v_numpoints = closest_valid_numpoint
        else:
            self.v_numpoints = v_numpoints

    def do(self):
        """Run measurement"""
        # first find the necessary voltage values
        Ibias_range = np.linspace(self.Ibias_start, self.Ibias_stop, self.Ibias_steps)
        Vbias_range = self.Rbias * Ibias_range  # These are the voltage settings to use
        """TODO finish stuff here; should use np.linspace"""

        # set up DAQ "current source" settings
        self.daq.ao0.V = self.Ibias_start*self.Rbias

        # Set up VNA settings
        self.vna.networkparam = 'S12'  # Set to measure REVERSE transmission
        self.vna.power = self.v_power
        self.vna.powerstate = 1  # turn vna source power on
        self.vna.averaging_state = 1  # Turn averaging on
        self.vna.averaging_factor = self.v_avg_factor
        self.vna.freqmax = self.v_freqmax
        self.vna.freqmin = self.v_freqmin
        self.vna.sweepmode = "LIN"
        self.vna.numpoints = self.v_numpoints  # set num freq pnts for VNA
        self.vna.smoothing_state = self.v_smoothing_state  # turn smoothing on
        self.vna.smoothing_factor = self.v_smoothing_factor

        time.sleep(3)  # ensure that VNA has enough time to change settings

        # print estimated_runtime
        sleep_length = float(self.vna.ask('SWET?'))*(self.vna.averaging_factor+3)
        estimated_runtime = sleep_length*self.Ibias_steps
        print('Minimum estimated runtime: ' + str(int(estimated_runtime/60)) + ' minutes')

        I_stepsize = (float(self.Ibias_stop-self.Ibias_start))/self.Ibias_steps
        print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')
        V_stepsize = self.Rbias*I_stepsize

        # creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        # initialize empty array to store data in TODO: change from empty to NAN?
        re_im = np.empty((self.Ibias_steps, 2, self.v_numpoints))
        if self.hysteresis:
            re_im_rev = np.empty((self.Ibias_steps, 2, self.v_numpoints))

        # sweep forward in current
        index = 0
        for step in range(0, self.Ibias_steps):
            if step % 10 == 0:
                # clear_output()
                print("Current source step #" + str(step + 1) + " out of " + str(self.Ibias_steps))
                print("DAQ voltage sourcing: ", str(self.daq.ao0.V))
            self.daq.ao0.V += V_stepsize  # increment voltage/current
            self.vna.averaging_restart()
            re_im[index] = self.vna.save_re_im()
            index += 1

        # sweep backward in current
        if self.hysteresis:
            for step in range(0, self.Ibias_steps):
                if step % 10 == 0:
                    clear_output()
                    print("Current source step #" + str(step + 1) + " out of " + str(self.Ibias_steps))
                self.daq.ao0.V += -V_stepsize
                self.vna.averaging_restart()
                re_im_rev[index] = self.vna.save_re_im()
                index += 1
            self.save_data(timestamp, re_im, re_im_rev=re_im_rev)
        else:
            self.save_data(timestamp, re_im)

        self.daq.ao0 = 0  # set daq voltage to 0
        self.vna.powerstate = 0  # turn off VNA source power

        if self.plot:
            RFSweepCurrentDAQ.plotdB(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")
            RFSweepCurrentDAQ.plot_phase(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")
            if self.hysteresis:
                RFSweepCurrentDAQ.plotdB(self.filepath+"\\" + timestamp + "_rf_sweep.hdf5")
                RFSweepCurrentDAQ.plot_phase(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")

    @staticmethod
    def plotdB(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart') * 1000,
                                  data.get(filename + '/Istop') * 1000,
                                  data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop') * 1000,
                                  data.get(filename + '/Istart') * 1000,
                                  data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin') / 1e9,
                           data.get(filename + '/freqmax') / 1e9,
                           data.get(filename + '/numpoints'))
        y, x = np.meshgrid(freq, current)
        dB = RFSweepCurrentDAQ.dB_data(filename, rev=rev)
        im = ax.pcolor(x, y, dB, cmap="viridis")
        cbar = fig.colorbar(im)
        ax.set_xlabel('field coil current (mA)')
        ax.set_ylabel('frequency (GHz)')
        if not rev:
            ax.set_title(filename + "\nPower from VNA = " +
                         str(data.get(filename + '/power')) + " dBm")
        else:
            ax.set_title(filename + "\nSweep back in current" +
                         "\nPower from VNA = " + str(data.get(filename + '/power'))
                         + " dBm")
        cbar.set_label('Gain [dB]')
        if not rev:
            graph_path = filename.replace(".hdf5", "db.png")
        else:
            graph_path = filename.replace(".hdf5", "db_rev.png")
        fig.savefig(graph_path)

    @staticmethod
    def dB_data(filename, rev=False):
        data = dataset.Dataset(filename)
        if not rev:
            re_im_info = data.get(filename + '/re_im/data')
        else:
            re_im_info = data.get(filename + '/re_im_rev/data')
        attenuation = np.empty((data.get(filename + '/Isteps'),
                                int(data.get(filename + '/numpoints'))))
        n = 0
        for array in re_im_info:
            attenuation[n] = VNA8722ES.Re_Im_to_dB(array)
            n += 1
        return attenuation

    @staticmethod
    def phase_data(filename, rev=False):
        data = dataset.Dataset(filename)
        if not rev:
            re_im_info = data.get(filename + '/re_im/data')
        else:
            re_im_info = data.get(filename + '/re_im_rev/data')
        phase = np.empty((data.get(filename + '/Isteps'),
                          int(data.get(filename + '/numpoints'))))
        n = 0
        for array in re_im_info:
            phase[n] = VNA8722ES.Re_Im_to_phase(array)
            n += 1
        return phase

    @staticmethod
    def plotdB1D(filename, rev=False):
        """Plot and save single VNA freq sweep. x-axis is frequency, y-axis is dB"""
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        freq = np.linspace(data.get(filename + '/freqmin') / 1e9,
                           data.get(filename + '/freqmax') / 1e9,
                           data.get(filename + '/numpoints'))
        dB = VNA8722ES.Re_Im_to_dB(data.get(filename + '/re_im/data'))
        im = ax.plot(freq, dB[0])
        ax.set_ylabel('attenuation (dB)')
        ax.set_xlabel('frequency (GHz)')
        ax.set_title(filename + "\nPower from VNA = " +
                     str(data.get(filename + '/power')) + " dBm" + "\n" + data.get(filename + '/notes'))
        graph_path = filename.replace(".hdf5", "db.png")
        fig.savefig(graph_path)

    @staticmethod
    def plot_phase(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart') * 1000,
                                  data.get(filename + '/Istop') * 1000,
                                  data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop') * 1000,
                                  data.get(filename + '/Istart') * 1000,
                                  data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin') / 1e9,
                           data.get(filename + '/freqmax') / 1e9,
                           data.get(filename + '/numpoints'))
        y, x = np.meshgrid(freq, current)
        phase = RFSweepCurrentDAQ.phase_data(filename, rev=rev)
        im = ax.pcolor(x, y, phase, cmap="viridis")
        cbar = fig.colorbar(im)
        ax.set_xlabel('field coil current (mA)')
        ax.set_ylabel('frequency (GHz)')
        if not rev:
            ax.set_title(filename + "\nPower from VNA = " +
                         str(data.get(filename + '/power')) + " dBm")
        else:
            ax.set_title(filename + "\nSweep back in current" +
                         "\nPower from VNA = " + str(data.get(filename + '/power'))
                         + " dBm")
        cbar.set_label('Phase [degrees]')
        if not rev:
            graph_path = filename.replace(".hdf5", "phase.png")
        else:
            graph_path = filename.replace(".hdf5", "phase_rev.png")
        fig.savefig(graph_path)

    def save_data(self, timestamp, re_im, re_im_rev = None):
        name = timestamp + '_rf_sweep'
        path = os.path.join(self.filepath, name + '.hdf5')
        info = dataset.Dataset(path)
        info.append(path + '/Istart', self.Ibias_start)
        info.append(path + '/Istop', self.Ibias_stop)
        info.append(path + '/Isteps', self.Ibias_steps)
        info.append(path + '/freqmin', self.v_freqmin)
        info.append(path + '/freqmax', self.v_freqmax)
        info.append(path + '/power', self.v_power)
        info.append(path + '/avg_factor', self.v_avg_factor)
        info.append(path + '/numpoints', self.v_numpoints)
        info.append(path + '/smoothing_state', self.v_smoothing_state)
        info.append(path + '/smoothing_factor', self.v_smoothing_factor)
        info.append(path + '/re_im/data', re_im)
        info.append(path + '/re_im/description', "shape [Current, Data, Re Im]")
        info.append(path + '/re_im_rev/data', re_im_rev)
        info.append(path + '/re_im_rev/description', "shape [Current, Data, Re Im]")
        info.append(path + '/notes', self.notes)
        info.append(path + '/hysteresis', self.hysteresis)


class RFSweepCurrent:

    """Class for sweeping current with the Keithley2400 and recording
    data from the VNA8722ES at each current step.
    """
    # should this extend class Measurement? also, there will be other sweeps in the future (e.g. power sweep),
    # so may be worth having the class WithoutDAQ_ThreeParam_Sweep (esp. for plotting fxns)
    # and having these RF_sweep_<some parameter> classes extend WithoutDAQ_ThreeParam_Sweep

    """
    Initiates a RF_sweep_current object with parameters about the sweep.
    """
    def __init__(self, k_Istart, k_Istop, k_Isteps, v_freqmin, v_freqmax, v_power, v_avg_factor, v_numpoints,
                 filepath, v_smoothing_state=0, v_smoothing_factor=1, notes="No notes", hysteresis=False,
                 plot=False):
        # Set object variables
        self.k_Istart = k_Istart
        self.k_Istop = k_Istop
        self.k_Isteps = k_Isteps
        self.v_freqmin = v_freqmin
        self.v_freqmax = v_freqmax
        self.v_power = v_power
        self.v_avg_factor = v_avg_factor

        self.filepath = filepath
        self.v_smoothing_state = v_smoothing_state
        self.v_smoothing_factor = v_smoothing_factor
        self.notes = notes
        self.hysteresis = hysteresis
        self.plot = plot

        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]

        if v_numpoints not in self.valid_numpoints:
            index = (np.abs(self.valid_numpoints - v_numpoints)).argmin()
            closest_valid_numpoint = self.valid_numpoints[index]
            print("%f is not a valid point number. Setting to %d instead." %(v_numpoints, closest_valid_numpoint))
            self.v_numpoints = closest_valid_numpoint
        else:
            self.v_numpoints = v_numpoints

        self.k3 = Keithley2400(24)  # initialize current source (Instrument object)
        self.v1 = VNA8722ES(16)  # initialize VNA (Instrument object)

    def do(self):
        """
        Run measurement
        """

        # Set up current source settings
        if self.k3.output == 'off':
            self.k3.output = 'on'
        self.k3.source = 'I'
        time.sleep(3)
        self.k3.Iout_range = 1e-3  # 2 mA range # TODO: figure out what exactly range is
        self.k3.Iout = self.k_Istart
        self.k3.V_compliance = 21  # 21 volt compliance

        # Set up VNA settings
        self.v1.networkparam = 'S21'  # Set to measure forward transmission
        self.v1.power = self.v_power
        self.v1.powerstate = 1  # turn vna source power on
        self.v1.averaging_state = 1  # Turn averaging on
        self.v1.averaging_factor = self.v_avg_factor
        self.v1.freqmax = self.v_freqmax
        self.v1.freqmin = self.v_freqmin
        self.v1.sweepmode = "LIN"
        self.v1.numpoints = self.v_numpoints  # set num freq pnts for VNA
        self.v1.smoothing_state = self.v_smoothing_state  # turn smoothing on
        self.v1.smoothing_factor = self.v_smoothing_factor

        # print estimated_runtime
        sleep_length = float(self.v1.ask('SWET?'))*(self.v1.averaging_factor+3)
        estimated_runtime = sleep_length*self.k_Isteps
        print('Minimum estimated runtime: '+ str(int(estimated_runtime/60)) + ' minutes')

        I_stepsize = (float(self.k_Istop-self.k_Istart))/self.k_Isteps
        print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')

        # creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        # initialize empty array to store data in TODO: change from empty to NAN?
        re_im = np.empty((self.k_Isteps, 2, self.v_numpoints))
        if self.hysteresis:
            re_im_rev = np.empty((self.k_Isteps, 2, self.v_numpoints))

        # sweep foward in current
        index = 0
        for step in range(0, self.k_Isteps):
            if step % 10 == 0:
                print("Current source step #" + str(step+1) + " out of " + str(self.k_Isteps))
            self.k3.Iout += I_stepsize    # increment current
            self.v1.averaging_restart()  # restart averaging
            re_im[index] = self.v1.save_re_im()
            index += 1

        # sweep backwards in current
        index = 0
        if self.hysteresis:
            for step in range(0, self.k_Isteps):
                if step % 10 == 0:
                    print("Current source step #" + str(step+1) + " out of " + str(self.k_Isteps))
                self.k3.Iout = self.k3.Iout - I_stepsize  # increment current
                self.v1.averaging_restart()  # restart averaging
                re_im_rev[index] = self.v1.save_re_im()
                index += 1
            self.save_data(timestamp, re_im, re_im_rev=re_im_rev)
        else:
            self.save_data(timestamp, re_im)    # save data to h5

        self.k3.Iout = 0
        self.k3.output = 'off'  # turn off keithley output
        self.v1.powerstate = 0  # turn off VNA source power

        # plot TODO: only plots forward attenuation atm
        if self.plot:
            RFSweepCurrent.plot_db(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")
            if self.hysteresis:
                RFSweepCurrent.plot_db(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5", rev=False)

    def setup_plots_1(self):
        self.fig, self.ax = plt.subplots(1, 1, figsize=(10, 6))

    def setup_plots_2(self):
        self.fig, self.ax = plt.subplots(2, 1, figsize=(10, 6))
        self.ax = list(self.ax)

    def setup_plots_4(self):
        self.fig, self.ax = plt.subplots(2, 2, figsize=(10, 6))
        self.ax = list(self.ax)

    def save_data(self, timestamp, re_im, re_im_rev = None):
        name = timestamp + '_rf_sweep'
        path = os.path.join(self.filepath, name + '.hdf5')
        info = dataset.Dataset(path)
        info.append(path + '/Istart', self.k_Istart)
        info.append(path + '/Istop', self.k_Istop)
        info.append(path + '/Isteps', self.k_Isteps)
        info.append(path + '/freqmin', self.v_freqmin)
        info.append(path + '/freqmax', self.v_freqmax)
        info.append(path + '/power', self.v_power)
        info.append(path + '/avg_factor', self.v_avg_factor)
        info.append(path + '/numpoints', self.v_numpoints)
        info.append(path + '/smoothing_state', self.v_smoothing_state)
        info.append(path + '/smoothing_factor', self.v_smoothing_factor)
        info.append(path + '/re_im/data', re_im)
        info.append(path + '/re_im/description', "shape [Current, Data, Re Im]")
        info.append(path + '/re_im_rev/data', re_im_rev)
        info.append(path + '/re_im_rev/description', "shape [Current, Data, Re Im]")
        info.append(path + '/notes', self.notes)
        info.append(path + '/hysteresis', self.hysteresis)

    @staticmethod
    def plot_db(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart')*1000,
                        data.get(filename + '/Istop')*1000,
                        data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop')*1000,
                                  data.get(filename + '/Istart')*1000,
                                  data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin')/1e9,
                           data.get(filename + '/freqmax')/1e9,
                           data.get(filename + '/numpoints'))
        y, x = np.meshgrid(freq, current)
        dB = RFSweepCurrent.dB_data(filename, rev=rev)
        im = ax.pcolor(x, y, dB, cmap="inferno")
        cbar = fig.colorbar(im)
        ax.set_xlabel('field coil current (mA)')
        ax.set_ylabel('frequency (GHz)')
        if not rev:
            ax.set_title(filename + "\nPower from VNA = " +
                         str(data.get(filename + '/power')) + " dBm")
        else:
            ax.set_title(filename + "\nSweep back in current" +
                         "\nPower from VNA = " + str(data.get(filename + '/power'))
                         + " dBm")
        cbar.set_label('Attenuation [dB]')
        if not rev:
            graph_path = filename.replace(".hdf5", "db.png")
        else:
            graph_path = filename.replace(".hdf5", "db_rev.png")
        fig.savefig(graph_path)

    @staticmethod
    def dB_data(filename, rev = False):
        data = dataset.Dataset(filename)
        if not rev:
            re_im_info = data.get(filename + '/re_im/data')
        else:
            re_im_info = data.get(filename + '/re_im_rev/data')
        attenuation = np.empty((data.get(filename + '/Isteps'),
                                int(data.get(filename + '/numpoints'))))
        n = 0
        for array in re_im_info:
            attenuation[n] = VNA8722ES.Re_Im_to_dB(array)
            n += 1
        return attenuation

    @staticmethod
    def phase_data(filename, rev = False):
        data = dataset.Dataset(filename)
        if not rev:
            re_im_info = data.get(filename + '/re_im/data')
        else:
            re_im_info = data.get(filename + '/re_im_rev/data')
        phase = np.empty((data.get(filename + '/Isteps'),
                          int(data.get(filename + '/numpoints'))))
        n = 0
        for array in re_im_info:
            phase[n] = VNA8722ES.Re_Im_to_phase(array)
            n += 1
        return phase

    @staticmethod
    def plotdB1D(filename, rev=False):
        """
        Plot and save single VNA freq sweep. x-axis is frequency, y-axis is dB
        """
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        freq = np.linspace(data.get(filename + '/freqmin')/1e9,
                           data.get(filename + '/freqmax')/1e9,
                           data.get(filename + '/numpoints'))
        dB = VNA8722ES.Re_Im_to_dB(data.get(filename + '/re_im/data'))
        im = ax.plot(freq, dB[0])
        ax.set_ylabel('attenuation (dB)')
        ax.set_xlabel('frequency (GHz)')
        ax.set_title(filename + "\nPower from VNA = " +
                     str(data.get(filename + '/power')) + " dBm" + "\n" + data.get(filename + '/notes'))
        graph_path = filename.replace(".hdf5", "db.png")
        fig.savefig(graph_path)

    @staticmethod
    def plot_phase(filename, rev=False):
        fig, ax = plt.subplots(1,1, figsize=(10,6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart')*1000,
                                  data.get(filename + '/Istop')*1000,
                                  data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop')*1000,
                                  data.get(filename + '/Istart')*1000,
                                  data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin')/1e9,
                           data.get(filename + '/freqmax')/1e9,
                           data.get(filename + '/numpoints'))
        y, x = np.meshgrid(freq, current)
        phase = RFSweepCurrent.phase_data(filename, rev = rev)
        im = ax.pcolor(x, y, phase, cmap="inferno")
        cbar = fig.colorbar(im)
        ax.set_xlabel('field coil current (mA)')
        ax.set_ylabel('frequency (GHz)')
        if not rev:
            ax.set_title(filename + "\nPower from VNA = " +
                         str(data.get(filename + '/power')) + " dBm")
        else:
            ax.set_title(filename + "\nSweep back in current" +
                         "\nPower from VNA = " + str(data.get(filename + '/power'))
                         + " dBm")
        cbar.set_label('Phase [degrees]')
        if not rev:
            graph_path = filename.replace(".hdf5", "phase.png")
        else:
            graph_path = filename.replace(".hdf5", "phase_rev.png")
        fig.savefig(graph_path)


class RFCWSweepPower:
    """ """
    def __init__(self, k_Istart, k_Istop, k_Isteps, v_cw_freq,
                 v_power_start, v_power_stop, v_power_step, filepath,
                 v_sweeptime=.1, v_numpoints=201,v_avg_factor = 1,
                 notes="No notes", plot=False, hysteresis = False):

        # Set object variables
        self.k_Istart = k_Istart
        self.k_Istop = k_Istop
        self.k_Isteps = k_Isteps
        self.v_cw_freq = v_cw_freq      # this is the cw frequency you want to sweep at
        self.v_sweeptime = v_sweeptime  # how long the time trace is
        self.v_avg_factor = v_avg_factor
        self.v_power_start = v_power_start
        self.v_power_stop = v_power_stop
        self.v_power_step = v_power_step
        self.filepath = filepath
        self.v_numpoints = v_numpoints
        self.v_sweeptime = v_sweeptime
        self.notes = notes
        self.plot = plot
        self.hysteresis = False

        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        if v_numpoints not in self.valid_numpoints:
            index = (np.abs(self.valid_numpoints - v_numpoints)).argmin()
            closest_valid_numpoint = self.valid_numpoints[index]
            print("%f is not a valid point number. Setting to %d instead." %
                (v_numpoints, closest_valid_numpoint))
            self.v_numpoints = closest_valid_numpoint
        else:
            self.v_numpoints = v_numpoints

        self.k3 = Keithley2400(24)
        self.v1 = VNA8722ES(16)

    def do(self):
        # Set up current source settings
        if self.k3.output == 'off':
            self.k3.output = 'on'
        self.k3.source = 'I'
        time.sleep(3)
        self.k3.Iout_range = 2e-3  # 2 mA range # TODO: figure out what exactly range is
        self.k3.Iout = self.k_Istart
        self.k3.V_compliance = 21  # 21 volt compliance

        # Set up VNA settings
        self.v1.sweepmode = "CW"    # Sets to continuous sweep mode
        self.v1.sweeptime = self.v_sweeptime
        self.v1.cw_freq = self.v_cw_freq
        self.v1.networkparam = 'S21'  # Set to measure forward transmission
        self.v1.power = self.v_power_start
        self.v1.powerstate = 1  # turn vna source power on
        self.v1.averaging_state = 1  # Turn averaging on
        self.v1.averaging_factor = self.v_avg_factor
        self.v1.numpoints = self.v_numpoints  # set num freq pnts for VNA

        # creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        I_stepsize = (float(self.k_Istop-self.k_Istart))/self.k_Isteps
        print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')

        power_stepsize = (float(self.v_power_stop-self.v_power_start))/self.v_power_step
        print('Incrementing power in step sizes of ', str(power_stepsize*1000) + ' milliamps')

        # initialize empty array to store data in TODO: change from empty to NAN?
        re_im = np.empty((self.v_power_step, int(self.k_Isteps), 2, self.v_numpoints))
        if self.hysteresis:
            re_im_rev = np.empty((self.v_power_step,int(self.k_Isteps), 2, self.v_numpoints))

        self.v1.power = self.v_power_start - power_stepsize
        for powerIndex in range(0, self.v_power_step):
            self.v1.power += power_stepsize
            if powerIndex % 10 == 0:
                print("Power source step #" + str(powerIndex+1) + " out of " + str(self.v_power_step))
            self.k3.Iout = self.k_Istart
            # sweep forward in current
            for step in range(0, self.k_Isteps):
                if step % 10 == 0:
                    print("Current source step #" + str(step+1) + " out of " + str(self.k_Isteps))
                self.k3.Iout += I_stepsize    # increment current
                self.v1.averaging_restart()  # restart averaging
                re_im[powerIndex][step] = self.v1.save_re_im()

        # sweep backwards in current
        if self.hysteresis:
            self.v1.power = self.v_power_start - power_stepsize
            for powerIndex in range(0, self.v_power_step):
                self.v1.power += power_stepsize
                if powerIndex % 10 == 0:
                    print("Power source step #" + str(powerIndex+1) + " out of " + str(self.v_power_step))
                self.k3.Iout = self.k_Istart
                for step in range(0, self.k_Isteps):
                    if step % 10 == 0:
                        print("Current source step #" + str(step+1) + " out of " + str(self.k_Isteps))
                    self.k3.Iout = self.k3.Iout - I_stepsize  # increment current
                    self.v1.averaging_restart()  # restart averaging
                    re_im_rev[powerIndex][step] = self.v1.save_re_im()

        if self.hysteresis:
            self.save_data(timestamp, re_im, re_im_rev=re_im_rev)
        else:
            self.save_data(timestamp, re_im)    # save data to h5

        self.k3.Iout = 0
        self.k3.output = 'off'  # turn off keithley output
        self.v1.powerstate = 0  # turn off VNA source power

        if self.plot:
            RFCWSweepPower.plotPowerSweep(self.filepath + "\\" + timestamp + "_RF_CW_sweep_power.hdf5")
            if self.hysteresis:
                RFCWSweepPower.plotPowerSweep(self.filepath + "\\" + timestamp + "_RF_CW_sweep_power.hdf5", rev=False)

    def save_data(self, timestamp, re_im):
        name = timestamp + '_RF_CW_sweep_power'
        path = os.path.join(self.filepath, name + '.hdf5')
        info = dataset.Dataset(path)
        info.append(path + '/Istart', self.k_Istart)
        info.append(path + '/Istop', self.k_Istop)
        info.append(path + '/Isteps', self.k_Isteps)
        info.append(path + '/v_cw_freq',  self.v_cw_freq)
        info.append(path + '/v_power_stop', self.v_power_stop)
        info.append(path + '/v_power_start', self.v_power_start)
        info.append(path + '/v_power_step', self.v_power_step)
        info.append(path + '/avg_factor', self.v_avg_factor)
        info.append(path + '/numpoints', self.v_numpoints)
        info.append(path + '/re_im/data', re_im)
        info.append(path + '/re_im/description', "shape [Data, Re Im]")
        info.append(path + '/notes', self.notes)

    @staticmethod
    def plotPowerSweep(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart')*1000,
                                  data.get(filename + '/Istop')*1000,
                                  data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop')*1000,
                                  data.get(filename + '/Istart')*1000,
                                  data.get(filename + '/Isteps'))
        power = np.linspace(data.get(filename + '/v_power_start'),
                            data.get(filename + '/v_power_stop'),
                            data.get(filename + '/v_power_step'))
        freq = data.get(filename + '/v_cw_freq')/1e9
        X, Y = np.meshgrid(power, current)
        dB = RFCWSweepPower.dB_data_pow_sweep(filename, rev=rev)
        dB_avg = np.empty((data.get(filename + '/v_power_step') ,int(data.get(filename + '/Isteps'))))
        n = 0
        for array in dB:
            m = 0
            for currentArray in array:
                dB_avg[n][m] = np.mean(currentArray)
                m += 1
            n += 1
        im=ax.pcolor(X, Y, dB_avg, cmap="inferno")
        cbar = fig.colorbar(im)
        ax.set_ylabel('field coil current (mA)')
        ax.set_xlabel('power (dBm)')
        if not rev:
            ax.set_title(filename + "\nFrequency = " +
                         str(data.get(filename + '/v_cw_freq')/1e9) + " GHz")
        else:
            ax.set_title(filename + "\nSweep back in current" +
                         "\nPower from VNA = " + str(data.get(filename + '/power'))
                         + " dBm")
        cbar.set_label('Attenuation [dB]')
        if not rev:
            graph_path = filename.replace(".hdf5", "pow.png")
        else:
            graph_path = filename.replace(".hdf5", "pow_rev.png")
        fig.savefig(graph_path)

    @staticmethod
    def dB_data_pow_sweep(filename, rev = False):
        data = dataset.Dataset(filename)
        if not rev:
            re_im_info = data.get(filename + '/re_im/data')
        else:
            re_im_info = data.get(filename + '/re_im_rev/data')
        attenuation = np.empty((data.get(filename + '/v_power_step'),int(data.get(filename + '/Isteps')), data.get(filename + '/numpoints')))
        n = 0
        for array in re_im_info:
            m = 0
            for currentArray in array:
                attenuation[n][m] = VNA8722ES.Re_Im_to_dB(currentArray)
                m += 1
            n += 1
        return attenuation


class RFSetupSaver:
    """
    Want to make this parent class of the other rf_sweep measurement procedures for less repeat save code
    """
    def __init__(self, save_location):
        # child classes should call this (how to enforce this using standard inheritance/OOP practices?)
        self.save_location = save_location
        self.timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        self.__hdf5_file = None
        pass

    def do(self):
        """
        The measurement; implement in subclass
        """
        pass

    def save(self):
        # gather names of attributes that are not methods or Python special methods
        attribute_names_to_save = [a for a in dir(self) if not a.startswith('__') and not callable(getattr(self, a))]
        timestamp = self.timestamp
        name = timestamp + self.__name__
        path = os.path.join(self.save_location, name + '.hdf5')
        info = dataset.Dataset(path)
        self.__hdf5_file = info
        for attr_name in attribute_names_to_save:
            info.append(path + '/' + attr_name, self.__getattribute__(attr_name))

    def get_saved_attribute(self, attribute_name):
        attr_to_return = getattr(self.__hdf5_file, attribute_name)
        return attr_to_return
