import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as sciopt
from scipy import signal
import time
from scipy import signal

import Nowack_Lab.Procedures.daqspectrum
reload(Nowack_Lab.Procedures.daqspectrum)
from Nowack_Lab.Procedures.daqspectrum import DaqSpectrum
from Nowack_Lab.Procedures.daqspectrum import TwoSpectrum

import Nowack_Lab.Utilities.save
reload(Nowack_Lab.Utilities.save)
from Nowack_Lab.Utilities.save import Measurement

import Nowack_Lab.Utilities.geophones
reload(Nowack_Lab.Utilities.geophones)
from Nowack_Lab.Utilities.geophones import Geophone
from Nowack_Lab.Utilities.geophones import Geophone_cal

import Nowack_Lab.Utilities.welch
reload(Nowack_Lab.Utilities.welch)
from Nowack_Lab.Utilities.welch import Welch

class Geophone_calibrate(Measurement):
    _daq_inputs = ['inA', 'inB']
    _daq_outputs= ['out']
    _instrument_list = ['daq']

    Zi = 10e9
    arg0 = [4.5, 2, 380, .1, 33**2/.023]

    def __init__(self, instruments={}, Rs=340, sample_rate=1000, maxV = .2, numpts = 8191, 
            inputfnct = 'heaviside'):
        '''
        Arguments:
        Rs(float): resistor used as divider with geophone
        sample_rate(float): rate of measurement in Hz.  Total time
                            of measurement is 8191/sample_rate
        '''
        super().__init__(instruments=instruments)
        self.Rs = Rs
        self.sample_rate = sample_rate
        self.maxV = maxV
        self.numpts = numpts
        self.inputfnct = inputfnct
        self.geophone_cal = Geophone_cal(Rs)

    def do(self):
        # send random noise signal and montor the input channels
        if self.inputfnct == 'uniform':
            noise = np.random.uniform(-self.maxV,self.maxV,self.numpts) # noise
        if self.inputfnct == 'linear':
            noise = np.linspace(-self.maxV,self.maxV,self.numpts) # linear (debug)
        if self.inputfnct == 'heaviside':
            noise = np.sign(np.linspace(-1,1,self.numpts))*self.maxV + self.maxV   # heaviside
        if self.inputfnct == 'delta':
            noise = -.2*np.ones(self.numpts); 
            noise[int(self.numpts/2)  ] = .2 #delta
        self.daq.outputs['out'].V = noise[0]
        time.sleep(1)
        data = {'out': noise}
        received = self.daq.send_receive(data, chan_in=['inA', 'inB'], 
                                         sample_rate=self.sample_rate)
        self.Va = received['inA']
        self.Vb = received['inB']
        self.t  = received['t']

        # Should I fourier transform first?  welch it?

        # Ratio of the input voltages should look like rho
        # fit to rho with parameters

        # this was wrong, should be the ratio of the 
        # fourier transforms, not the time traces
        #self.ratio = self.Vb/self.Va 
        #self.f, self.ratiopsd = signal.welch(self.ratio, fs=self.sample_rate)

        self.f, self.Vapsd = self.makepsd(self.Va, .5)
        self.f, self.Vbpsd = self.makepsd(self.Vb, .5)
        self.ratiopsd = self.Vbpsd/self.Vapsd

        self.dft = np.sqrt(self.ratiopsd)

        self.plot_debug()

        self.popt, self.pcov = self.geophone_cal._calfit(self.f, self.dft, p0=self.arg0)

        self.plot()

    def makepsd(self, timetrace, freqspace):
        [window, nperseg] = self._makewindow(freqspace)
        [f, psd] = signal.welch(timetrace, fs=self.sample_rate,
                                          window=window, nperseg=nperseg)
        return f,psd

    def _makewindow(self, freqspace):
        #n = min(int(self.sample_rate/freqspace), self.numpts)
        n = int(max(256, self.sample_rate / freqspace))
        return [signal.blackmanharris(n, False), n]


    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('Hz')
        self.ax.set_ylabel(r'Frequency Response (V/$\sqrt{\rm Hz}$)')
        self.ax.annotate(self.timestamp, xy=(.02,.98), xycoords='axes fraction',
                         fontsize=10, ha='left', va='top', family='monospace')

    def plot(self):
        self.ax.loglog(self.f, self.dft, marker='o', linestyle='', label='data')
        ylims = self.ax.get_ylim()

        xdata = np.linspace(1/self.sample_rate, self.sample_rate, 1000)
        self.ax.loglog(xdata, self.rho(xdata, *self.popt), label='fit')

        self.ax.set_ylim(ylims)
        self.ax.legend()

    def plot_debug(self):
        fig,ax, = plt.subplots()
        ax.plot(self.t, self.Va, label='Va')
        ax.plot(self.t, self.Vb, label='Vb')
    #    ax.plot(self.t, self.ratio, label='Vb/Va')
        ax.legend()

    def print_params(self):
        names = ['f0', 'Q0', 'Rt', 'Lt']
        for n,i in zip(names, range(len(names))):
            print(r"{2}: {0:f} $\pm$ {1:f}".format(self.popt[i], self.pcov[i], n))
        print(r"L12: {0:f} $\pm$ {1:f}".format((self.popt[4]*.023)**.5, 
                                               (self.pcov[4]*.023)**.5, n))

