import numpy as np
import matplotlib.pyplot as plt

from .daqspectrum import DaqSpectrum
from .daqspectrum import TwoSpectrum
from ..Utilities.save import Measurement



class Geophone_sr5113(Measurement):
    _daq_inputs = ['dc']
    _instrument_list = ['daq', 'preamp']

    def __init__(self, instruments={}, 
                 measure_time=1, 
                 measure_freq=256000, 
                 averages=30,
                 preamp_diff_mode=False,
                 conversion=31.5 # V/ (m/s)
                 ):
        '''
        '''
        super().__init__(instruments=instruments)
        self.instruments = instruments
        self.measure_time = measure_time
        self.measure_freq = measure_freq
        self.averages = averages
        self.preamp_diff_mode = preamp_diff_mode
        self.conversion = conversion

        self.geo = Geophone(conversion=self.conversion)

    def do(self):
        self.daqspectrum = DaqSpectrum(instruments=self.instruments,
                                       measure_time=self.measure_time,
                                       measure_freq=self.measure_freq,
                                       averages=self.averages,
                                       preamp_gain_override=True,
                                       preamp_filter_override=True,
                                       preamp_dccouple_override=True,
                                       preamp_autoOL=False,
                                       preamp_diff_mode=self.preamp_diff_mode
                                       )
        self.daqspectrum.run(welch=True)

        self.psd = self.daqspectrum.psd
        self.f   = self.daqspectrum.f

        [self.acc, self.vel, self.pos] = self.geo.convert(np.sqrt(self.psd), 
                                                          self.f)

        self.rewelch(1/self.averages)
        self.rewelch(1)

        #self.plot()

    def rewelch(self, freqspace):
        '''
        changes the frequency bins
        '''
        self.daqspectrum.makepsd(freqspace)
        self.psd = self.daqspectrum.psd
        self.f   = self.daqspectrum.f
        [self.acc, self.vel, self.pos] = self.geo.convert(np.sqrt(self.psd), 
                                                          self.f)

        self.plot()
        

    def setup_plots(self):
        self.fig, self.ax = plt.subplots(3,2, figsize=(15,15))
        self.ax = list(self.ax.flatten() )

        self.ax[0].set_ylabel(r'Position' '\n' r'$\mu$m/$\sqrt{\rm Hz}$')
        self.ax[2].set_ylabel(r'Velocity' '\n' r'($\mu$m/s)/$\sqrt{\rm Hz}$')
        self.ax[4].set_ylabel(r'Acceleration' '\n' 
                              r'($\mu$m/s/s)/$\sqrt{\rm Hz}$')
        
        self.ax[4].set_xlabel('Frequency (Hz)')
        self.ax[5].set_xlabel('Frequency (Hz)')

        for ax in self.ax:
            ax.annotate(self.timestamp, xy=(.02,.98), xycoords='axes fraction',
                        fontsize=10, ha='left', va='top', family='monospace')

        plt.tight_layout()

    def plot(self):
        self.ax[0].semilogy(self.f, self.pos*1e6)
        self.ax[1].loglog(self.f, self.pos*1e6)
        self.ax[2].semilogy(self.f, self.vel*1e6)
        self.ax[3].loglog(self.f, self.vel*1e6)
        self.ax[4].semilogy(self.f, self.acc*1e6)
        self.ax[5].loglog(self.f, self.acc*1e6)

        for a in self.ax:
            a.set_xlim([0,1000])


