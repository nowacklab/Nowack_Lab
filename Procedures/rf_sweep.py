# Some of these imports may not be used (same imports as squidIV2)
import numpy as np
import matplotlib.pyplot as plt
import os
from importlib import reload
from scipy.interpolate import UnivariateSpline
from ..Utilities.plotting import plot_mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.signal import savgol_filter
from datetime import datetime

# Nowack_Lab imports
import Nowack_Lab.Utilities.dataset
from Nowack_Lab.Utilities.dataset import Dataset
from Nowack_Lab.Instruments import VNA8722ES
from Nowack_Lab.Instruments import Keithley2400

class WithoutDAQ_ThreeParam_Sweep):
    '''Sweep field coil current and measured frequency using VNA and keithley2400'''
    def __init__(self):
        pass

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()

    def plot(self):
        pass

    def _do(self, i, j):
        pass

    def _sweeptopt(self):
        pass

    def do(self):
        pass

    @staticmethod
    def plot_lines():
        pass

    @staticmethod
    def plot_color_diff(obj, ax):
        pass

    @staticmethod
    def plot_color():
        pass

    @staticmethod
    def plot_color_gradient():
        pass

    @staticmethod
    def plot_color_absgradient():
        pass

    @staticmethod
    def plot_fastmod():
        pass

    @staticmethod
    def plot_amplitude():
        pass

