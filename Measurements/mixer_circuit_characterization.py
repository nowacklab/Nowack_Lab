""" Use to get DAQ voltage as function of reflected squid power and circuit drive power"""
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from ..Instruments.VNA import VNA8722ES
from ..Instruments.nidaq import NIDAQ
from ..Instruments.HP8657B import FunctionGenerator
from ..Utilities.dataset import Dataset
from IPython.display import clear_output
from ..Utilities.save import Saver
from ..Utilities.plotting.plotter import Plotter


class MixerCircuitTester:
    """ SHOULD NOT BE USED - this test should not give meaningful results"""
    def __init__(self, power_start, power_stop, power_numpoints,
                 freq_start, freq_stop, freq_numpoints,
                 preamp_gain, filepath, daq_input_label='ai0'):
        print("MAY NEED TO MANUALLY PUT IN GPIB ADDRESSES -- SHOULD CHANGE THAT TO INIT IN CODE")
        self.power_start = power_start
        self.power_stop = power_stop
        self.power_numpoints = power_numpoints
        self.power_range = np.linspace(self.power_start, self.power_stop, self.power_numpoints)
        self.freq_start = freq_start
        self.freq_stop = freq_stop
        self.freq_numpoints = freq_numpoints
        self.freq_range = np.linspace(self.freq_start, self.freq_stop, self.freq_numpoints)
        self.preamp_gain = preamp_gain

        self.filepath = filepath

        self.vna = VNA8722ES()
        self.fxngen = FunctionGenerator(7)
        self.daq = NIDAQ()
        self.daq_input_label = daq_input_label

    def do(self):
        """ Run measurement and save data """
        # set vna power to starting power
        self.vna.networkparam = 'S22'
        self.vna.power = self.power_range[0]
        self.vna.numpoints = 3
        self.vna.powerstate = 1

        self.fxngen.freq = float(self.freq_start)/2
        self.vna.freqmin = self.freq_start
        self.vna.freqmax = self.freq_start

        data_arr = np.zeros((self.power_numpoints, self.freq_numpoints))

        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')
        for i in range(self.power_numpoints):
            self.vna.power = self.power_range[i]
            time.sleep(.5)
            for f in range(self.freq_numpoints):
                thisfreq = self.freq_range[f]
                self.vna.freqmin = thisfreq
                self.vna.freqmax = thisfreq
                clear_output()
                print("changing fxngen freq")
                print("power step ", i)
                print("frequency step ", f)
                self.fxngen.freq = float(thisfreq)/2
                time.sleep(.5)

                daq_monitor_time = 1
                daq_data = self.daq.monitor([self.daq_input_label], daq_monitor_time, 1000)
                time.sleep(1.1*daq_monitor_time)
                daq_data_average = np.mean(daq_data[self.daq_input_label])
                normalized_daq_data_average = daq_data_average/float(self.preamp_gain)

                data_arr[i, f] = normalized_daq_data_average

        self.vna.powerstate = 0
        self.save(timestamp, data_arr)
        MixerCircuitTester.plot(self.filepath + '\\' + timestamp + '_mixer_characterization.hdf5')

    def save(self, timestamp, array):
        name = timestamp + '_mixer_characterization'
        path = os.path.join(self.filepath, name + '.hdf5')
        info = Dataset(path)
        info.append(path + '/power_start', self.power_start)
        info.append(path + '/power_stop', self.power_stop)
        info.append(path + '/power_numpoints', self.power_numpoints)
        info.append(path + '/power_range', self.power_range)
        info.append(path + '/freq_start', self.freq_start)
        info.append(path + '/freq_stop', self.freq_stop)
        info.append(path + '/freq_numpoints', self.freq_numpoints)
        info.append(path + '/freq_range', self.freq_range)
        info.append(path + '/preamp_gain', self.preamp_gain)
        info.append(path + '/daq_input_label', self.daq_input_label)

        info.append(path + '/data_array', array)

    @staticmethod
    def plot(filename):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = Dataset(filename)
        freq_range = data.get(filename + '/freq_range')
        power_range = data.get(filename + '/power_range')
        y, x = np.meshgrid(freq_range, power_range)
        im = ax.pcolor(x, y, data.get(filename + '/data_array'), cmap="viridis")
        cbar = fig.colorbar(im)
        ax.set_xlabel('power, dbm')
        ax.set_ylabel('frequency, Hz')
        preamp_gain = data.get(filename + '/preamp_gain')
        ax.set_title(filename + ' preamp gain ' + str(preamp_gain))
        cbar.set_label('DAQ voltage normalized by preamp_gain, preamp_gain = ' + str(preamp_gain))
        graph_path = filename.replace(".hdf5", "graph.png")
        fig.savefig(graph_path)


