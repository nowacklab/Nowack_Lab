""" Use to get DAQ voltage as function of reflected squid power and circuit drive power"""
import os, time, datetime, numpy as np, matplotlib.pyplot as plt
from ..Instruments.VNA import VNA8722ES
from ..Instruments.nidaq import NIDAQ
from ..Instruments.HP8657B import functiongenerator
from ..Utilities.dataset import Dataset


class MixerCircuitTester:
    def __init__(self, power_start, power_stop, power_numpoints,
                 freq_start, freq_stop, freq_numpoints,
                 preamp_gain, filepath, daq_input_label='ai0'):

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
        self.fxngen = functiongenerator(17)
        self.daq = NIDAQ()
        self.daq_input_label = daq_input_label

    def do(self):
        """ Run measurement and save data """
        # set vna power to starting power
        self.vna.networkparam = 'S22'
        self.vna.power = self.power_range[0]
        self.vna.numpoints = 3
        self.vna.powerstate = 1

        data_arr = np.zeros((self.power_numpoints, self.freq_numpoints))

        now = datetime.now()
        timestamp = now.strftime('%Y-%m-%d_%H%M%S')
        for i in range(self.power_numpoints):
            self.vna.power = self.power_range[i]
            time.sleep(.5)
            for f in range(self.freq_numpoints):
                thisfreq = self.freq_range[f]
                self.vna.minfreq = thisfreq
                self.vna.maxfreq = thisfreq

                self.fxngen.freq = float(thisfreq)/2
                time.sleep(.5)

                daq_data = self.daq.monitor([self.daq_input_label], 1, 1000)
                daq_data_average = np.mean(daq_data[self.daq_input_label])
                normalized_daq_data_average = daq_data_average/float(self.preamp_gain)

                data_arr[i, f] = normalized_daq_data_average

        self.save(timestamp, data_arr)

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
        ax.set_title(filename + ' preamp gain ', data.get(filename + '/preamp_gain'))
        cbar.set_label('DAQ voltage normalized by preamp gain')
        graph_path = filename.replace(".hdf5", "graph.png")
        fig.savefig(graph_path)