class RF_sweep_current(WithoutDAQ_ThreeParam_Sweep):
    ''' At different current steps, measure frequency response
    Using class SQUID_Mod_FastIV(ThreeParam_Sweep) as example'''
    instrument_list = ['VNA', 'keithley']  # probably not necessary

    # _XLABEL = r'$I_{squid}$ ($\mu A$)'
    # _YLABEL = r'$Frequency_{squid}$ ($\mu Hz$)'

    def __init__(self, instruments = [],
                k_Istart, k_Istop, k_Isteps,
                v_freqmin, v_freqmax, v_power, v_avg_factor, v_numpoints,
                filepath, v_smoothing_state=0,
                v_smoothing_factor=1, notes = "No notes",hysteresis=False,
                plot=False):
        # mode 0: only dB. mode 1: only phase. mode 2: dB and phase.
        super().__init__(instruments=instruments)  # no daq stuff

        assert self.k_Istart < k_Istop, "stop voltage should be greater than start voltage"
        assert self.v_power <= -65, "Don't send too much power to SQUID"
        valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert self.v_numpoints in self.valid_numpoints, "number of points must be in " + str(valid_numpoints)

        self.k3 = Keithley2400(24)  # initialize current source (Instrument object)
        self.v1 = VNA8722ES(16)  # initialize VNA (Instrument object)

        self.arr_1 = None  # store an array to plot
        self.arr_2 = None  # store an array to plot

    def do(self):
        '''
        Run measurement
        Arguments:
            hysteresis (boolean): sweep current up and down?
            plot (boolean): should I plot?
        '''

        # Set up current source settings
        if(self.k3.output == 'off'):
            self.k3.output = 'on'
        self.k3.source = 'I'
        time.sleep(3)  # FIXME this is clumsy way of making sure keithley has enough time to turn on
        self.k3.Iout_range = 20e-3  # 20 mA range # TODO: figure out what exactly range is
        self.k3.Iout = 0
        self.k3.V_compliance = 21  # 21 volt compliance

        # Set up VNA settings
        self.v1.networkparam = 'S21'  # Set to measure forward transmission
        self.v1.power = v_power
        self.v1.powerstate = 1  # turn vna source power on
        self.v1.averaging_state = 1  # Turn averaging on
        self.v1.averaging_factor = v_averaging_factor # Set averaging factor
        self.v1.minfreq = v_freqmin  # set sweep range
        self.v1.maxfreq = v_freqmax
        self.v1.numpoints = v_numpoints  # set number of points in frequency sweep
        self.v1.smoothing_state = v_smoothing_state  # turn smoothing on
        self.v1.smoothing_factor = v_smoothing_factor  # set smoothing factor

        sleep_length = float(self.v1.ask('SWET?'))*(self.v1.averaging_factor+3)
        estimated_runtime = sleep_length*k_Isteps
        print('Minimum estimated runtime: '+ str(int(estimated_runtime/60)) + ' minutes')

        I_stepsize = (float(k_Istop-k_Istart))/k_Isteps
        print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')
        re_im = np.empty((k_Isteps, int(self.v1.numpoints), 2))

        timestamp = now.strftime('%Y-%m-%d_%H%M%S')

        if hysteresis == True:
            re_im_rev = np.empty((k_Isteps, int(self.v1.numpoints), 2))

        index = 0
        for step in range(0, k_Isteps):
            if step % 10 == 0:
                print("Current source step #" + str(step+1) + " out of " + str(k_Isteps))
            self.k3.Iout = self.k3.Iout + I_stepsize  # increment current
            self.v1.averaging_restart()  # restart averaging
            re_im[index] = self.v1.save_Re_Im()
            index += 1

        index = 0
        if(hysteresis == True):
            for step in range(0, k_Isteps):
                if step % 10 == 0:
                    print("Current source step #" + str(step+1) + " out of " + str(k_Isteps))
                self.k3.Iout = self.k3.Iout - I_stepsize  # increment current
                self.v1.averaging_restart()  # restart averaging
                re_im_rev[index] = self.v1.save_Re_Im()
                index += 1
            save_data(timestamp, re_im, re_im_rev = attenuation_rev)
        else:
            save_data(timestamp, re_im)

        self.k3.Iout = 0
        self.k3.output = 'off'  # turn off keithley output
        self.v1.powerstate = 0  # turn off VNA source power


        if plot == True:
            rf_sweep.plot(filepath + "\\" + timestamp + "_rf_sweep.hdf5")



    def setup_plots_1(self):
        self.fig, self.ax = plt.subplots(1,1, figsize=(10,6))

    def setup_plots_2(self):
        self.fig, self.ax = plt.subplots(2,1, figsize=(10,6))
        self.ax = list(self.ax)

    def setup_plots_4(self):
        self.fig, self.ax = plt.subplots(2,2, figsize=(10,6))
        self.ax = list(self.ax)

    @staticmethod
    def plot(filename):
        fig, ax = plt.subplots(1,1, figsize=(10,6))
        data = dataset(filename)
        current = np.linspace(data.get(filename + '/Istart'),
                    data.get(filename + '/Istop'),
                    data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin'),
                    data.get(filename + '/freqmax'),
                    data.get(filename + '/numpoints'))
        X,Y = np.meshgrid(freq, current)
        dB = dB_data(filename)
        im=ax.pcolor(X, Y, dB, cmap="inferno")
        cbar = fig.colorbar(im)
        ax.set_ylabel('field coil current (A)')
        ax.set_xlabel('frequency (Hz)')
        cbar.set_label('Attenuation [dB]')

    @staticmethod
    def dB_data(filename):
        data = dataset(filename)
        re_im_info = data.get(filename + '/re_im/data')
        attenuation = np.empty((data.get(filename + '/Isteps'),
                                int(data.get(filename + '/numpoints'))))
        n = 0
        for array in re_im_info:
            attenuation[n] = Re_Im_to_dB(array)
            n += 1
        return attenuation

    def save_data(self, timestamp, re_im, re_im_rev = None):
        now = datetime.now()
        name = timestamp + '_rf_sweep'
        path = os.path.join(filepath, name + '.hdf5')
        info = dataset(path)
        info.append(path + '/Istart', k_Istart)
        info.append(path + '/Istop', k_Istop)
        info.append(path + '/Isteps', k_Isteps)
        info.append(path + '/freqmin', v_freqmin)
        info.append(path + '/freqmax', v_freqmax)
        info.append(path + '/freqmax', v_freqmax)
        info.append(path + '/power', v_power)
        info.append(path + '/avg_factor', v_avg_factor)
        info.append(path + '/numpoints', v_numpoints)
        info.append(path + '/smoothing_state', v_smoothing_state)
        info.append(path + '/smoothing_factor', v_smoothing_factor)
        info.append(path + '/re_im/data', re_im)
        info.append(path + '/re_im/description', "shape [Current, Data, Re Im]")
        info.append(path + '/re_im_rev/data', re_im_rev)
        info.append(path + '/re_im_rev/description', "shape [Current, Data, Re Im]")
        info.append(path + '/notes', notes)
        info.append(path + '/hysteresis', hysteresis)




    @staticmethod
    def plot_color(ax, xaxis, yaxis, z, cmap='viridis'):
        im = ax.imshow(z, cmap, origin='lower',
                        extent=(xaxis[0], xaxis[-1], yaxis[0], yaxis[-1]),
                        aspect='auto')
        d = make_axes_locatable(ax)
        cax = d.append_axes('right', size=.1, pad=.1)
        cbar = plt.colorbar(im, cax=cax)

        return [ax, cbar]
