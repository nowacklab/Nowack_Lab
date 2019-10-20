import numpy as np
import matplotlib.pyplot as plt
import os, time, math

from importlib import reload
from datetime import datetime

# Nowack_Lab imports
from Nowack_Lab.Utilities import dataset
from Nowack_Lab.Utilities.dataset import Dataset
from Nowack_Lab.Instruments.VNA import VNA8722ES
from Nowack_Lab.Instruments.keithley import Keithley2400
from Nowack_Lab.Procedures.rf_sweep import *

class RF_sweep_current_graph_analyzer:
    """Contains (static) methods for inspecting/analyzing/replotting graphs
    from datasets produced by RF_sweep_current"""

    @staticmethod
    def plotPhase(filename, rev=False):
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
       Y,X = np.meshgrid(freq, current)
       phase = RF_sweep_current.phase_data(filename, rev = rev)
       im=ax.pcolor(X, Y, phase, cmap="viridis")
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

    @staticmethod
    def single_freq_linecut_phase(filename, single_frequency, current_near, rev=False):
        fig, ax = plt.subplots(1,1, figsize=(10,6))
        data = dataset.Dataset(filename)

        current_numpoints = data.get(filename + '/Isteps')
        current_min = data.get(filename + '/Istart')
        current_max = data.get(filename+ '/Istop')
        print("current numpoints: " + str(current_numpoints))
        print(current_min)
        print(current_max)
        print(current_near)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart')*1000,
                        data.get(filename + '/Istop')*1000,
                        data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop')*1000,
                        data.get(filename + '/Istart')*1000,
                        data.get(filename + '/Isteps'))

        minfreq = data.get(filename + '/freqmin')
        maxfreq = data.get(filename + '/freqmax')
        numfreqpoints = data.get(filename + '/numpoints')
        freq = np.linspace(minfreq/1e9,
                    maxfreq/1e9,
                    numfreqpoints)

        phase = RF_sweep_current.phase_data(filename, rev = rev) # phase data
        phase_data_shape = np.shape(phase)
        single_frequency_index = int(float(single_frequency)/1e9/(maxfreq-minfreq)*numfreqpoints)
        cut_phase = phase[:, single_frequency_index]

        current_index1 = int((current_near-current_min)/(current_max-current_min)*current_numpoints-current_numpoints/20)
        current_index2 = int((current_near-current_min)/(current_max-current_min)*current_numpoints+current_numpoints/20)

        plt.plot(current[current_index1:current_index2], cut_phase[current_index1:current_index2])
        plt.title("At frequency %.3f Reflected phase shift vs. current" %(single_frequency/1e9))
        plt.ylabel("phase shift")
        plt.xlabel("current")
        plt.ylim(-90, 90)

    @staticmethod
    def plotdB(filename, rev=False):
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
        Y,X = np.meshgrid(freq, current)
        dB = RF_sweep_current.dB_data(filename, rev = rev)
        im=ax.pcolor(X, Y, dB, cmap="viridis")
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
    def plotdB_currentx10(filename, rev=False):
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        data = dataset.Dataset(filename)
        if not rev:
            current = np.linspace(data.get(filename + '/Istart')*10000,
                        data.get(filename + '/Istop')*10000,
                        data.get(filename + '/Isteps'))
        else:
            current = np.linspace(data.get(filename + '/Istop')*10000,
                        data.get(filename + '/Istart')*10000,
                        data.get(filename + '/Isteps'))
        freq = np.linspace(data.get(filename + '/freqmin')/1e9,
                    data.get(filename + '/freqmax')/1e9,
                    data.get(filename + '/numpoints'))
        Y,X = np.meshgrid(freq, current)
        dB = RF_sweep_current.dB_data(filename, rev = rev)
        im=ax.pcolor(X, Y, dB, cmap="viridis")
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
            graph_path = filename.replace(".hdf5", "db_currentx10.png")
        else:
            graph_path = filename.replace(".hdf5", "db_rev_currentx10.png")
        fig.savefig(graph_path)
