import numpy as np
import matplotlib.pyplot as plt
import os
import time
from importlib import reload
from scipy.interpolate import UnivariateSpline
from ..Utilities.plotting import plot_mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.signal import savgol_filter
from datetime import datetime

# Nowack_Lab imports
from Nowack_Lab.Utilities import dataset
from Nowack_Lab.Utilities.dataset import Dataset
from Nowack_Lab.Instruments.VNA import VNA8722ES
from Nowack_Lab.Instruments.keithley import Keithley2400

class RF_take_spectra:
    '''
    Take a single spectrum (attenuation as function of frequency)
    '''
    def __init__(self,v_freqmin, v_freqmax, v_power, v_avg_factor, v_numpoints,
                filepath, v_smoothing_state=0,v_smoothing_factor=1,
                notes = "No notes",plot=False):

        #Set object variables
        self.v_freqmin =v_freqmin
        self.v_freqmax =v_freqmax
        self.v_power =v_power
        self.v_avg_factor =v_avg_factor
        self.v_numpoints =v_numpoints
        self.filepath = filepath
        self.v_smoothing_state = v_smoothing_state
        self.v_smoothing_factor = v_smoothing_factor
        self.notes = notes
        self.plot = plot

        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert self.v_numpoints in self.valid_numpoints,"number of points must be in " + str(self.valid_numpoints)

        self.v1 = VNA8722ES(16)  # initialize VNA (Instrument object)

    def do(self):
        '''
        Run measurement
        '''
        # Set up VNA settings
        self.v1.networkparam = 'S21'  # Set to measure forward transmission
        self.v1.power = self.v_power
        self.v1.powerstate = 1  # turn vna source power on
        self.v1.averaging_state = 1  # Turn averaging on
        self.v1.averaging_factor = self.v_avg_factor
        self.v1.minfreq = self.v_freqmin
        self.v1.maxfreq = self.v_freqmax
        self.v1.numpoints = self.v_numpoints  # set num freq pnts for VNA
        self.v1.smoothing_state = self.v_smoothing_state  # turn smoothing on
        self.v1.smoothing_factor = self.v_smoothing_factor

        #creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        #initialize empty array to store data in TODO: change from empty to NAN?
        re_im = np.empty((2, int(self.v1.numpoints)))

        re_im = self.v1.save_Re_Im()  # get real and imaginary parts
        self.save_data(timestamp, re_im) #save data to h5

        self.v1.powerstate = 0  # turn off VNA source power

        #plot TODO: only plots foward attenuation atm
        if self.plot == True:
            RF_sweep_current.plotdB1D(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")

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


'''Class for sweeping current with the Keithley2400 and recording
data from the VNA8722ES at each current step.
'''

class RF_sweep_current: # should this extend class Measurement?
                        # also, there will be other sweeps in the future (e.g. power sweep),
                        # so may be worth having the class WithoutDAQ_ThreeParam_Sweep (esp. for plotting fxns)
                        # and having these RF_sweep_<some parameter> classes extend WithoutDAQ_ThreeParam_Sweep

    '''
    Initiates a RF_sweep_current object with parameters about the sweep.
    '''
    def __init__(self,
                k_Istart, k_Istop, k_Isteps,
                v_freqmin, v_freqmax, v_power, v_avg_factor, v_numpoints,
                filepath, v_smoothing_state=0,
                v_smoothing_factor=1, notes = "No notes",hysteresis=False,
                plot=False):

        #Set object variables
        self.k_Istart = k_Istart
        self.k_Istop =k_Istop
        self.k_Isteps =k_Isteps
        self.v_freqmin =v_freqmin
        self.v_freqmax =v_freqmax
        self.v_power =v_power
        self.v_avg_factor =v_avg_factor
        self.v_numpoints =v_numpoints
        self.filepath = filepath
        self.v_smoothing_state = v_smoothing_state
        self.v_smoothing_factor = v_smoothing_factor
        self.notes = notes
        self.hysteresis = hysteresis
        self.plot = plot

        assert self.k_Istart < k_Istop,"stop voltage should be greater than start voltage"
        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert self.v_numpoints in self.valid_numpoints,"number of points must be in " + str(self.valid_numpoints)

        self.k3 = Keithley2400(24)  # initialize current source (Instrument object)
        self.v1 = VNA8722ES(16)  # initialize VNA (Instrument object)

    def do(self):
        '''
        Run measurement
        '''

        # Set up current source settings
        if(self.k3.output == 'off'):
            self.k3.output = 'on'
        self.k3.source = 'I'
        time.sleep(3)
        self.k3.Iout_range = 20e-3  # 20 mA range # TODO: figure out what exactly range is
        self.k3.Iout = self.k_Istart
        self.k3.V_compliance = 21  # 21 volt compliance

        # Set up VNA settings
        self.v1.networkparam = 'S21'  # Set to measure forward transmission
        self.v1.power = self.v_power
        self.v1.powerstate = 1  # turn vna source power on
        self.v1.averaging_state = 1  # Turn averaging on
        self.v1.averaging_factor = self.v_avg_factor
        self.v1.minfreq = self.v_freqmin
        self.v1.maxfreq = self.v_freqmax
        self.v1.numpoints = self.v_numpoints  # set num freq pnts for VNA
        self.v1.smoothing_state = self.v_smoothing_state  # turn smoothing on
        self.v1.smoothing_factor = self.v_smoothing_factor

        #print estimated_runtime
        sleep_length = float(self.v1.ask('SWET?'))*(self.v1.averaging_factor+3)
        estimated_runtime = sleep_length*self.k_Isteps
        print('Minimum estimated runtime: '+ str(int(estimated_runtime/60)) + ' minutes')

        I_stepsize = (float(self.k_Istop-self.k_Istart))/self.k_Isteps
        print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')

        #creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        #initialize empty array to store data in TODO: change from empty to NAN?
        re_im = np.empty((self.k_Isteps, 2, int(self.v1.numpoints)))
        if self.hysteresis == True:
            re_im_rev = np.empty((self.k_Isteps, 2, int(self.v1.numpoints)))

        # sweep foward in current
        index = 0
        for step in range(0, self.k_Isteps):
            if step % 10 == 0:
                print("Current source step #" + str(step+1) + " out of " + str(self.k_Isteps))
            self.k3.Iout = self.k3.Iout + I_stepsize  # increment current
            self.v1.averaging_restart()  # restart averaging
            re_im[index] = self.v1.save_Re_Im()
            index += 1

        # sweep backwards in current
        index = 0
        if(self.hysteresis == True):
            for step in range(0, self.k_Isteps):
                if step % 10 == 0:
                    print("Current source step #" + str(step+1) + " out of " + str(self.k_Isteps))
                self.k3.Iout = self.k3.Iout - I_stepsize  # increment current
                self.v1.averaging_restart()  # restart averaging
                re_im_rev[index] = self.v1.save_Re_Im()
                index += 1
            self.save_data(timestamp, re_im, re_im_rev=re_im_rev)
        else:
            self.save_data(timestamp, re_im) #save data to h5

        self.k3.Iout = 0
        self.k3.output = 'off'  # turn off keithley output
        self.v1.powerstate = 0  # turn off VNA source power

        #plot TODO: only plots forward attenuation atm
        if self.plot == True:
            RF_sweep_current.plotdB(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")
            if self.hysteresis == True:
                RF_sweep_current.plotdB(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5", rev=False)



    def setup_plots_1(self):
        self.fig, self.ax = plt.subplots(1,1, figsize=(10,6))

    def setup_plots_2(self):
        self.fig, self.ax = plt.subplots(2,1, figsize=(10,6))
        self.ax = list(self.ax)

    def setup_plots_4(self):
        self.fig, self.ax = plt.subplots(2,2, figsize=(10,6))
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
    def plotdB(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart')*100,
                        data.get(filename + '/Istop')*100,
                        data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop')*100,
                        data.get(filename + '/Istart')*100,
                        data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin')/1e9,
                    data.get(filename + '/freqmax')/1e9,
                    data.get(filename + '/numpoints'))
        Y,X = np.meshgrid(freq, current)
        dB = RF_sweep_current.dB_data(filename, rev = rev)
        im=ax.pcolor(X, Y, dB, cmap="inferno")
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
        '''
        Plot and save single VNA freq sweep. x-axis is frequency, y-axis is dB
        '''
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
    def plotPhase(filename, rev=False):
        fig, ax = plt.subplots(1,1, figsize=(10,6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart')*100,
                        data.get(filename + '/Istop')*100,
                        data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop')*100,
                        data.get(filename + '/Istart')*100,
                        data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin')/1e9,
                    data.get(filename + '/freqmax')/1e9,
                    data.get(filename + '/numpoints'))
        Y,X = np.meshgrid(freq, current)
        phase = RF_sweep_current.phase_data(filename, rev = rev)
        im=ax.pcolor(X, Y, phase, cmap="inferno")
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
        cbar.set_label('Phase [derees]')
        if not rev:
            graph_path = filename.replace(".hdf5", "phase.png")
        else:
            graph_path = filename.replace(".hdf5", "phase_rev.png")
        fig.savefig(graph_path)


class RF_sweep_power:

    """
    Initiate a sweep through bias current (x-axis), VNA source power (y-axis), attenuation/phase? (z-axis)
    """
    def __init__(self,
                 k_Istart, k_Istop, k_Isteps,
                 v_freqmin, v_freqmax, v_powermin, v_powermax, v_powersteps, v_avg_factor, filepath, v_numpoints=1601,
                 v_smoothing_state=0,
                 v_smoothing_factor=1, notes="No notes", hysteresis=False,
                 plot=False):

        # Set object variables
        self.k_Istart = k_Istart
        self.k_Istop = k_Istop
        self.k_Isteps = k_Isteps
        self.v_freqmin = v_freqmin
        self.v_freqmax = v_freqmax
        self.v_powermin = v_powermin
        self.v_powermax = v_powermax
        self.v_powersteps = v_powersteps
        self.v_avg_factor = v_avg_factor
        self.v_numpoints = v_numpoints
        self.filepath = filepath
        self.v_smoothing_state = v_smoothing_state
        self.v_smoothing_factor = v_smoothing_factor
        self.notes = notes
        self.hysteresis = hysteresis
        self.plot = plot

        assert self.k_Istart < k_Istop, "stop voltage should be greater than start voltage"
        self.valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert self.v_numpoints in self.valid_numpoints, "number of points must be in " + str(self.valid_numpoints)

        self.k3 = Keithley2400(24)  # initialize current source (Instrument object)
        self.v1 = VNA8722ES(16)  # initialize VNA (Instrument object)

    def do(self):
        """
        Run measurement power current sweep measurement
        """
        # Set up current source settings
        if self.k3.output == 'off':
            self.k3.output = 'on'
        self.k3.source = 'I'
        time.sleep(3)
        self.k3.Iout_range = 20e-3  # 20 mA range
        self.k3.Iout = self.k_Istart
        self.k3.V_compliance = 21   # 21 volt compliance

        # Set up VNA settings
        self.v1.networkparam = 'S21'    # Set to measure forward transmission
        self.v1.power = self.v_powermin    # set to start power
        self.v1.powerstate = 1          # turn vna source power on
        self.v1.averaging_state = 1     # Turn averaging on
        self.v1.averaging_factor = self.v_avg_factor
        self.v1.minfreq = self.v_freqmin    # set min sweep frequency
        self.v1.maxfreq = self.v_freqmax    # set max sweep frequency
        self.v1.numpoints = self.v_numpoints                # set num freq pnts for VNA
        self.v1.smoothing_state = self.v_smoothing_state    # turn smoothing on
        self.v1.smoothing_factor = self.v_smoothing_factor  # set smoothing factor

        # print estimated_runtime
        sleep_length = float(self.v1.ask('SWET?')) * (self.v1.averaging_factor + 3)
        estimated_runtime = sleep_length * self.k_Isteps
        print('Minimum estimated runtime: ' + str(int(estimated_runtime / 60)) + ' minutes')

        power_stepsize = (float(self.v_powermax - self.v_powermin)) / self.v_powersteps
        print('Incrementing power in step sizes of ', str(power_stepsize) + ' dB')

        I_stepsize = (float(self.k_Istop - self.k_Istart)) / self.k_Isteps
        print('Incrementing current in step sizes of ', str(I_stepsize * 1000) + ' mA')

        # creates a timestamp that will be in the h5 file name for this run
        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        # initialize empty array to store data in TODO: change from empty to NAN?
        re_im = np.empty((self.k_Isteps, 2, int(self.v_powersteps)))
        if self.hysteresis:
            print("Hysteretic sweep for current-power sweep not yet implemented; which param to sweep both ways, and what is physical interpretation")
            re_im_rev = np.empty((self.k_Isteps, 2, int(self.v_powersteps)))

        # sweep foward in power, then current
        index = 0
        for powerstep in range(0, self.v_powersteps):
            if powerstep % 10 == 0:
                print("something source step #" + str(powerstep + 1) + " out of " + str(self.k_powersteps))
            self.v1.power += power_stepsize  # increment power
            self.v1.averaging_restart()  # restart averaging

            for currentstep in range(self.k_Isteps):
                self.k3.Iout += I_stepsize    # increment source current
                re_im_to_average = self.v1.save_Re_Im()
                re_im[currentstep, 0, powerstep] = np.mean(re_im_to_average[0])      # averaged real part
                re_im[currentstep, 1, powerstep] = np.mean(re_im_to_average[1])      # averaged imaginary part
                index += 1

        # save data to h5
        if self.hysteresis:
            print("Saving empty reverse array (hysteretic sweep not yet implemented)")
            self.save_data(timestamp, re_im, re_im_rev=re_im_rev)
        else:
            self.save_data(timestamp, re_im)    # save data to h5

        self.k3.Iout = 0
        self.k3.output = 'off'  # turn off keithley output
        self.v1.powerstate = 0  # turn off VNA source power

        # plot TODO: only plots forward attenuation atm
        if self.plot:
            RF_sweep_power.plotdB(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5")
            RF_sweep_power.plotPh
            if self.hysteresis:
                print("power current sweep hysteresis not yet implemented")
                RF_sweep_power.plotdB(self.filepath + "\\" + timestamp + "_rf_sweep.hdf5", rev=False)

    def setup_plots_1(self):
        self.fig, self.ax = plt.subplots(1,1, figsize=(10,6))

    def setup_plots_2(self):
        self.fig, self.ax = plt.subplots(2,1, figsize=(10,6))
        self.ax = list(self.ax)

    def setup_plots_4(self):
        self.fig, self.ax = plt.subplots(2,2, figsize=(10,6))
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
        info.append(path + '/powermin', self.v_powermin)
        info.append(path + '/powermax', self.v_powermax)
        info.append(path + '/powersteps', self.v_powersteps)
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
    def plotdB(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart') * 100,
                                  data.get(filename + '/Istop') * 100,
                                  data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop') * 100,
                                  data.get(filename + '/Istart') * 100,
                                  data.get(filename + '/Isteps'))
        powers = np.linspace(data.get(filename + '/powermin') / 1e9,
                             data.get(filename + '/powermax') / 1e9,
                             data.get(filename + '/powersteps'))
        Y, X = np.meshgrid(powers, current)
        dB = RF_sweep_power.dB_data(filename, rev=rev)
        im = ax.pcolor(X, Y, dB, cmap="inferno")
        cbar = fig.colorbar(im)
        ax.set_xlabel('field coil current (mA)')
        ax.set_ylabel('VNA source power (dBm)')
        if not rev:
            ax.set_title(filename + "\nFrequency = " +
                         str(data.get(filename + '/freqmin') * .5 + data.get(filename + '/freqmax') * .5) + " Hz")
        else:
            raise NotImplementedError("Change title if have implemented reverse sweep in either param")
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
    def removenoise_phase_data(filename, degree_limit=50, rev=False):
        """Return phase arrays without "blips" i.e. no phase shift above/below some number of degrees"""

        phase_data = RF_sweep_current.phase_data(filename, rev=rev)
        outside_threshold_indices = np.abs(phase_data) > degree_limit
        phase_data[outside_threshold_indices] = 0   # set all entries above/below degree_limit to 0
        return phase_data

    @staticmethod
    def plotPhase(filename, rev=False):
        fig, ax = plt.subplots(1,1, figsize=(10,6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart')*100,
                        data.get(filename + '/Istop')*100,
                        data.get(filename + '/Isteps'))
        else:

            current = np.linspace(data.get(filename + '/Istop')*100,
                        data.get(filename + '/Istart')*100,
                        data.get(filename + '/Isteps'))
        powers = np.linspace(data.get(filename + '/powermin')/1e9,
                    data.get(filename + '/powermax')/1e9,
                    data.get(filename + '/powersteps'))
        Y,X = np.meshgrid(powers, current)
        phase = RF_sweep_current.phase_data(filename, rev = rev)
        im=ax.pcolor(X, Y, phase, cmap="inferno")
        cbar = fig.colorbar(im)
        ax.set_xlabel('field coil current (mA)')
        ax.set_ylabel('VNA source power (dBm)')
        if not rev:
            ax.set_title(filename + "\nFrequency = " +
                str(data.get(filename + '/freqmin')*.5+data.get(filename + '/freqmax')*.5) + " Hz")
        else:
            raise NotImplementedError("Change title if have implemented reverse sweep in either param")
            ax.set_title(filename + "\nSweep back in current" +
                "\nPower from VNA = " + str(data.get(filename + '/power'))
                 + " dBm")
        cbar.set_label('Phase [derees]')
        if not rev:
            graph_path = filename.replace(".hdf5", "phase.png")
        else:
            graph_path = filename.replace(".hdf5", "phase_rev.png")
        fig.savefig(graph_path)