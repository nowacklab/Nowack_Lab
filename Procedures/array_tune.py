"""
# Limit the number of attempts @ each tuning step
# Figure out when resets are required
# Record traces when tuning is done
Add offset to lock point  (not just the mean)
"""
from matplotlib import pyplot as plt
import numpy as np
from importlib import reload
import matplotlib.cm
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.signal import savgol_filter

import sys

import Nowack_Lab.Utilities.save
reload(Nowack_Lab.Utilities.save)
from Nowack_Lab.Utilities.save import Measurement

import Nowack_Lab.Utilities.utilities
reload(Nowack_Lab.Utilities.utilities)
from Nowack_Lab.Utilities.utilities import running_std

import Nowack_Lab.Procedures.daqspectrum
reload(Nowack_Lab.Procedures.daqspectrum)
from Nowack_Lab.Procedures.daqspectrum import SQUIDSpectrum

import Nowack_Lab.Procedures.mutual_inductance
reload(Nowack_Lab.Procedures.mutual_inductance)
from Nowack_Lab.Procedures.mutual_inductance import MutualInductance2


class ArrayTune(Measurement):
    instrument_list = ["daq", "squidarray", "preamp"]
    _daq_inputs = ["saa", "test"]
    _daq_outputs = []

    def __init__(self,
                 instruments,
                 squid_bias,
                 squid_tol = 100e-3,
                 aflux_tol = 10e-3,
                 sflux_offset = 0.0,
                 aflux_offset = 0.0,
                 conversion=1/1.44,
                 testsignalconv = 10,
                 debug=False):
        """
        Lock a SQUID automatically, given a locked SAA

        Constructor Parameters:
        -----------------------
        instruments (dict): Dictionary of instruments

        squid_bias (float): Bias point for SQUID lock

        squid_tol (float): Allowed DC offset for the locked SQUID
                           (SQUID locked)

        aflux_tol (float): Allowed DC offset from the desired lock point 
                           when choosing the SQUID lock point (Array locked)

        sflux_offset (float): Desired DC offset from 0 for the locked SQUID 
                              Aims to lock at this point, if the squid array
                              signal was centered at zero.
                              SQUID locked.
        
        aflux_offset (float): Desired DC offset from 0 for the SQUID 
                              characteristic used to find the desired lock
                              point.  (Array locked).  Aims for 
                              to lock at this point, if the characteristic
                              was centered at zero.
                             

        conversion (float): Conversion in phi_0/V for the locked SQUID. 
                            MED sensitivity
                            IBM: 1/1.44; HYPRES: .565

        testsignalconv (float): Conversion in uA/V for S_flux per test 
                                signal voltage.
                                Normal: 10; Dipping Probe: 30.3
                                
        debug (boolean): Print debug messages if True
        """
        super(ArrayTune, self).__init__(instruments=instruments)

        self.instruments = instruments
        self.squid_bias = squid_bias
        self.squid_tol = squid_tol
        self.aflux_tol = aflux_tol
        self.sflux_offset = sflux_offset
        self.aflux_offset = aflux_offset
        self.saaconversion = conversion # med
        self.testsignalconv = testsignalconv
        self.debug = debug

    def acquire(self):
        """Ramp the modulation coil current and monitor the SAA response."""

        usingtest = False #FIXME
        if usingtest:
            # Send TTL pulse on "test"
            data = {"test": 2*np.ones(2000)}
            # Record test
            ret = self.daq.send_receive(data, chan_in = ["saa", "test"],
                                    sample_rate=256000)
            # Zero the DAQ output
            self.daq.outputs["test"].V = 0
        else:
            ret = self.daq.monitor(["saa","test"], 0.01, 
                                    sample_rate = 256000)
        out = np.zeros((3, len(ret['t'])))
        out[0] = ret['t']
        out[1] = ret['test']
        out[2] = ret['saa']
        
        return out

    def tune_squid_setup(self):
        """
        Configure SAA for SQUID tuning.  Array locked, choose a place on 
        the SQUID characteristic to lock.
        """
        self.squidarray.lock("Array")
        #self.squidarray.S_flux_lim = 100
        #self.squidarray.S_flux = self.squidarray.S_flux_lim/2
        self.squidarray.testInput = "S_flux"
        self.squidarray.testSignal = "On"
        self.squidarray.S_bias = self.squid_bias
        self.squidarray.sensitivity = "High"
        self.squidarray.reset()

    @staticmethod
    def _midpoint(data):
        return (np.max(data) + np.min(data))/2

    def tune_squid(self, attempts=5):
        """
        Tune the SQUID and adjust the DC SAA flux.  Array locked,
        lock on a specific value of the SQUID characteristic.
        """
        self.tune_squid_setup()
        self.char = self.acquire()
        error = self._midpoint(self.char[-1]) + self.aflux_offset
        
        if self.debug:
            print('Tune_squid error:', error)
        if np.abs(error) < self.aflux_tol:
            return True
        elif attempts == 0:
            print("Cannot tune SQUID.  Cannot find good place on characteristic")
            return False
        else:
            self.adjust("A_flux", error)
            return self.tune_squid(attempts = attempts-1)

    def lock_squid(self, attempts=5):
        """
        Lock the SQUID and adjust the DC SQUID flux.
        Adjust the DC offset of the SQUID signal to be near
        zero to avoid overloading the preamp.
        """
        self.squidarray.lock("Squid")
        self.squidarray.testSignal = "Off"
        self.squidarray.reset()
        ret = self.daq.monitor(["saa"], 0.01, sample_rate = 256000)
        error = self._midpoint(ret["saa"]) + self.sflux_offset

        if self.debug:
            print('lock_squid error:', error)

        if np.abs(error) < self.squid_tol:
            print("locked with {} attempts".format(5-attempts))
            return True
        elif attempts == 0:
            print("Cannot lock SQUID. Cannot zero signal within squid_tol.")
            return False
        else:
            self.adjust("S_flux", error)
            return self.lock_squid(attempts - 1)

    def adjust(self, attr, error):
        """
        Adjust DC flux to center the trace @ 0 V.
        Called by lock_squid and tune_squid

        Parameters:
        -----------
        attr:   (string): parameter of squidarray to change

        error:  (float):  distance in V from desired point
        """
        value = getattr(self.squidarray, attr)

        conversion = -1/(self.calibrate_adjust(attr))  

        if self.debug:
            print('    adjusting {0}: error={1:3.3f}, {0}+={2:3.3f}'.format(
                        attr, error, error*conversion))

        if value + error * conversion < 0:
            # Force a jump by resetting
            setattr(self.squidarray, attr, value + 50)
        elif value + error * conversion > 150:
            setattr(self.squidarray, attr, 0)
        else:
            # Directly correct the offset
            setattr(self.squidarray, attr, value + conversion * error)
        
        self.squidarray.reset()

    def _getmean(self, monitortime):
        received = self.daq.monitor('saa', monitortime, sample_rate=256000)
        return np.mean(received['saa']), np.std(received['saa'])

    def calibrate_adjust(self, attr, monitortime=.25, step=10):
        """
        Create conversion factor for adjust in V/[attr]
        For a given step size, how much does the SAA signal change?

        Parameters:
        -----------
        attr (string): parameter of squidarray to change

        monitortime (float): time in seconds to monitor the saa signal

        step (float): step size to change attr
        """
        conversion = 0
        attr_state = getattr(self.squidarray,attr)  

        mean1,_ = self._getmean(monitortime)
        setattr(self.squidarray, attr, attr_state + step)
        mean2,_ = self._getmean(monitortime)

        conversion  = (mean2-mean1)/step
        conversion_ = np.sign(conversion) * np.minimum(
                            100, np.maximum(.001, np.abs(conversion)))
        if conversion != conversion_:
            print('Conversion (V/{0}) out of range: {1}'.format(
                attr, conversion))
            conversion = conversion_

        setattr(self.squidarray, attr, attr_state)

        return conversion

    def setup_plots(self):
        '''
        purposely left empty to prevent creating a figure if 
        squid fails to lock
        '''
        pass

    def plot(self):
        '''
        '''
        self.fig, self.ax = plt.subplots(1,3,figsize=(12,4))
        # Plot the charactaristic
        self.ax[0].plot(self.char[1]*self.testsignalconv, self.char[2])
        self.ax[0].set_xlabel("Sflux (uA)")
        self.ax[0].set_ylabel("SAA Signal (V)", size="medium")
        self.ax[0].set_title(" {0:2.2e} phi_0/V".format(self.spectrum.conversion))
        #self.ax[0].axhline(self.aflux_offset, linestyle=':', color='k')

        # Plot the spectrum
        mean = self.noise_mean
        std = self.noise_std
        
        self.ax[2].loglog(self.spectrum.f,
                     self.spectrum.psdAve * self.spectrum.conversion)
        self.ax[2].set_xlabel("Frequency (Hz)")
        self.ax[2].set_title(r"PSD (Noise = {1:2.2f} $\mu \rm {0}/\sqrt{{Hz\rm}}$".format(
                        self.spectrum.units, mean*1e6 ), size="medium")
