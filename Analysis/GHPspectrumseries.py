'''
Functions to calculate and plot noise figures from a series of spectra taken
versus gate voltage.
'''
import matplotlib.pyplot as plt, numpy as np
from ..Measurements.spectrum import ZurichSpectrum
from ..Utilities.save import Saver

class SpectrumSeries(Saver):
    def __init__(self, Vtgs, Vbias, paths):
        '''
        Parameters:
        Vtgs: array of topgate voltages (V)
        Vbias: current bias (uA)
        paths: list of paths of ZurichSpectrum objects
        '''
        self.Vtgs = Vtgs
        self.Vbias = Vbias
        self.paths = paths

    def get_averages(self, fmin=0, fmax=None):
        '''
        Averages the spectrum over frequency range (fmin, fmax) (Hz) to obtain
        an average voltage spectral density for the spectrum. Also averages the
        timetrace to obtain an average DC voltage. Also takes the input current
        of the keithley used to bias the sample.
        '''
        Vav = []
        Ibias = []
        Vn = []

        for j, Vtg in enumerate(self.Vtgs):
            self.zs = ZurichSpectrum.load(self.paths[j])
            zs = self.zs
            Vav.append(np.array(zs.timetraces_V).mean())
            Ibias.append(zs.kbias.input_current)
            Vn.append(zs.get_average(fmin, fmax))

        self.Vav = np.array(Vav)
        self.Ibias = np.array(Ibias)
        self.Vn = np.array(Vn)


    def get_one_over_f(self, fmin=.1, fmax=None, filters=[60], filters_bw=[10]):
        '''
        Gets the fit parameters to A/f^alpha (using fit_one_over_f in ZurichSpectrum)
        over the frequency range (fmin, fmax) (Hz).
        '''
        As = []
        alphas = []

        for j, Vtg in enumerate(self.Vtgs):
            self.zs = ZurichSpectrum.load(self.paths[j])
            zs = self.zs
            A, alpha = zs.fit_one_over_f(fmin, fmax, filters=[60], filters_bw=[10])
            As.append(A)
            alphas.append(alpha)

        self.As = np.array(As)
        self.alphas = np.array(alphas)


    def plot(self):
        '''
        Plots Vav/Ibias and Vn versus topgate voltage.
        '''
        self.fig, self.ax = plt.subplots()
        self.ax.set_title('%.2f $\mu$A bias' %self.Vbias)
        self.ax.plot(self.Vtgs, self.Vav/self.Ibias)
        self.ax.set_xlabel('Vtg (V)')
        self.ax.set_ylabel('Vav/Ibias ($\Omega$)')

        self.ax2 = self.ax.twinx()
        self.ax2.semilogy(self.Vtgs, self.Vn, 'C1')
        self.ax2.set_ylabel('Average spectral density (V/Hz$^{1/2}$)', color='C1')
        self.fig.tight_layout()

    def plot_single_spectrum(self, idx):
        '''
        Plots a full single spectrum versus frequency
        idx: index (from topgate voltage array)
        '''
        fig, ax = plt.subplots()
        ax.set_title('%.2f $\mu$A bias, %.3f Vtg' %(self.Vbias, self.Vtgs[idx]))
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('Voltage spectral density (V/Hz$^{1/2}$)')

        self.zs = ZurichSpectrum.load(self.paths[idx])
        zs = self.zs
        ax.loglog(zs.f, zs.Vn)

        return fig, ax
