from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os
import re
from ..Instruments import nidaq #, preamp
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict

class DaqSpectrum(Measurement):
    _chan_labels = ['dc'] # DAQ channel labels expected by this class
    #instrument_list = ['daq','preamp']
    instrument_list = ['daq']
    ## So plotting will work with no data
    f = 1
    V = 1
    t = 1
    psdAve = 1

    def __init__(self, instruments={}, measure_time=0.5, measure_freq=256000, averages=30,
                 gain = 2000, phi0persqrthz = False, conv_VperPhi0 = 1.5):
        super().__init__()


        self._load_instruments(instruments)
        self.gain = gain
        self.conv_VperPhi0 = conv_VperPhi0;
        self.phi0persqrthz = phi0persqrthz;

        for arg in ['measure_time','measure_freq','averages']:
            setattr(self, arg, eval(arg))


    def do(self):
        #self.setup_preamp()

        self.psdAve = self.get_spectrum()
        print("Scan Done")

        self.plot()
        self.save()


    def get_spectrum(self):
        Nfft = int((self.measure_freq*self.measure_time / 2) + 1)
        psdAve = np.zeros(Nfft)

        for i in range(self.averages):
            received = self.daq.monitor('dc', self.measure_time,
                                        sample_rate=self.measure_freq
                                    )
            self.V = received['dc']/self.gain #extract data from the required channel
            self.t = received['t']
            self.f, psd = signal.periodogram(self.V, self.measure_freq,
                                             'blackmanharris')
            psdAve = psdAve + psd

        psdAve = psdAve / self.averages # normalize by the number of averages

        return np.sqrt(psdAve) # spectrum in V/sqrt(Hz)


    def get_overalllevel(self):
        '''
        Average voltage level with averaging for calibration.
        Outputs a single voltage and saves the end average/std, and the
        average/std for each averaged scan.
        '''
        Nfft = int((self.measure_freq*self.measure_time / 2) + 1)
        psdAve = np.zeros(Nfft)
        self.cal_v = [];
        self.cal_std = [];
        for i in range(self.averages):
            received = self.daq.monitor('dc', self.measure_time,
                                        sample_rate=self.measure_freq
                                    )
            vs = received['dc']/self.gain;
            ts = received['t'];
            v = np.mean(vs);
            std = np.std(vs);
            self.cal_v.append(v);
            self.cal_std.append(std);

        self.cal_avev = np.mean(self.cal_v);
        self.cal_avevstd = np.std(self.cal_v);

        self.save();

        return [self.cal_avev, self.cal_avevstd, self.cal_std];


    def plot(self):
        super().plot()
        if(self.phi0persqrthz):
            self.ax['loglog'].loglog(self.f, self.psdAve/self.conv_VperPhi0);
            self.ax['semilog'].semilogy(self.f, self.psdAve/self.conv_VperPhi0);
        else:
            self.ax['loglog'].loglog(self.f, self.psdAve)
            self.ax['semilog'].semilogy(self.f, self.psdAve)

    def plotLog(self, fname, calibration=None):
        '''
        Generate a log-log plot of spectrum. If there is a known calibration
        between RMS voltage noise and flux noise, the plot is generated in units
        of flux quanta. Use daqspectrum.load to get all the data before calling
        plotLog.

        calibration should be in units of Phi_o/V

        THIS MAY NOT WORK ANYMORE
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


    def setup_plots(self):
        self.fig = plt.figure(figsize=(12,6))
        self.ax = AttrDict()
        self.ax['loglog'] = self.fig.add_subplot(121)
        self.ax['semilog'] = self.fig.add_subplot(122)

        for ax in self.ax.values():
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel(r'Power Spectral Density ($\mathrm{V/\sqrt{Hz}}$)')
            if(self.phi0persqrthz):
                ax.set_ylabel(
                    r'Power Spectral Density ($\mathrm{\phi_0/\sqrt{Hz}}$)');
            #apply a timestamp to the plot
            ax.annotate(self.timestamp, xy=(0.02,.98), xycoords='axes fraction',
                fontsize=10, ha='left', va = 'top', family='monospace'
            )



    def setup_preamp(self):
        if not hasattr(self, 'preamp') or self.preamp is None:
            print('No preamp!')
            return
        self.preamp.gain = 1
        self.preamp.filter = (0, 100e3)
        self.preamp.dc_coupling()
        self.preamp.diff_input(False)
        self.preamp.filter_mode('low',12)