#        self.ax[2].set_title(r"PSD ($\rm {0}/\sqrt{{Hz\rm}}$".format( self.spectrum.units),
#                        size="medium")
        self.ax[2].annotate('Sbias        = {0:2.2e} uA\nAflux_offset = {1:2.2e} uA'.format(
                            self.squid_bias, self.aflux_offset), 
                            xy=(.02, .2), xycoords='axes fraction',
                            fontsize=8, ha='left', va='top', family='monospace')
        self.ax[2].loglog(self.spectrum.f, 
                          np.ones(self.spectrum.f.shape)*mean, 
                          color='red', linewidth = .5)
        self.ax[2].loglog(self.spectrum.f, 
                          np.ones(self.spectrum.f.shape)*(mean+std), 
                          color='red', linestyle=':', linewidth=.5)
        self.ax[2].loglog(self.spectrum.f, 
                          np.ones(self.spectrum.f.shape)*(mean-std), 
                          color='red', linestyle=':', linewidth=.5)
        
        # Plot the sweep
        self.sweep.ax = self.ax[1]
        self.sweep.plot()
        self.ax[1].set_ylabel("")
        self.ax[1].set_title("DC SQUID Signal (V)",
                        size="medium")



    def run_spectrum(self, save_appendedpath=''):
        '''
        Run a squid spectrum
        '''
        self.squidarray.sensitivity = "High" #Essential, for some reason
        self.preamp.gain = 1
        self.preamp.filter = (1, 100000)
        self.squidarray.reset()
        self.spectrum = SQUIDSpectrum(self.instruments, 
                                      preamp_dccouple_override=True)
        self.spectrum.conversion = self.saaconversion/10
        self.spectrum.saa_status = self.squidarray.__dict__
        if self.debug:
            print('squid sensitivity = ', self.squidarray.sensitivity)

        self.isOL = self.preamp.is_OL()
        if self.isOL:
            print('Overloaded Preamp!')
        self.spectrum.run(welch=True, save_appendedpath = save_appendedpath)

    def run_mi(self, save_appendedpath=''):
        '''
        Run a mutual inductance
        '''
        self.squidarray.sensitivity = "Medium"
        self.squidarray.reset()
        self.preamp.filter = (1, 300)
        self.preamp.gain = 1
        self.squidarray.reset()
        self.sweep = MutualInductance2(self.instruments,
                                       np.linspace(-1e-3, 1e-3, 1000),
                                       Rbias=340,
                                       conversion = 1,
                                       units = 'V')
        self.sweep.saa_status = self.squidarray.__dict__
        self.sweep.run(save_appendedpath = save_appendedpath)

    def do(self):
        # TODO: Measure array V/phi_0 conversion
        # TODO: take array spectrum

        # Try to measure squid V/phi_0 conversion
        #self.squidarray.S_flux_lim = 100
        #[self.selfcal, 
        # self.saaconversion, 
        # self.conv_sflux]  = self.findconversion(stepsize=5, dur=.001)
        #print('Self calibrated? = {0}, phi_0/V = {1}'.format(
        #            self.selfcal, self.saaconversion))

        # Tune squid
        self.istuned = self.tune_squid()
        if self.istuned == False:
            print('Array Tune Failed, will not save array_tune')
            sys.stdout.flush()
            self._DO_NOT_SAVE = True
            return False

        [self.char_ave_grad, 
         self.char_ave_mean, 
         self.char_ave_err, 
         self.char_ave_good, 
        _] = self.analyze_char()

        self.islocked = self.lock_squid()
        if self.islocked == False:
            print('Array Tune Failed, will not save array_tune')
            sys.stdout.flush()
            self._DO_NOT_SAVE = True
            return False

        self.run_spectrum(self._save_appendedpath)
        plt.close()
        self.run_mi(self._save_appendedpath)
        plt.close()

        # make some statistics
        self.noise_mean, self.noise_std = self.spectrum.findmeanstd()
        self.sweep_fcIsrc = np.array(self.sweep.Vsrc / 
                                     self.sweep.Rbias).flatten()
        self.sweep_sresp  = np.array(self.sweep.Vmeas * 
                                     self.sweep.conversion).flatten()
        
        [self.sweep_p, self.sweep_v] = np.polyfit(self.sweep_fcIsrc, 
                                                  self.sweep_sresp,1,
                                                  cov=True)

        self.plot()
        plt.close()
        self.ax = list(self.ax.flatten())
        return True

    def save(self, filename=None, savefig=True, **kwargs):
        if hasattr(self, '_DO_NOT_SAVE') and self._DO_NOT_SAVE == True:
            return

        self._save(filename, savefig=True, **kwargs)

    def findconversion(self, dur=.1, stepsize=1):
        '''
        Find the squid phi_0/V using the saa reset

        Parameters:
        -----------
        dur (float): duration to measure in seconds

        stepsize (float): stepsize to take in S_flux

        Returns:
        --------
        False or out
            out = [the phi_0/V to make phi_0 jump at med,
                   the flux bias point necessary to make the jump]
        '''
        istuned = self.tune_squid()
        if not istuned:
            return [False, self.saaconversion, -1]
        islocked = self.lock_squid()
        if not islocked:
            return [False, self.saaconversion, -1]
        sfluxlim = self.squidarray.S_flux_lim
        self.squidarray.sensitivity = 'Medium'
        return self._findconversion('S_flux', sfluxlim, stepsize, dur)

    def _findconversion(self, attrname, maxattrval, stepsize=1, dur=.1):
        '''
        To find the phi_0/v, one must have a locked device (squid or saa)
        and increment some parameter (s_flux, a_flux) until you see a 
        jump.

        Parameters:
        -----------
        attrname (string): attribute of squidarray to increment

        maxattrval (float): maximum value of attrname

        stepsize (float) increment attrname in steps of stepsize

        dur (float): measure duration

        Returns:
        --------
        False or out
            out = [the phi_0/V to make phi_0 jump at med,
                   the flux bias point necessary to make the jump]
        '''


        self.squidarray.testSignal='Off'
        self.squidarray.sensitivity = 'Medium'
        setattr(self.squidarray, attrname, 0)
        self.squidarray.reset()

        for attrval in np.arange(0, maxattrval+1, stepsize):
            self.squidarray.sensitivity = 'Medium'
            setattr(self.squidarray, attrname, attrval)
            premean, prestd = self._getmean(dur)
            self.squidarray.reset()
            posmean, posstd = self._getmean(dur)
            if np.abs(premean - posmean) > 8*np.maximum(prestd, posstd):
                print(attrname, '=', attrval)
                return [True, 1/abs(posmean - premean), attrval]

        return [False, self.saaconversion, -1]
    
    def analyze_char(self, saasig_range = .05):
        '''
        Analyze the characteristic
        '''
        # sort the characteristics by the test signal
        order = np.argsort(self.char[1])
        self.char_testsig = self.char[1][order]
        self.char_saasig  = self.char[2][order]

        # create mean, grad, err, absgradovererr for this characteristic
        [self.char_mean, 
         self.char_grad, 
         self.char_err, 
         self.char_absgradovererr
        ] = BestLockPoint.savgolmeangrad_convstd(
                self.char_testsig, 
                self.char_saasig)

        # Order the mean, grad, err, absgradovererr=good from closest
        # to the lockpoint (0) to furthest from the lockpoint
        order = np.argsort(np.abs(self.char_mean)) # always locks at zero
        mean_s = self.char_mean[order]
        grad_s = self.char_grad[order]
        err_s  = self.char_err[order]
        good_s = self.char_absgradovererr[order]

        # find the index at which the mean is futher than saasig_range from 
        # the lock point
        index_f = np.argmin(np.abs(mean_s - saasig_range))

        # average all the points near the lockpoint for mean, grad, etc
        ave_grad = np.mean(np.abs(grad_s[0:index_f]))
        ave_mean = np.mean(mean_s[0:index_f])
        ave_err  = np.mean(err_s[0:index_f])
        ave_good = np.mean(good_s[0:index_f])

        return [ave_grad, ave_mean, ave_err, ave_good, order]


        

        


