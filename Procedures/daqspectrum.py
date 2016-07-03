from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
import datetime
from time import strftime
import os

class DaqSpectrum():
    def __init__(self, instruments, input_chan, measure_time=0.5, measure_freq=256000, averages=30):
        self.instruments = instruments
        self.daq = instruments['daq']
        self.pa = instruments['preamp']
        
        for arg in ['input_chan', 'measure_time','measure_freq','averages']:
            setattr(self, arg, eval(arg))
        
        home = os.path.expanduser("~")
        self.path = home+'Dropbox (Nowack lab)\\TeamData\\Montana\\spectra\\'
        self.time = strftime('%Y-%m-%d_%H%M%S')
        
        self.setup_preamp()
        
    def do(self):
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
        
    def plot_loglog(self):
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
        
    def setup_preamp(self):
        self.pa.gain = 1
        self.pa.filter = (0, 100e3)
        self.pa.dc_coupling()
        self.pa.diff_input(False)
        self.pa.filter_mode('low',12)