class GeophoneAccelerometer(Geophone_sr5113):
    '''
    Compare geophone and accelerometer
    '''
    _daq_inputs = ['dc', 'dc2']
    _instrument_list = ['daq', 'preamp']
    def __init__(self, nonpreamp_gain, *args, 
                accelerometerconv = .1024, #.1024 V/ (m/s/s)
                instruments={},
                **kwargs
                ):
        '''
        Compares geophones and accelerometer.

        Inputs:
        nonpreamp_gain (float): the gain on the accelerometer box
        accelerometerconv (float): conversion factor,  V/(m/s/s)
        '''
        super().__init__(*args, instruments=instruments, **kwargs)
        self.nonpreamp_gain = nonpreamp_gain
        self.accelerometerconv = accelerometerconv

    def do(self):
        self.spectra = TwoSpectrum(self.nonpreamp_gain, 
                                   instruments=self.instruments,
                                   measure_time=self.measure_time,
                                   measure_freq=self.measure_freq,
                                   averages=self.averages,
                                   preamp_gain_override=True,
                                   preamp_filter_override=True,
                                   preamp_dccouple_override=True,
                                   preamp_autoOL=False,
                                   preamp_diff_mode=self.preamp_diff_mode
                                   )
        self.spectra.run()
        self._populate()
        self.plot()

    def rewelch(self, freq):
        '''
        Change frequency bins and populate the local attributes
        '''
        self.spectra.makepsd(freq)
        self._populate()

    def _populate(self):
        '''
        Populate local geophone and accelerometer attributes
        '''
        [self.geo_acc, self.geo_vel, self.geo_pos] = self.geo.convert(
                                           self.spectra.psdAve1, 
                                           self.spectra.f1)
        self.geo_f = self.spectra.f1

        self.acc_acc = self.spectra.psdAve2/self.accelerometerconv
        self.acc_f = self.spectra.f2

        for name in ['geo_acc', 'geo_vel', 'geo_pos', 'geo_f',
                      'acc_acc', 'acc_f']:
            setattr(self, name, getattr(self, name)[1:])


    def setup_plots(self):
        self.fig, self.ax = plt.subplots(3,1,figsize=(12,8))
        self.ax = list(self.ax.flatten())

    def clearplot(self):
        '''
        Clear all axes
        '''
        self.ax[0].cla()
        self.ax[1].cla()
        self.ax[2].cla()

    def plot(self):
        self.ax[0].loglog(self.geo_f, self.geo_acc, label='geophone')
        self.ax[0].loglog(self.acc_f, self.acc_acc, label='accelerometer')
        self.ax[1].set_xlim([self.geo_f[0], 2000])
        self.ax[1].set_ylim([
            self.min2(self.geo_acc, self.acc_acc, self.geo_f, self.geo_f[0]),
            self.max2(self.geo_acc, self.acc_acc, self.geo_f, 2000)]),
        self.ax[1].semilogx(self.geo_f, self.geo_acc, label='geophone')
        self.ax[1].semilogx(self.acc_f, self.acc_acc, label='accelerometer')
        self.ax[2].set_xlim([0,100])
        self.ax[2].set_ylim([
            self.min2(self.geo_acc, self.acc_acc, self.geo_f, self.geo_f[0]),
            self.max2(self.geo_acc, self.acc_acc, self.geo_f, 100)]),
        self.ax[2].plot(self.geo_f, self.geo_acc, label='geophone')
        self.ax[2].plot(self.acc_f, self.acc_acc, label='accelerometer')
        
        self.ax[1].legend()

    def max2(self, sety1, sety2, setx, targetx):
        '''
        Returns the value of sety1, sety2 that has the highest
        value from the first value in the array to the index
        where targetx occurs in setx
        '''
        maxi = np.abs((setx-targetx)).argmin()
        return max(sety1[0:maxi+1].max(), sety2[0:maxi+1].max())

    def min2(self, sety1, sety2, setx, targetx):
        '''
        Returns the value of sety1, sety2 that has the lowest
        value from the first value in the array to the index
        where targetx occurs in setx
        '''
        mini = np.abs((setx-targetx)).argmin()
        return min(sety1[0:mini+1].min(), sety2[0:mini+1].min())

class Geophone(object):
    '''
    Conversions for geophones
    '''
    conversion = 0
    c_acc = lambda f, G: np.abs(G * 2j*np.pi*f /
                                ((2j*np.pi*f)**2 + 18*2j*np.pi*f + 760))
    c_vel = lambda f, G: np.abs(G * (2j*np.pi*f)**2 /
                                ((2j*np.pi*f)**2 + 18*2j*np.pi*f + 760))
    c_pos = lambda f, G: np.abs(G * (2j*np.pi*f)**3 /
                                ((2j*np.pi*f)**2 + 18*2j*np.pi*f + 760))

    def __init__(self, 
                 conversion=31.5 # V/(m/s)
                 ):
        self.conversion = conversion

    def convert(self, psd_V, f):
        '''
        Converts the psd in f space from volts to 
        [acceleration, velocity, position]
        '''
        acc = psd_V / self.__class__.c_acc(f, self.conversion)
        vel = psd_V / self.__class__.c_vel(f, self.conversion)
        pos = psd_V / self.__class__.c_pos(f, self.conversion)

        return [acc, vel, pos]