class BestLockPoint(Measurement):
    instrument_list = ["daq", "squidarray", "preamp"]
    _daq_inputs = ["saa", "test"]
    _daq_outputs = []

    def __init__(self, 
                instruments,
                 monitortime=.01, 
                 numsamples=200,
                 samplerate=256000,
                 testinputconv = 10 # uA/V
                 ):
        '''
        BestLockPoint: Quickly find the region in the squid bias-squid flux 
        parameter space where the squid will lock with low noise

        Constructor Parameters:
        -----------------------
        instruments (dict): instruments for measurement

        monitortime (float): time to measure a channel.  Should be at least
                             greater than 1/freq = 1 period of triangle test
                             signal

        numsamples (int): number of sbias samples.  
                          SbiasList = numpy.linspace(0,2000,numsamples)

        samplerate (int): sample rate of daq, in samples/s

        testinputconv (float): uA squid flux / V test signal.  Usually 10 uA/V
                               but can be altered by changing the resistors in 
                               the PFL-102

        '''
        
        super(BestLockPoint, self).__init__(instruments=instruments)
        self.monitortime = monitortime
        self.numsamples = numsamples
        self.samplerate = samplerate
        self.testinputconv = testinputconv

    def do(self):
        '''
        Find best lock points
        '''
        self.findbestlocpoints_record()
        self.findbestlocpoints_analyze()
        self.plot()

    def setup_plots(self):
        '''
        Setup plots
        '''
        self.fig, self.ax = plt.subplots(2,2, figsize=(12,9))
        self.ax = list(self.ax.flatten())

    @staticmethod
    def vmax_xsigma_p(data, sigmas):
        '''
        Calculate the highest value within sigmas sigmas.

        Parameters:
        -----------
        data (numpy ndarray): array of floats (data)

        sigmas (float): number of sigmas to keep


        Returns:
        --------
        out (float): numpy.mean(data) + sigma*numpy.std(data)
        '''
        return np.nanmean(data) + sigmas*np.nanstd(data)

    @staticmethod
    def vmax_xsigma_n(data, sigmas):
        '''
        See vmax_xsigma_n but - instead of +

        Returns:
        --------
        out (float): numpy.mean(data) - sigma*numpy.std(data)

        '''
        return np.nanmean(data) - sigmas*np.nanstd(data)

    def plot(self):
        extent = (self.testinputconv*self.bestloc_testsort_test[0][0], 
                  self.testinputconv*self.bestloc_testsort_test[0][-1],
                  self.sbiasList[0], self.sbiasList[-1])
        mean = self.bestloc_mean - np.tile(np.mean(self.bestloc_mean, axis=1), 
                                          (self.bestloc_mean.shape[1],1)).T
        data = [mean, self.bestloc_grad, self.bestloc_err, 
                self.bestloc_absgrad_over_err]
        labels = ['mean', 'gradient', 'error', 'gradient/error']
        vmax = [
                self.vmax_xsigma_p(mean,4),
                self.vmax_xsigma_p(self.bestloc_grad,4),
                self.vmax_xsigma_p(self.bestloc_err,4),
                self.vmax_xsigma_p(self.bestloc_absgrad_over_err,4)]
        vmin = [
                self.vmax_xsigma_n(mean,4),
                self.vmax_xsigma_n(self.bestloc_grad,4),
                0,
                0]
        cmaps = ['PRGn', 'coolwarm', 'plasma', 'inferno']
        for d,a,l,vp,vn,cm in zip(data, self.ax, labels,vmax,vmin,cmaps):
            self.plot_1(a, d, extent,l,vp, vn, cm)

        self.fig.tight_layout()
        self.ax[0].annotate(self.filename, xy=(.02,.98), xycoords='axes fraction',
                       fontsize=8, ha='left', va='top', family='monospace')


    def plot_1(self, ax, data, extent, label, vmax,vmin,cmap):
        '''
        Helper for plot. Plots a single imshow of the given data

        '''
        im = ax.imshow(data, extent=extent, aspect='auto', 
                      origin='lower',vmax=vmax, vmin=vmin,
                      cmap=cmap)
        d = make_axes_locatable(ax)
        cax = d.append_axes('right', size=.1, pad=.1)
        cbar = plt.colorbar(im, cax=cax)
        cbar.set_label(label)
        ax.set_xlabel('Sflux (uA)')
        ax.set_ylabel('Sbias (uA)')


    def plot_goodness(self, vmax):
        '''
        Plot gradient/err with given vmax to enhance contrast
        '''
        fig,ax = plt.subplots()
        extent = (self.bestloc_testsort_test[0][0], 
                  self.bestloc_testsort_test[0][-1],
                  self.sbiasList[0], 
                  self.sbiasList[-1])
        self.plot_1(ax,self.bestloc_absgrad_over_err,
                    extent=extent, label='gradient/err',
                    vmax=vmax)
        

    @staticmethod
    def plotline(obj, index):
        '''
        Plots a single line (constant Sbias) for the given index

        Parameters:
        -----------
        obj (BestPlotLines or equivalent)

        index (int): which index number to plot
        '''
        xs = obj.testinputconv * obj.bestloc_testsort_test[index]

        fig,ax = plt.subplots(4,1, sharex=True, figsize=(5,9))

        ax[0].plot(xs, obj.bestloc_testsort_saa[index])
        ax[0].plot(xs, obj.bestloc_mean[index])
        ax[0].set_ylabel('signal = SAA signal (V)')

        ax[1].plot(xs, obj.bestloc_grad[index])
        ax[1].set_ylabel('grad = Gradient of signal')

        ax[2].plot(xs, obj.bestloc_err[index])
        ax[2].set_ylabel('err = Binned STD')

        ax[3].plot(xs, obj.bestloc_absgrad_over_err[index])
        ax[3].set_ylabel('abs(grad of saa)/err')

        ax[3].set_xlabel('Sflux (uA)')

        ax[0].annotate(obj.filename, xy=(.02,.98), xycoords='axes fraction',
                       fontsize=8, ha='left', va='top', family='monospace')

        ax[1].annotate('S_bias = {0:2.2f} uA'.format(obj.sbiasList[index]), 
                       xy=(.02,.98), xycoords='axes fraction',
                       fontsize=8, ha='left', va='top', family='monospace')

        fig.subplots_adjust(wspace=0, hspace=0)

        fig.tight_layout()
        
        return fig,ax

    @staticmethod
    def plotline_current(obj, current):
        '''
        plotline but you can choose a current (in uA) instead of an index
        '''
        return BestLockPoint.plotline(obj, np.argmin(np.abs(obj.sbiasList-current)))
    

    def findbestlocpoints_record(self):
        '''
        Record data to find the best lock point
        Called by do.  You should not call this normally.
        '''
        monitortime = self.monitortime
        numsamples = self.numsamples
        samplerate = self.samplerate

        self.squidarray.lock('Array')
        self.squidarray.sensitivity = 'High'
        self.squidarray.testSignal = 'On'
        self.squidarray.testInput = 'S_flux'
        self.sbiasList = np.linspace(0, self.squidarray.S_bias_lim, numsamples)

        first = True
        for sbias,x in zip(self.sbiasList, range(len(self.sbiasList))):
            # take data
            self.squidarray.S_bias = sbias
            self.squidarray.reset()
            received = self.daq.monitor(['saa', 'test'], monitortime, sample_rate=256000)

            # store data
            if first:
                self.bestloc_raw_saa = np.zeros( (numsamples, len(received['saa'])))
                self.bestloc_raw_test = np.zeros( self.bestloc_raw_saa.shape)
                self.bestloc_raw_time = np.zeros( self.bestloc_raw_saa.shape)
                self.bestloc_testsort_saa = np.zeros(  self.bestloc_raw_saa.shape)
                self.bestloc_testsort_test = np.zeros( self.bestloc_raw_saa.shape)

                first = False

            self.bestloc_raw_saa[x] = received['saa']
            self.bestloc_raw_test[x] = received['test']
            self.bestloc_raw_time[x] = received['t']

            # sort by the test signal
            order = np.argsort(self.bestloc_raw_test[x])
            self.bestloc_testsort_test[x] = self.bestloc_raw_test[x][order]
            self.bestloc_testsort_saa[x]  = self.bestloc_raw_saa[x][order]


    def findbestlocpoints_analyze(self, 
                                  savgol_winlen_mean=201, 
                                  savgol_polyorder_mean=5,
                                  savgol_winlen_grad=201,
                                  savgol_polyorder_grad=5,
                                  std_winlen=16):
        '''
        Analyze the data taken.  Constructs gradients, means, error.

        Parameters:
        -----------
        savgol_winlen_mean (int): window length for the sav_gol filter 
                                  for the mean

        savgol_polyorder_mean (int): polynomial order for the sav_gol filter 
        
        savgol_winlen_grad (int): window length for the sav_gol filter
                                  for the gradient

        savgol_polyorder_grad (int): polynomial order for hte sav_gol filter

        std_winlen (int): window length (convolution) for the running 
                          standard deviation for the error.

        Returns:
        --------
        none

        Creates bestloc_mean, bestloc_grad, bestloc_absgrad_over_err
        '''
        [self.bestloc_mean,
         self.bestloc_grad,
         self.bestloc_err,
         self.bestloc_absgrad_over_err] = self.savgolmeangrad_convstd(
                                            self.bestloc_testsort_test,
                                            self.bestloc_testsort_saa,
                                            savgol_winlen_mean,
                                            savgol_polyorder_mean,
                                            savgol_winlen_grad,
                                            savgol_polyorder_grad,
                                            std_winlen)
