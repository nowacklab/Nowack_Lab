from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import datetime #probably dont need to import datetime and time
import time
from datetime import datetime
import os
import re
from ..Instruments import nidaq, preamp
from ..Utilities.save import Measurement, get_todays_data_path

_home = os.path.expanduser("~")
DATA_FOLDER = get_todays_data_path()

class DaqSpectrum(Measurement):
    def __init__(self, instruments=None, input_chan=None, measure_time=0.5, measure_freq=256000, averages=30):
        self.instruments = instruments
        if instruments:
            self.daq = instruments['nidaq']
            self.pa = instruments['preamp']
        else:
            self.daq = None
            self.pa = None
            print('Instruments not loaded... can only plot!')

        self.input_chan = 'ai%i' %input_chan
        for arg in ['measure_time','measure_freq','averages']:
            setattr(self, arg, eval(arg))

        ## So plotting will work with no data
        self.f = 1
        self.V = 1
        self.t = 1
        self.psdAve = 1

        self.filename = ''
        self.notes = ''

    def __getstate__(self):
        super().__getstate__() # from Measurement superclass,
                               # need this in every getstate to get save_dict
        self.save_dict.update({"timestamp": self.timestamp,
                          "V": self.V,
                          "t": self.t,
                          "f": self.f,
                          "psdAve": self.psdAve,
                          "averages": self.averages,
                          "measure_time": self.measure_time,
                          "measure_freq": self.measure_freq,
                          "averages": self.averages,
                          "notes": self.notes,
                          "daq": self.daq,
                          "pa": self.pa
                      })
        return self.save_dict

    def do(self):
        #record the time when the measurement starts
        super().make_timestamp_and_filename('spectra')

        self.setup_preamp()

        Nfft = int((self.measure_freq*self.measure_time / 2) + 1)
        psdAve = np.zeros(Nfft)

        for i in range(self.averages):
            received = self.daq.monitor(self.input_chan, self.measure_time,
                                        sample_rate=self.measure_freq
                                    )
            self.V = received[self.input_chan] #extract data from the required channel
            self.t = received['t']
            self.f, psd = signal.periodogram(self.V, self.measure_freq, 'blackmanharris')
            psdAve = psdAve + psd

        psdAve = psdAve / self.averages # normalize by the number of averages
        self.psdAve = np.sqrt(psdAve) # spectrum in V/sqrt(Hz)

        self.notes = input('Notes for this spectrum: ')

        self.setup_plots()
        self.plot_loglog()
        self.plot_semilog()

        self.save()


    def plot(self):
        try:
            self.ax_loglog # see if this exists
        except:
            self.setup_plots()
        self.plot_loglog()
        self.plot_semilog()


    def plotLog(self, fname, calibration=None):
        '''
        Generate a log-log plot of spectrum. If there is a known calibration between RMS voltage noise and flux noise, the plot is generated in units of flux quanta. Use daqspectrum.load to get all the data before calling plotLog

        calibration should be in units of Phi_o/V
        '''
        self.load(fname)
        fig, ax = plt.subplots(figsize=(5,5))
        #if a calibration is provided, rescale the y axis
        #also label with appropriate units
        if calibration:
            self.psdAve = self.psdAve / calibration
            ax.set_ylabel(r'Flux Noise ($\mathrm{\Phi_o/\sqrt{Hz}}$)')
        else:
            ax.set_ylabel(r'RMS Voltage Noise ($V_{rms}/\sqrt{Hz}$)')
        ax.loglog(self.f, self.psdAve)
        ax.set_xlabel(r'Frequency (Hz)')
        ax.set_xlim([0, 200000])
        #annotate the plot with the timestamp
        ax.annotate(self.timestamp, xy=(0.005, 1.02), xycoords='axes fraction', fontsize=10, family='monospace')
        #generate the name of the plot from the initial filename
        figPathPng = os.path.splitext(fname)[0] + '.png'
        figPathPdf = os.path.splitext(fname)[0] + '.pdf'
        plt.savefig(figPathPng, dpi=400)
        plt.savefig(figPathPdf)
        return figPathPng


    def plot_loglog(self, calibration=None):
        self.ax_loglog.loglog(self.f, self.psdAve)


    def plot_semilog(self):
        self.ax_semilog.semilogy(self.f, self.psdAve)


    def save(self, savefig=True):
        '''
        Saves the planefit object to json in .../TeamData/Montana/spectra/
        Also saves the figures as pdfs, if wanted.
        '''

        self.tojson(DATA_FOLDER, self.filename)

        if savefig:
            self.fig_loglog.savefig(os.path.join(DATA_FOLDER, self.filename)+'_loglog.pdf')
            self.fig_semilog.savefig(os.path.join(DATA_FOLDER, self.filename)+'_semilog.pdf')


    def setup_plots(self):
        self.fig_loglog = plt.figure(figsize=(6,6))
        self.ax_loglog = self.fig_loglog.add_subplot(111)

        self.fig_semilog = plt.figure(figsize=(6,6))
        self.ax_semilog = self.fig_semilog.add_subplot(111)

        for ax in (self.ax_loglog, self.ax_semilog):
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel(r'Power Spectral Density ($\mathrm{V/\sqrt{Hz}}$)')
            #apply a timestamp to the plot
            ax.annotate(self.timestamp, xy=(0.02,.98), xycoords='axes fraction', fontsize=10,
            ha='left', va = 'top', family='monospace')
            ax.set_title(self.notes)


    def setup_preamp(self):
        self.pa.gain = 1
        self.pa.filter = (0, 100e3)
        self.pa.dc_coupling()
        self.pa.diff_input(False)
        self.pa.filter_mode('low',12)