class SimpleTakeDAQVoltage:
    """
    Take voltage of DAQ using monitor
    """
    def __init__(self, daq_monitor_time, daq_input_label='ai0'):
        self.daq = NIDAQ()
        self.daq_monitor_time = daq_monitor_time
        self.daq_input_label = daq_input_label

    def do(self):
        daq_data = self.daq.monitor([self.daq_input_label], self.daq_monitor_time, 1000)
        time.sleep(1.1 * self.daq_monitor_time)
        daq_data_average = np.mean(daq_data[self.daq_input_label])
        print(daq_data_average)
        return daq_data_average


class StepVNAasRF(Saver, Plotter):
    """
    To characterize direct conversion property of single mixer
    With set LO frequency, step VNA frequency as RF input
    """
    def __init__(self, v_minfreq, v_maxfreq, v_freqsteps, v_power, v_pause_time, v_network_param='S12'):
        self.v = VNA8722ES(16)
        self.daq = NIDAQ()
        self.v_minfreq = v_minfreq
        self.v_maxfreq = v_maxfreq
        self.v_freqsteps = v_freqsteps
        self.v_power = v_power
        self.v_pausetime = v_pause_time
        self.v_network_param = v_network_param
        # self.daq_input_label = daq_input_label
        self.v_freq_range = np.linspace(self.v_minfreq, self.v_maxfreq, num=self.v_freqsteps)

        self.x_axis_data = self.v_freq_range
        self.y_axis_data = np.array([])

    def do(self):
        # first get y data, then save, then plot
        self.v.sweepmode = 'CW'  # set VNA to continuous wave
        self.v.cw_freq = self.v_minfreq

        self.v.power = self.v_power
        self.v.networkparam = self.v_network_param

        y_data_array = np.empty((self.v_freqsteps, 1))

        self.v.powerstate = 1

        counter = 0
        for freq_point in self.v_freq_range:
            self.v.cw_freq = freq_point
            time.sleep(self.v_pausetime)
            y_data_array[counter] = self.daq.ai0.V
            counter += 1

        self.y_axis_data = y_data_array
        self.save()
        self.plot()

    def plot_update(self):
        self.plot1.set_xdata(self.v_freq_range)
        self.plot1.set_ydata(self.y_axis_data)

        self.ax.relim()
        self.ax.autoscale_view()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.plot1 = self.ax.plot(self.x_axis_data, self.y_axis_data)[0]
        self.ax.set_xlabel('VNA frequency (mixer RF port)')
        self.ax.set_ylabel('DAQ voltage reading (mixer IF port)')

class StepVNAandFunctionGenerator:
    """
    To characterize direct conversion property of single mixer
    Keep VNA and FunctionGenerator at equal frequencies, artificially control VNA power as function of frequency
    """

    def __init__(self, minfreq, maxfreq, freqsteps, power_dip_frequencies, pause_time, v_network_param='S12'):
        self.v = VNA8722ES(16)
        self.daq = NIDAQ
        self.fxn_gen = FunctionGenerator()
        pass