# Old method, remove if code works
#        delta = np.abs(self.bestloc_testsort_test[0][0]-
#                       self.bestloc_testsort_test[0][-1]
#                       )/self.bestloc_testsort_test[0].shape[0]
#
#        self.bestloc_mean = savgol_filter(self.bestloc_testsort_saa, 
#                                          window_length=savgol_winlen_mean,
#                                          polyorder=savgol_polyorder_mean,
#                                          axis=1)
#        self.bestloc_grad = savgol_filter(self.bestloc_testsort_saa,
#                                          window_length=savgol_winlen_grad,
#                                          polyorder=savgol_polyorder_grad,
#                                          deriv=1, delta=delta,
#                                          axis=1)
#
#        self.bestloc_err = np.apply_along_axis(running_std, 1, 
#                                                  self.bestloc_testsort_saa-self.bestloc_mean, 
#                                                  windowlen=16, mode='same')
#        self.bestloc_absgrad_over_err = np.abs(self.bestloc_grad
#                                              )/self.bestloc_err

    @staticmethod
    def savgolmeangrad_convstd(testsig, saasig, 
                                  savgol_winlen_mean=201, 
                                  savgol_polyorder_mean=5,
                                  savgol_winlen_grad=201,
                                  savgol_polyorder_grad=5,
                                  std_winlen=16):
        '''
        Constructs gradients, means, error of saasig for applied testsig

        Parameters:
        -----------
        testsig (numpy ndarray): 1d or 2d array of test signal voltages, 
                                 sorted such that the lowest is first and
                                 the highest is last.

                                 If 2d, axis 0 (rows) are each squid bias
                                 and axis 1 (column) is the squid flux, 
                                 modulated by the test signal

        saasig (numpy ndarray): 1d or 2d array of saa signal voltages,
                                sorted in the same order as testsig
                                 
        savgol_winlen_mean (int): window length for the sav_gol filter 
                                  for the mean

        savgol_polyorder_mean (int): polynomial order for the sav_gol filter 
        
        savgol_winlen_grad (int): window length for the sav_gol filter
                                  for the gradient

        savgol_polyorder_grad (int): polynomial order for hte sav_gol filter

        std_winlen (int): window length (convolution) for the running 
                          standard deviation for the error.

        Returns:
        --------
        out = [mean, gradient, error, abs(gradient) / error]

        '''
        if len(testsig.shape) > 2:
            raise ValueError('testsig has dimension > 2')

        if len(testsig.shape) == 2:
            axis=1
            delta = np.abs(testsig[0][0]- testsig[0][-1])/testsig[0].shape[0]
        elif len(testsig.shape) == 1:
            axis=-1
            delta = np.abs(testsig[0]- testsig[-1])/testsig.shape[0]


        mean = savgol_filter(saasig,
                             window_length=savgol_winlen_mean,
                             polyorder=savgol_polyorder_mean,
                             axis=axis)
        grad = savgol_filter(saasig,
                             window_length=savgol_winlen_grad,
                             polyorder=savgol_polyorder_grad,
                             deriv=1, delta=delta,
                             axis=axis)
        err = np.apply_along_axis(running_std, 
                                  axis, 
                                  saasig-mean, 
                                  windowlen=std_winlen, 
                                  mode='same')
        absgrad_over_err = np.abs(grad)/err

        return [mean, grad, err, absgrad_over_err]



