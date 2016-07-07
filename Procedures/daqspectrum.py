from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import datetime
from time import strftime
import os
import re

class DaqSpectrum():
    def __init__(self, instruments=None, input_chan=None, measure_time=0.5, measure_freq=256000, averages=30):
        self.instruments = instruments
        if instruments == None:
            self.daq = None
            self.pa = None
        else:
            self.daq = instruments['daq']
            self.pa = instruments['preamp']
        
        for arg in ['input_chan', 'measure_time','measure_freq','averages']:
            setattr(self, arg, eval(arg))
        
        home = os.path.expanduser("~")
        self.path = home+'Dropbox (Nowack lab)\\TeamData\\Montana\\spectra\\'
        self.time = strftime('%Y-%m-%d_%H%M%S')
        
               
    def do(self):
        self.setup_preamp()
        self.notes = input('Notes for this spectrum: ')
    
        Nfft = int((self.measure_freq*self.measure_time / 2) + 1)
        psdAve = np.zeros(Nfft)
        
        for i in range(self.averages):
            self.V, self.t, a = self.daq.monitor('ai%i' %self.input_chan, self.measure_time, self.measure_freq)
            self.f, psd = signal.periodogram(self.V, self.measure_freq, 'blackmanharris')
            psdAve = psdAve + psd 
        
        psdAve = psdAve / self.averages # normalize by the number of averages
        self.psdAve = np.sqrt(psdAve) # spectrum in V/sqrt(Hz)
        
        self.setup_plots()
        self.plot_loglog()
        self.plot_semilog()
            
        self.save()
        
    def load(self, filename):
        self.f, self.psdAve = np.loadtxt(filename, delimiter = ',')
        #define a regular expression that looks like a date and time
        timeStamp = "20[0-9][0-9]-[0-1][0-9]-[0-3][0-9]_[0-2][0-9][0-6][0-9][0-6][0-9]"
        re.compile(timeStamp)
        reMatch = re.search(timeStamp, filename)
        self.time = reMatch.group()
        
    def plot_loglog(self, calibration=None):
        self.ax_loglog.loglog(self.f, self.psdAve)
            
    def plot_semilog(self):           
        self.ax_semilog.semilogy(self.f, self.psdAve)

    def save(self):
        traceName = self.path + self.time + '_trace.csv'
        fftName = self.path + self.time + '_fft.csv'

        np.savetxt(fftName, (self.f, self.psdAve), delimiter=',')
        np.savetxt(traceName, (self.t, self.V), delimiter=',')
        
        self.fig_loglog.savefig(self.path+self.time+'_loglog.pdf')
        self.fig_semilog.savefig(self.path+self.time+'_semilog.pdf')
      
    def setup_plots(self):
        self.fig_loglog = plt.figure(figsize=(6,6))
        self.ax_loglog = self.fig_loglog.add_subplot(111)
        
        self.fig_semilog = plt.figure(figsize=(6,6))
        self.ax_semilog = self.fig_semilog.add_subplot(111)
        
        for ax in (self.ax_loglog, self.ax_semilog):
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel(r'Power Spectral Density ($\mathrm{V/\sqrt{Hz}}$)')
            #apply a timestamp to the plot
            ax.annotate(self.time, xy=(0.02,.98), xycoords='axes fraction', fontsize=10,
            ha='left', va = 'top', family='monospace')
            ax.set_title(self.notes)

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
        ax.set_xlim([1, 200000])
        #annotate the plot with the timestamp
        ax.annotate(self.time, xy=(0.005, 1.02), xycoords='axes fraction', fontsize=10, family='monospace')
        #generate the name of the plot from the initial filename
        figPathPng = os.path.splitext(fname)[0] + '.png'
        figPathPdf = os.path.splitext(fname)[0] + '.pdf'
        plt.savefig(figPathPng, dpi=400)
        plt.savefig(figPathPdf)
        return figPathPng

    def setup_preamp(self):
        self.pa.gain = 1
        self.pa.filter = (0, 100e3)
        self.pa.dc_coupling()
        self.pa.diff_input(False)
        self.pa.filter_mode('low',12)