class Geophone_calibrate_fnctgen(Geophone_calibrate):
    def __init__(self, instruments={}, Rs=340, measure_dur = 2, sample_rate=256000):
        super().__init__(instruments=instruments, Rs=Rs, sample_rate=sample_rate, maxV=2,
                         numpts = sample_rate*measure_dur, inputfnct='heaviside')

class Geophone_calibrate_lockins(Geophone_calibrate):
    _instruments_list=['lockinA', 'lockinB'] # lockinA reads A and outputs into A, lockinB just reads

    def __init__(self, instruments={}, 
                 Rs=340, minf=.1, 
                 maxf=1000, numpts=1000):
        super().__init__(instruments=instruments, Rs=Rs, sample_rate='N/A', maxV='N/A', numpts=numpts,
                        inputfnct='N/A')
        self.freqs = 10**np.linspace(np.log10(minf), np.log10(maxf), numpts)

    def do(self):
        self.Var = []
        self.Vat = []
        self.Vbr = []
        self.Vbt = []
        self.isol = []
        self.guessETC()
        for f in self.freqs:
            self.lockinA.frequency = f
            tcguess = (1/f)*10
            closests = np.array(self.lockinA._time_constant_values) - tcguess
            tcguess_i = np.argmin(closests - 30000*np.sign(closests))
            tc = self.lockinA._timeconstant_values[tcguess_i]
            self.lockinA.time_constant = tc
            self.lockinB.time_constant = tc
            self.isol.append((self.lockinA.is_OL(), self.lockinB.is_OL()))
            sleep(tc*10)
            self.Var.append(self.lockinA.R)
            self.Vat.append(self.lockinA.theta)
            self.Vbr.append(self.lockinB.R)
            self.Vbt.append(self.lockinB.theta)
            self.Vax.append(self.lockinA.X)
            self.Vay.append(self.lockinA.Y)
            self.Vbx.append(self.lockinB.X)
            self.Vby.append(self.lockinB.Y)
        self.Var = np.array(self.Var)
        self.Vat = np.array(self.Vat)
        self.Vbr = np.array(self.Vbr)
        self.Vbt = np.array(self.Vbt)
        self.Vax = np.array(self.Vax)
        self.Vay = np.array(self.Vay)
        self.Vbx = np.array(self.Vbx)
        self.Vby = np.array(self.Vby)
        self.impedence_r = (self.Vbr/(self.Var-Vbr)*self.Rs)
        self.impedence_t = (self.Vbt/(self.Vat-Vbt)*self.Rs)
        self.impedence_x = (self.Vbx/(self.Vax-Vbx)*self.Rs)
        self.impedence_y = (self.Vby/(self.Vay-Vby)*self.Rs)

    def fit_z_rt(self):
        self.z_abs = lambda f, f0, q0, rt, lt, z12: np.abs(
                    self.geophone_cal._Ze(
                        f, f0, q0, rt, lt, z12
                    )
                )
        self.z_pha = lambda f, f0, q0, rt, lt ,z12: np.angle(
                    self.geophone_cal._Ze(
                        f, f0, q0, rt, lt, z12
                    )
                )
        self.popt_abs, self.pcov_abs = curve_fit(
                self.z_abs, self.freqs, self.impedence_r, p0=self.geophone_cal.arg0)
        self.popt_pha, self.pcov_pha = curve_fit(
                self.z_pha, self.freqs, self.impedence_t, p0=self.geophone_cal.arg0)

    def plot_z(self):
        fig,ax_abs = plt.subplots()
        fs = np.linspace(self.freqs[0], self.freqs[-1], 1000)
        ax.loglog(self.freqs, self.impedence_r)
        ax.loglog(fs, self.z_abs(fs, *(self.popt_abs)))
        fig,ax_pha = plt.subplots()
        ax.loglog(self.freqs, self.impedence_a, self.z_pha(fs, *(self.popt_abs)))
        ax.loglog(fs, self.z_pha(fs, *(self.popt_abs)))
        return [ax_abs, ax_pha]


    def guessETC(self):
        tcguess = (1/self.freqs)*10
        tcs = []

        for tg in tcguess:
            closests = np.array(self.lockinA._time_constant_values) - tg
            tg_i = np.argmin(closests - 30000*np.sign(closests))
            tc = self.lockinA._timeconstant_values[tcguess_i]
            tcs.append(tc)

        print('Estimated Time to Completion: {0}s'.format(sum(tcs)*10))

class Geophone_calibrate_zurich(Geophone_calibrate_lockins):
    _instruments_list=['zurich'] 

    def __init__(self, instruments={}, minf=.1, maxf=1000, numpts=1000):
        super().__init__(instruments=instruments, Rs='N/A', sample_rate='N/A', maxV='N/A', numpts=numpts,
                        inputfnct='N/A')
        self.freqs = 10**np.linspace(np.log10(minf), np.log10(maxf), numpts)

    def do(self):
        pass
    

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

    def do(self, notes=False):
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
        if notes:
            self.notes = input('Enter notes:\n')
            self.spectra.notes = self.notes
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
        self.ax[2].set_xlabel('Hz')
        for a in self.ax:
            a.set_ylabel('Acceleration (m/s/s)')
            a.annotate(self.timestamp, xy=(.02,.98), 
                         xycoords='axes fraction',
                         fontsize=10, ha='left', va='top', 
                         family='monospace')

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