class ArrayTuneBatch(Measurement):
    def __init__(self, 
                 instruments,
                 sbias = [0], 
                 aflux = [0], 
                 sflux = [0],
                 squid_tol = 100e-3, 
                 aflux_tol = 10e-3, 
                 sbias_ex = 100,
                 aflux_ex = 0,
                 save_appendedpath = '',
                 conversion=1/1.44,
                 debug=False):
        '''
        Test a squid automatically with a SAA 

        Work in progress

        live plotting only plots the first element of sflux, all of 
        sbias and aflux
        '''
        
        super(ArrayTuneBatch, self).__init__(instruments=instruments)

        self.instruments = instruments
        self.sbias = np.array(sbias) 
        self.aflux = np.array(aflux)
        self.sflux = np.array(sflux)
        self.squid_tol = squid_tol
        self.aflux_tol = aflux_tol
        self.save_appendedpath = save_appendedpath
        self.sbias_ex = sbias_ex
        self.aflux_ex = aflux_ex
        self.conversion = conversion

        self.cmap = matplotlib.cm.viridis
        self.cmap.set_bad('white', 1.)
        self.arraytunefilenames = []
        self.leastlineari = -1 
        self.leastlinearval = 1e9
        self.debug = debug
        
        self._initialize()


    def _initialize(self):       

        self.spectrum_f = np.array([])

        # X axis (0th axis) = array flux (where on the characteristic to lock)
        # Y axis (1th axis) = squid bias 
        # Z axis (2th axis) = squid flux (offset after SQUID is locked)
        #        (3rd axis) = data

        # stores [aflux, squid bias, sflux]
        self.lockparams = np.zeros((len(self.sbias),
                                    len(self.aflux),
                                    len(self.sflux),
                                    3))

        # stores [whether squid locked or not]
        self.success    = np.array(np.zeros((len(self.sbias), 
                                             len(self.aflux), 
                                             len(self.sflux),
                                             1), dtype=bool)) # zero = false
        # stores [filtered characteristic, gradient of characteristic,
        #         error (spread) of characteristic, and gradient/error]
        self.char_stats = np.full((len(self.sbias), 
                                   len(self.aflux), 
                                   len(self.sflux),
                                   4), np.nan) 

        self.filenameindex = np.full((len(self.sbias), 
                                             len(self.aflux), 
                                             len(self.sflux),
                                             1), np.nan) 

        self.savenames = ['spectrum_psd',  # psdave * conversion (phi_0)
                          'sweep_fcIsrc',  # Vsrc / Rbias (amps)
                          'sweep_sresp',   # Vmeas * conversion (phi_0)
                          'char_testsig',  # squid char, test signal (V)
                          'char_saasig',   # squid char, saa signal (V)
                          'spectrum_mean', # mean of spectrum (phi_0)
                          'spectrum_std',  # std of spectrum (phi_0)
                          'sweep_p',       # polyfit p: linear fit of sweep
                          'sweep_v',       # polyfit v: linear fit of sweep
                          ]


    def do(self, liveplot = True):

        # try out a point that you know will work. 
        # This determines how large the structures should be 
        print('Test run')
        self._tunesave(0, 0, 0, self.sbias_ex, self.aflux_ex, 0, first=True)
        print('')

        for sb in range(len(self.sbias)):
            for af in range(len(self.aflux)):
                for sf in range(len(self.sflux)):
                    self._tunesave(sb, af, sf, self.sbias[sb],
                                               self.aflux[af],
                                               self.sflux[sf])
            if self.debug:
                print('End of Afluxes')
                print(plottingindex)
                sys.stdout.flush()

        self.plot()
        self.print_highlights()

        

    def _tunesave(self, index_sb, index_af, index_sf, 
                  sbias, aflux, sflux, first=False):
        '''
        Create arraytune, run it, and save it if it is good
        '''

        at = ArrayTune(self.instruments, 
                       squid_bias=sbias, 
                       squid_tol=self.squid_tol,
                       aflux_tol=self.aflux_tol,
                       sflux_offset=sflux,
                       aflux_offset=aflux,
                       conversion=self.conversion, 
                       debug=self.debug)
        locked = at.run(save_appendedpath=self.save_appendedpath)

        try:
        # what to save
            tosave = [np.array(at.spectrum.psdAve * 
                               at.spectrum.conversion).flatten(),
                      np.array(at.sweep.Vsrc /
                               at.sweep.Rbias).flatten(),
                      np.array(at.sweep.Vmeas *
                               at.sweep.conversion).flatten(),
                      np.array(at.char[1]).flatten(), 
                      np.array(at.char[2]).flatten(),
                      np.array([at.noise_mean]).flatten(),
                      np.array([at.noise_std]).flatten(),
                      np.array([at.sweep_p]).flatten(),
                      np.array([at.sweep_v]).flatten()
                     ]
        except:
            pass

        if first: # create all data structures
            ArrayTuneBatch._makestruct(self, 
                                       tosave, 
                                       self.savenames, 
                                       self.success.shape[0:3])
            self.spectrum_f = np.array(at.spectrum.f)
            return

        # did ArrayTune lock?
        self.success[index_sb, index_af, index_sf, 0] = locked

        # what parameters were set?
        self.lockparams[index_sb, index_af, index_sf
                       ] = np.array([aflux, sbias, sflux])

        # details about the characteristic
        print(at.istuned, locked)
        if at.istuned or locked:
            print('saving char', at.char_ave_grad)
            self.char_stats[index_sb, index_af, index_sf
                           ] = np.array([at.char_ave_mean,
                                         at.char_ave_grad,
                                         at.char_ave_err,
                                         at.char_ave_good])

        if not locked: # Squid is not locked, do not save
            return 

        # Save the filename in a roundabout way.  Save index in an ndarray
        # of the correct shape and store the actual filename in a list
        self.filenameindex[index_sb, index_af, index_sf
                          ] = len(self.arraytunefilenames)
        self.arraytunefilenames.append(at.filename)

        # save the actual data
        ArrayTuneBatch._savetostruct(self, tosave, 
                                     self.savenames, 
                                     (index_sb, index_af, index_sf))

        return 

    @staticmethod
    def _makestruct(obj, tosave, savenames, shape):
        for name, item in zip(savenames, tosave):
            setattr(obj, name, np.full( (*shape, *item.shape), np.nan))
            #print(shape, item.shape, getattr(obj, name).shape)

    @staticmethod
    def _savetostruct(obj, tosave, savenames, index):
        for name, item in zip(savenames, tosave):
            try:
                #print(item.shape, getattr(obj,name).shape, index)
                getattr(obj, name)[index] = item
            except:
                print('Cannot set {0} of len {1}'.format(item, len(item)),
                       ' to {2} expecting len {3}'.format(name, 
                           len(getattr(obj, name)[index]))
                      )

    def setup_plots(self):
        self.fig, self.axes = plt.subplots(2,3, figsize=(16,8))
        self.axes = list(self.axes.flatten())

    def plot(self):

        cbarlabels = [r'rms noise ($\mu\phi_0/\sqrt{Hz}$)', 
                      r'linearity (covar of fit)',
                      r'abs grad of squid char',
                      r'error of squid char',
                      r'grad/err',
                      r'noise/(grad/err)'
                     ]
        data = [self.spectrum_mean[:,:,0,0]*1e6, 
                self.sweep_v[:,:,0,0],
                self.char_stats[:,:,0,1],
                self.char_stats[:,:,0,2],
                self.char_stats[:,:,0,3],
                self.spectrum_mean[:,:,0,0]/self.char_stats[:,:,0,3]
               ]
        vmins = [None,
                 None,
                 0,
                 0,
                 0,
                 0
                ]
        vmaxs = [ArrayTuneBatch.vmax_median_p(data[0],1),
                 ArrayTuneBatch.vmax_median_p(data[1],1),
                 BestLockPoint.vmax_xsigma_p(data[2],4),
                 BestLockPoint.vmax_xsigma_p(data[3],4),
                 BestLockPoint.vmax_xsigma_p(data[4],4),
                 BestLockPoint.vmax_xsigma_p(data[5],4),
                ]
        cmaps = ['plasma',
                 'inferno',
                 'viridis',
                 'viridis',
                 'magma',
                 'viridis'
                ]
        extent = [self.aflux.min(), self.aflux.max(), 
                  self.sbias.min()*1e-3, self.sbias.max()*1e-3]

        for ax, d, cbarlabel, vmin, vmax, cmap in zip(self.axes, data, 
                   cbarlabels, vmins, vmaxs, cmaps):
            print(d.shape)
            masked_data = np.ma.array(d, mask=np.isnan(d))
            image = ax.imshow(masked_data, cmap, origin='lower',
                              extent=extent, aspect='auto',
                              vmin=vmin, vmax=vmax)

            d = make_axes_locatable(ax)
            cax = d.append_axes('right', size=.1, pad=.1)
            cbar = plt.colorbar(image, cax=cax)
            cbar.set_label(cbarlabel, rotation=270, labelpad=12)
            cbar.formatter.set_powerlimits( (-2,2))

            ax.set_ylabel('S bias (mA)')
            ax.set_xlabel('A flux offset (V)')

            self.fig.tight_layout()
            self.fig.canvas.draw()
            plt.pause(.001)

    def plot_hist(self):
        fig,ax = plt.subplots()
        order = np.argsort(self.spectrum_mean.flatten())
        noise = self.spectrum_mean.flatten()[order]
        ax.hist(noise[~np.isnan(noise)]*1e6, range=(0,10), bins=100)
        ax.set_xlabel(r'Noise ($\mu\phi_0$)')
        ax.set_ylabel('Occurances (#)')
        return fig,ax


    @staticmethod
    def vmax_median_p(data, n):
        return np.nanmedian(data) + n*np.abs(np.nanmedian(data) - np.nanmin(data))

    def print_highlights(self):
        index_minnoise = np.unravel_index(np.nanargmin(self.spectrum_mean),self.spectrum_mean.shape)
        index_minlinear = np.unravel_index(np.nanargmin(self.sweep_v[:,:,:,0]),self.sweep_v[:,:,:,0].shape)
        print(index_minnoise, index_minlinear)

        print('min noise={0:2.2e}: sbias={1:2.2e}, aflux={2:2.2e}, filename={3}'.format(
                self.spectrum_mean[index_minnoise],
                self.lockparams[index_minnoise[0:3]][1],
                self.lockparams[index_minnoise[0:3]][0],
                self.arraytunefilenames[int(self.filenameindex[index_minnoise[0:3]][0])]))

        print('max linear={0:2.2e}: sbias={1:2.2e}, aflux={2:2.2e}, filename={3}'.format(
                self.sweep_v[index_minlinear][0],
                self.lockparams[index_minlinear[0:3]][1],
                self.lockparams[index_minlinear[0:3]][0],
                self.arraytunefilenames[int(self.filenameindex[index_minlinear[0:3]][0])]))

                    
    def findconversion(self, stepsize=5, dur=.001):
        '''
        Finds the conversion (phi_0/V) for all the points in
        arraytunebatch.  Not very useful.
        '''
        self.caltrue       = np.zeros((len(self.sbias), len(self.aflux)))
        self.saaconversion = np.full((len(self.sbias), len(self.aflux)), np.nan)
        self.conv_sflux    = np.full((len(self.sbias), len(self.aflux)), np.nan)
        ix = -1 
        iy = -1 
        for sb in self.sbias:
            print('Sbias = ', sb)
            ix += 1
            iy = -1 
            for af in self.aflux:
                iy += 1
                at = ArrayTune(self.instruments, squid_bias=sb, 
                       squid_tol = self.squid_tol,
                       aflux_tol = self.aflux_tol,
                       sflux_offset = 0,
                       aflux_offset = af,
                       conversion=self.conversion, debug=self.debug)
                [caltrue, 
                 saaconversion, 
                 conv_sflux
                ] = at.findconversion( stepsize=stepsize, dur=dur)
                if caltrue:
                    self.caltrue[ix][iy] = caltrue 
                    self.saaconversion[ix][iy] = saaconversion
                    self.conv_sflux[ix][iy]  = conv_sflux

    def plotconversion(self):
        '''
        Plots the conversions
        '''
        fig, axs = plt.subplots(1,2)
        for data,cbarlabel,ax,cmap in zip(
                [self.saaconversion, self.conv_sflux], 
                ['V/phi_0', 'S_flux V'],
                axs, 
                ['viridis', 'magma']):
            masked_data = np.ma.array(data, mask=np.isnan(data))
            image = ax.imshow(masked_data, self.cmap, origin='lower',
                              extent=[self.aflux.min(), self.aflux.max(),
                                      self.sbias.min()*1e-3,
                                      self.sbias.max()*1e-3])
            d = make_axes_locatable(ax)
            cax = d.append_axes('right', size=.1, pad=.1)
            cbar = plt.colorbar(image, cax=cax)
            cbar.set_label(cbarlabel, rotation=270, labelpad=12)

                                   

