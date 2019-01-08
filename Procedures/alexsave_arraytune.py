import numpy as np
from importlib import reload
import time

import Nowack_Lab.Utilities.utilities as NL_util
reload(NL_util)

import Nowack_Lab.Utilities.welch
reload(Nowack_Lab.Utilities.welch)
from Nowack_Lab.Utilities.welch import Welch

import Nowack_Lab.Utilities.dataset
reload(Nowack_Lab.Utilities.dataset)
from Nowack_Lab.Utilities.dataset import Dataset

import Nowack_Lab.Utilities.datasaver
reload(Nowack_Lab.Utilities.datasaver)
from Nowack_Lab.Utilities.datasaver import Saver

import Nowack_Lab.Utilities.alexsave_david_meas
reload(Nowack_Lab.Utilities.alexsave_david_meas)
from Nowack_Lab.Utilities.alexsave_david_meas import Preamp_Util

class SQUID_Noise():
    _daq_inputs=['dc', 'saa', 'fieldcoil', 'test']
    _daq_outputs=['fieldcoil']

    def __init__(self,
                 instruments,
                 sample_dur,
                 sample_rate,
                 fast_dur,
                 fast_rate,
                 fft_fspace,
                 fc_Is,
                 fc_R,
                 fc_rate,
                 rms_range,
                 slock_tol,
                 stune_tol,
                 set_preamp_gain,
                 set_preamp_filter,
                 set_preamp_dccouple,
                 set_preamp_diffmode,
                 ):
        '''
        Super class for SQUID_Noise measurements
        For code common to running open and closed loop
        Do not run on its own
        '''

        self.daq = instruments['daq']
        self.saa = instruments['squidarray']
        Preamp_Util.init(self, instruments,
                        set_preamp_gain=set_preamp_gain,
                        set_preamp_filter=set_preamp_filter,
                        set_preamp_dccouple=set_preamp_dccouple,
                        set_preamp_diffmode=set_preamp_diffmode,
                        )

        self.sample_dur = sample_dur
        self.sample_rate = sample_rate
        self.fast_dur = fast_dur
        self.fast_rate = fast_rate
        self.fft_fspace = fft_fspace

        self.fc_Is = np.asarray(fc_Is)
        self.fc_R = fc_R
        self.fc_rate = fc_rate

        self.rms_range = rms_range

        self.slock_tol = slock_tol
        self.stune_tol = stune_tol

    def lock_squid(self, attempts=5, sflux_offset=0, slock_tol=None):
        """
        Lock the SQUID and adjust the DC SQUID flux.
        Adjust the DC offset of the SQUID signal to be near
        zero to avoid overloading the preamp.

        State Before:
        ~~~~~~~~~~~~
        SQUID is tuned
            array is locked
            SQUID is biased to correct bias point

        State After:
        ~~~~~~~~~~~~
        SQUID is locked and Vsaa is within squid_tol of 0

        Params:
        ~~~~~~
        attempts        (int): number of times to run this (recursive)
        sflux_offset    (float): offset midpoint of signal by this much
                                 always 0 to prevent overloading preamp
        squid_tol       (float or None): signal is at least squid_tol from zero

        Returns:
        ~~~~~~~~
        If locked or not

        """
        if slock_tol == None:
            slock_tol = self.slock_tol
        self.saa.lock("Squid")
        self.saa.testSignal = "Off"
        self.saa.reset()
        [error, _] = self._minimize_attr("S_flux", 
                                    channels=['saa'], 
                                    evalchannel='saa',
                                    offset=sflux_offset, 
                                    tol=slock_tol)

        #if self.debug:
        #    print('lock_squid error:', error)

        if np.abs(error) < slock_tol:
            print("locked with {} attempts".format(5-attempts))
            return True
        elif attempts == 0:
            print("Cannot lock SQUID. Cannot zero signal within slock_tol.")
            return False
        else:
            return self.lock_squid(attempts - 1)

    def findconversion(self, stepsize=1):
        '''  
        Find the squid phi_0/V using the saa reset

        State Before:
        ~~~~~~~~~~~~
        Array locked

        Parameters:
        -----------
        dur         (float): duration to measure in seconds
        stepsize    (float): stepsize to take in S_flux

        Returns:
        --------
        [boolean if could find a jump,
         the phi_0/V to make phi_0 jump at med,
         the flux bias point necessary to make the jump,
        ]
        '''
        [istuned,_] = self.tune_squid(self.saa.S_bias)
        if not istuned:
            return [False, np.nan, -1]
        islocked = self.lock_squid()
        if not islocked:
            return [False, np.nan, -1]
        sfluxlim = self.saa.S_flux_lim
        self.saa.sensitivity = 'Medium'
        return self._findconversion('S_flux', sfluxlim, stepsize=stepsize) 

    def _findconversion(self, attrname, maxattrval, stepsize=1):
        '''  
        To find the phi_0/v, one must have a locked device (squid or saa)
        and increment some parameter (s_flux, a_flux) until you see a 
        jump.

        Parameters:
        -----------
        attrname    (string): attribute of squidarray to increment
        maxattrval  (float): maximum value of attrname
        stepsize    (float) increment attrname in steps of stepsize
        dur         (float): measure duration

        Returns:
        --------
        [boolean if could find a jump,
         the phi_0/V to make phi_0 jump at med,
         the flux bias point necessary to make the jump]
        '''


        self.saa.testSignal='Off'
        self.saa.sensitivity = 'Medium'

        startattrval = getattr(self.saa, attrname)
        setattr(self.saa, attrname, 0)
        self.saa.reset()

        for attrval in np.arange(0, maxattrval+1, stepsize):
            setattr(self.saa, attrname, attrval)
            premean, prestd = self._getmean()
            self.saa.reset()
            posmean, posstd = self._getmean()
            if np.abs(premean - posmean) > 8*np.maximum(prestd, posstd):
                print(attrname, '=', attrval)
                setattr(self.saa, attrname, startattrval)
                return [True, 1/abs(posmean - premean), attrval]

        setattr(self.saa, attrname, startattrval)
        return [False, np.nan, -1]

    def tune_squid(self, sbias, attempts=5, aflux_offset=0, stune_tol=None):
        """
        Tune the SQUID and adjust the DC SAA flux.  Array locked,
        lock on a specific value of the SQUID characteristic.

        State Before:
        ~~~~~~~~~~~~~
        Array is tuned an locked
        Large test signal

        State After:
        ~~~~~~~~~~~~
        SQUID is tuned
            SQUID biased to sbias
            stune_tol < midpoint(characteristic) + aflux_offset

        Returns:
        ~~~~~~~
        [if tuned, 
         rec (dict): 't': measure times
                     'saa': saa voltages
                     'test': test signal voltages
        ]
        """
        if stune_tol == None:
            stune_tol = self.stune_tol
        self._tune_squid_setup(sbias)
        [error, rec] = self._minimize_attr("A_flux", 
                                    evalchannel='saa',
                                    channels=['saa','test'], 
                                    offset=aflux_offset, 
                                    tol=stune_tol)

        if np.abs(error) < stune_tol:
            return [True, rec]
        elif attempts == 0:
            print("Cannot tune SQUID.  No good place on characteristic")
            return [False, rec]
        else:
            return self.tune_squid(sbias, attempts = attempts-1)

    def _tune_squid_setup(self, sbias):
        """
        Configure SAA for SQUID tuning.  Array locked, choose a place on
        the SQUID characteristic to lock.
        """
        self.saa.lock("Array")
        #self.squidarray.S_flux_lim = 100
        #self.squidarray.S_flux = self.squidarray.S_flux_lim/2
        self.saa.testInput = "S_flux"
        self.saa.testSignal = "On"
        self.saa.S_bias = sbias
        self.saa.sensitivity = "High"
        self.saa.reset()

    @staticmethod
    def _midpoint(data):
        return (np.max(data) + np.min(data))/2

    def _minimize_attr(self, attr, channels=['saa'], evalchannel='saa',
                        offset=0, tol=0):
        """
        Adjust DC flux to center the trace @ 0 V.
        Called by lock_squid and tune_squid

        Parameters:
        -----------
        attr:           (string): parameter of squidarray to change
        channels:       (list of strings): names of channels to measure
        evalchannel:    (string): name of channel to compute error with
        offset:         (float): error = midpoint(evalchannel) + offset 
        tol:            (float): if abs(error) < tol: exit
        """

        # Evaluate error =  midpoint(signal from channel) + offset
        rec = self.daq.monitor(channels, self.fast_dur, 
                                sample_rate = self.fast_rate)
        error = self._midpoint(rec[evalchannel]) + offset

        if np.abs(error) < tol:
            return [error, rec]

        value = getattr(self.saa, attr)

        conversion = -1/(self._calibrate_adjust(attr)[0])

        if False:
            print('    adjusting {0}: error={1:3.3f}, {0}+={2:3.3f}'.format(
                        attr, error, error*conversion))

        # If the predicted correction is outside the acceptable range
        # reset or set to zero
        if value + error * conversion < 0:
            setattr(self.saa, attr, value + 50)
        elif value + error * conversion > 150:
            setattr(self.saa, attr, 0)
        else:
            # Directly correct the error
            setattr(self.saa, attr, value + conversion * error)

        self.saa.reset()

        # Re-evaluate error =  midpoint(signal from channel) + offset
        rec = self.daq.monitor(channels, self.fast_dur, 
                                sample_rate = self.fast_rate)
        error = self._midpoint(rec[evalchannel]) + offset
        return [error, rec]

    def _calibrate_adjust(self, attr, step=1):
        """
        Create conversion factor for adjust in V/[attr]
        For a given step size, how much does the SAA signal change?

        Parameters:
        -----------
        attr        (string): parameter of squidarray to change
        step        (float): step size to change attr
        """
        success = True
        conversion = 0
        attr_state = getattr(self.saa,attr)
        sigstate = getattr(self.saa, 'testSignal')
        self.saa.testSignal='Off'

        mean1,_ = self._getmean()
        setattr(self.saa, attr, attr_state + step)
        mean2,_ = self._getmean()

        conversion  = (mean2-mean1)/step
        conversion_ = np.sign(conversion) * np.minimum(
                            100, np.maximum(.001, np.abs(conversion)))
        if conversion != conversion_:
            #print('Conversion (V/{0}) out of range: {1}'.format(
            #    attr, conversion))
            conversion = conversion_
            success = False

        setattr(self.saa, attr, attr_state)
        setattr(self.saa, 'testSignal', sigstate)

        return [conversion, success]

    def _getmean(self):
        received = self.daq.monitor('saa', self.fast_dur, 
                                    sample_rate=self.fast_rate)
        return np.mean(received['saa']), np.std(received['saa'])

    def _getmaxabs(self):
        received = self.daq.monitor('saa', self.fast_dur, 
                                    sample_rate=self.fast_rate)
        return np.max(np.abs(received['saa'])) 

    def _prep_preamp(self):
        '''
        State Before:
        ~~~~~~~~~~~~
        squid locked
        '''
        maxabs = self._getmaxabs()
        gain = NL_util.preamp_gain(self._getmaxabs())
        self.preamp.gain = gain
    
    def _len_of_fft(self):
        '''
        How large will the fft be?  Compute it by calling the welching function
        on ones
        '''
        v = np.ones(self.sample_dur * self.sample_rate)
        [f, psd] = Welch.welchf(v, self.sample_rate, self.fft_fspace)
        return [f, f.shape[0]]

class SQUID_Noise_Open_Loop(SQUID_Noise):
    def __init__(self,
            instruments,
            sbias = [],
            sflux = [],
            sample_dur=1,
            sample_rate=76800,
            fast_dur = .05,
            fast_rate=25600,
            fft_fspace=5,
            fc_Is=[],
            fc_R=336,
            fc_rate=100,
            rms_range=(500,5000),
            phi_0_per_sflux_uA=1/170,
            slock_tol=.01,
            stune_tol=.01,
            set_preamp_gain=None,
            set_preamp_filter=None,
            set_preamp_dccouple=None,
            set_preamp_diffmode=None,
            ):
        '''
        Measure SQUID noise open loop
        '''
        super().__init__(instruments,
                sample_dur,
                sample_rate,
                fast_dur,
                fast_rate,
                fft_fspace,
                fc_Is,
                fc_R,
                fc_rate,
                rms_range,
                slock_tol,
                stune_tol,
                set_preamp_gain,
                set_preamp_filter,
                set_preamp_dccouple,
                set_preamp_diffmode,
                )

        self.sbias = np.asarray(sbias)
        self.sflux = np.asarray(sflux)
        self.phi_0_per_sflux_uA = phi_0_per_sflux_uA
        self.sflux_offsets = np.asarray([0,10])

        [f, len_fft] = self._len_of_fft()

        self.saver = Saver(name='SQUID_Noise_Open_Loop')

        # dimensions (coordinates)
        self.saver.append('/sflux/', self.sflux)
        self.saver.create_attr('/sflux/', 'units', 'micro Amps')
        self.saver.append('/sbias/', self.sbias)
        self.saver.create_attr('/sbias/', 'units', 'micro Amps')
        self.saver.append('/f/', f)
        self.saver.create_attr('/f/', 'units', 'Seconds')
        self.saver.append('/t_Vsaa/', 
                            np.linspace(0, self.sample_dur, 
                            int(self.sample_dur*self.sample_rate)))
        self.saver.create_attr('/t_Vsaa/', 'units', 'Seconds')
        self.saver.append('/t_Voverview/', 
                            np.linspace(0, self.fast_dur, 
                            int(self.fast_dur*self.fast_rate)))
        self.saver.create_attr('/t_Voverview/', 'units', 'Seconds')

        self.saver.append('/_voverview_data_names/', ['test', 'Vdc'])
        self.saver.append('/_rms_data_names/', ['rms', 'rms_reject_outliers'])
        self.saver.append('/_sflux_offset/', self.sflux_offsets)
        self.saver.create_attr('/_sflux_offset/', 'units', 'saa uA')


        self.saver.append('/Vsaa/', 
                            np.full((self.sbias.shape[0],
                                     self.sflux.shape[0],
                                     int(self.sample_dur*self.sample_rate)
                                     ),
                                    np.nan))
        self.saver.make_dim('/Vsaa/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/Vsaa/', 1, 'sflux', '/sflux/', 'sflux (uA)')
        self.saver.make_dim('/Vsaa/', 2, 't_Vsaa', '/t_Vsaa/', 'time (s)')
        self.saver.create_attr('/Vsaa/', 'units', 'Volts')

        self.saver.append('/Voverview/',
                            np.full((self.sbias.shape[0],
                                    2,
                                    2,
                                     int(self.fast_dur*self.fast_rate)
                                     ),
                                    np.nan))
        self.saver.make_dim('/Voverview/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/Voverview/', 1, '_sflux_offset', '/_sflux_offset/', 
                                                'saa uA')
        self.saver.make_dim('/Voverview/', 2, 'voverview_data_names', 
                                              '/_voverview_data_names/', 
                                              'Voverview Data names')
        self.saver.make_dim('/Voverview/', 3, 't_Voverview', '/t_Voverview/', 
                                                'time (s)')
        self.saver.create_attr('/Voverview/', 'units', 'Volts')
        
        self.saver.append('/starttimes/',
                            np.full((self.sbias.shape[0],
                                     self.sflux.shape[0]),
                                    np.nan))
        self.saver.make_dim('/starttimes/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/starttimes/', 1, 'sflux', '/sflux/', 'sflux (uA)')
        self.saver.create_attr('/starttimes/', 'units', 'Seconds')

        self.saver.append('/Vsaa_per_sflux/', 
                            np.full((self.sbias.shape[0],
                                     self.sflux.shape[0]),
                                    np.nan))
        self.saver.make_dim('/Vsaa_per_sflux/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/Vsaa_per_sflux/', 1, 'sflux', '/sflux/', 'sflux (uA)')
        self.saver.create_attr('/Vsaa_per_sflux/', 'units', 'Volts / micro Amps')

        self.saver.append('/asd/', 
                            np.full((self.sbias.shape[0],
                                     self.sflux.shape[0],
                                     len_fft,
                                     ),
                                    np.nan))
        self.saver.make_dim('/asd/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/asd/', 1, 'sflux', '/sflux/', 'sflux (uA)')
        self.saver.make_dim('/asd/', 2, 'f', '/f/', 'frequency (Hz)')
        self.saver.create_attr('/asd/', 'units', r'$\Phi_0/\sqrt{Hz\rm}$')

        self.saver.append('/asd_rms/',
                            np.full((self.sbias.shape[0],
                                     self.sflux.shape[0],
                                     2), 
                                    np.nan))
        self.saver.make_dim('/asd_rms/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/asd_rms/', 1, 'sflux', '/sflux/', 'sflux (uA)')
        self.saver.make_dim('/asd_rms/', 2, 'rms_data_names', 
                            '/_rms_data_names/', 'rms data names')
        self.saver.create_attr('/asd_rms/', 'units', r'$\Phi_0/\sqrt{Hz\rm}#')

        self.saver.append('/wasoverloaded/', 
                            np.full((self.sbias.shape[0],
                                     self.sflux.shape[0]), np.nan))
        self.saver.make_dim('/wasoverloaded/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/wasoverloaded/', 1, 'sflux', '/sflux/', 'sflux (uA)')
        self.saver.create_attr('/wasoverloaded/', 'units', '(0=False, 1=True)')

        self.saver.append('/attrs/',
                {'sample_dur': sample_dur,
                 'sample_rate': sample_rate,
                 'fast_dur': fast_dur,
                 'fast_rate': fast_rate,
                 'fft_fspace': fft_fspace,
                 'fc_Is': fc_Is,
                 'fc_R': fc_R,
                 'fc_rate': fc_rate,
                 'phi_0_per_sflux_uA': phi_0_per_sflux_uA,
                })
        self.saver.append('/units/',
                {'sflux': 'SAA uA',
                 'sbias': 'SAA uA',
                 'Vsaa' : 'V',
                 'Voverview': 'V',
                 'starttimes': 'epoc time (seconds)',
                 'Vsaa_per_sflux': 'V/(SAA uA)',
                 'asd': 'phi_0/Hz^.5',
                 'asd_rms': 'phi_0/Hz^.5',
                 'wasoverloaded': 'boolean (0 False, 1 True)',
                 'rms_range': self.rms_range,
                    })
        

    def _localconversion(self, span=4):
        '''
        Returns the Vsaa (V) /S_flux (uA) at the current S_flux
        '''
        orig = self.saa.S_flux
        self.saa.S_flux = orig-span/2
        self._prep_preamp()
        r = self.daq.monitor('dc',
                             self.fast_dur,
                             sample_rate=self.fast_rate)

        low = np.mean(r['dc']/self.preamp.gain)

        self.saa_S_flux = orig+span/2
        self._prep_preamp()
        r = self.daq.monitor('dc',
                             self.fast_dur,
                             sample_rate=self.fast_rate)

        high = np.mean(r['dc']/self.preamp.gain)

        self.saa_S_flux = orig

        return (high-low)/span

    def _run_const_sbias(self, i):
        for sflux, j in zip(self.sflux, range(self.sflux.shape[0])):
            self.saa.S_flux = sflux
            #print('sflux: ', sflux, ', j: ', j)

            self.saa.testSignal = 'Off'
            self.saa.sensitivity = 'High'

            # center about zero so preamp can have gain
            _ = self._minimize_attr('A_flux')


            # get Vsaa/sflux conversion for each sbias, sflux
            v_per_sflux_uA = self._localconversion()
            self.saver.append('/Vsaa_per_sflux/', v_per_sflux_uA, slc=(i,j))

            # take noise spectrum

            self._prep_preamp()
            starttime = time.time()
            r = self.daq.monitor(['dc'],
                                 self.sample_dur,
                                 sample_rate=self.sample_rate)
            self.saver.append('/starttimes/', starttime, slc=(i,j))
            self.saver.append('/Vsaa/', 
                              r['dc']/self.preamp.gain, 
                              slc=(i,j))
            self.saver.append('/wasoverloaded/', self.preamp.is_OL(), 
                            slc=(i,j))

            # save fourier transformed data
            [f, psd] = Welch.welchf(r['dc']/self.preamp.gain, self.sample_rate,
                                    self.fft_fspace)
            conversion = 1 / np.abs(v_per_sflux_uA) * self.phi_0_per_sflux_uA
            asd = np.sqrt(psd) *conversion
            self.saver.append('/asd/', asd, slc=(i,j))

            # save rms
            [rms, rms_sigma] = NL_util.make_rms(f, psd, self.rms_range, sigma=2)
            rms = rms*conversion
            rms_sigma = rms_sigma*conversion
            self.saver.append('/asd_rms/', np.array([rms, rms_sigma]), slc=(i,j))

    def _get_overview(self, i):

        self.saa.testSignal = 'On'
        self.saa.sensitivity = 'High'

        _ = self._minimize_attr('A_flux')

        self._prep_preamp()

        for j in range(len(self.sflux_offsets)):
            orig = self.saa.S_flux
            self.saa.S_flux = orig + self.sflux_offsets[j]
            r = self.daq.monitor(['dc','test'], 
                                 self.fast_dur,
                                 sample_rate=self.fast_rate)
            self.saver.append('/Voverview/',
                              r['test'],
                              slc=(i,j,0))
            self.saver.append('/Voverview/',
                              r['dc']/self.preamp.gain,
                              slc=(i,j,1))
            self.saa.S_flux = orig

    def run(self):
        '''
        State Before:
        ~~~~~~~~~~~~
        Array Locked
        High test signal excitation

        '''

        for sbias, i in zip(self.sbias, range(self.sbias.shape[0])):
            print('sbias: ', sbias)
            self._tune_squid_setup(sbias)
            self._get_overview(i)
            self._run_const_sbias(i)

class SQUID_Noise_Closed_Loop(SQUID_Noise):
    def __init__(self,
                 instruments,
                 sbias=[],
                 num_aflux=10,
                 sample_dur=3,
                 sample_rate=76800,
                 fast_dur=.05,
                 fast_rate=25600,
                 fft_fspace=1,
                 fc_Is=[],
                 fc_R=300,
                 fc_rate=1000,
                 rms_range=(500,5000),
                 phi0perVmed=.565,
                 slock_tol=.05,
                 stune_tol=.01,
                 set_preamp_gain=None,
                 set_preamp_filter=None,
                 set_preamp_dccouple=None,
                 set_preamp_diffmode=None,
                 ):
        super().__init__(instruments,
                sample_dur,
                sample_rate,
                fast_dur,
                fast_rate,
                fft_fspace,
                fc_Is,
                fc_R,
                fc_rate,
                rms_range,
                slock_tol,
                stune_tol,
                set_preamp_gain,
                set_preamp_filter,
                set_preamp_dccouple,
                set_preamp_diffmode
                )

        self.sbias = np.asarray(sbias)
        self.num_aflux = int(num_aflux)
        self.phi0perVmed = phi0perVmed

        f, len_fft = self._len_of_fft()

        self.saver = Saver(name='SQUID_Noise_Closed_Loop')

        # dimensions / coordinates
        self.saver.append('/sbias/', self.sbias)
        self.saver.create_attr('/sbias/', 'units', 'saa uA')
        self.saver.append('/_num_aflux/', np.arange(0,self.num_aflux))
        self.saver.create_attr('/_num_aflux/', 'units', 'index')
        self.saver.append('/t_Vspectrum/', 
                          np.linspace(0,self.sample_dur,
                                      int(self.sample_rate*self.sample_dur)))
        self.saver.create_attr('/t_Vspectrum/', 'units', 'seconds')
        self.saver.append('/t_Vsquidchar/', 
                          np.linspace(0,self.fast_dur,
                                      int(self.fast_rate*self.fast_dur)))
        self.saver.create_attr('/t_Vsquidchar/', 'units', 'seconds')
        self.saver.append('/_vsquidchar_data_names/', ['test', 'Vsaa'])
        self.saver.append('/f/', f)
        self.saver.create_attr('/f/', 'units', 'Hz')
        self.saver.append('/_Vfc_sweep_data_names/', ['Vsrc', 'Vmeas'])
        self.saver.append('/t_Vfc_sweep/', 
                          np.linspace(0,self.fc_Is.shape[0]/self.fc_rate,
                                      int(self.fc_Is.shape[0])))
        self.saver.create_attr('/t_Vfc_sweep/', 'units', 'Seconds')
        self.saver.append('/_rms_data_names/', ['rms', 'rms_reject_outliers'])
        self.saver.append('/Vspectrum/', 
                            np.full((self.sbias.shape[0],
                                     self.num_aflux,
                                     int(self.sample_rate*self.sample_dur),
                                     ), np.nan))
        self.saver.make_dim('/Vspectrum/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/Vspectrum/', 1, 'aflux_num', '/_num_aflux/', 'index')
        self.saver.make_dim('/Vspectrum/', 2, 't_Vspectrum', '/t_Vspectrum/', 
                            'Vspectrum time (seconds)')
        self.saver.create_attr('/Vspectrum/', 'units', 'Volts')

        self.saver.append('/aflux/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.make_dim('/aflux/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/aflux/', 1, 'aflux_num', '/_num_aflux/', 'index')
        self.saver.create_attr('/aflux/', 'units', 'Vsaa Volts')

        self.saver.append('/wastuned/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.make_dim('/wastuned/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/wastuned/', 1, 'aflux_num', '/_num_aflux/', 'index')
        self.saver.create_attr('/wastuned/', 'units', 
                                'boolean (0 False, 1 True)')

        self.saver.append('/waslocked_med/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.make_dim('/waslocked_med/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/waslocked_med/', 1, 'aflux_num', '/_num_aflux/', 
                            'index')
        self.saver.create_attr('/waslocked_med/', 'units', 
                                'boolean (0 False, 1 True)')

        self.saver.append('/waslocked_high/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.make_dim('/waslocked_high/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/waslocked_high/', 1, 'aflux_num', '/_num_aflux/', 
                            'index')
        self.saver.create_attr('/waslocked_high/', 'units', 
                                'boolean (0 False, 1 True)')

        self.saver.append('/Vsquidchar/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux,
                                         2, # 0 test, 1 saa 
                                         int(self.fast_dur*self.fast_rate)),
                                         np.nan))
        self.saver.make_dim('/Vsquidchar/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/Vsquidchar/', 1, 'aflux_num', '/_num_aflux/', 'index')
        self.saver.make_dim('/Vsquidchar/', 2, 'Vsquidchar_data_names', 
                            '/_vsquidchar_data_names/', 'Vsquidchar data names')
        self.saver.make_dim('/Vsquidchar/', 3, 't_Vsquidchar', '/t_Vsquidchar/', 
                            'seconds')
        self.saver.create_attr('/Vsquidchar/', 'units', 'Volts')

        self.saver.append('phi_0_per_V', 
                            np.full((self.sbias.shape[0],
                                     self.num_aflux), np.nan))
        self.saver.make_dim('/phi_0_per_V/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/phi_0_per_V/', 1, 'aflux_num', '/_num_aflux/', 'index')
        self.saver.create_attr('/phi_0_per_V/', 'units', r'$\Phi_0 / $Volts')

        self.saver.append('/Vfc_sweep/', 
                            np.full((self.sbias.shape[0],
                                     self.num_aflux,
                                     2, # 1 Vsrc, 2 Vmeas
                                     int(self.fc_Is.shape[0])
                                     ), np.nan))
        self.saver.make_dim('/Vfc_sweep/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/Vfc_sweep/', 1, 'aflux_num', '/_num_aflux/', 'index')
        self.saver.make_dim('/Vfc_sweep/', 2, 'vfc_sweep_data_names', 
                            '/_Vfc_sweep_data_names/', 'Vfc sweep data names')
        self.saver.make_dim('/Vfc_sweep/', 3, 't_Vfc_sweep', '/t_Vfc_sweep/', 
                            'time of fc sweep (seconds)')
        self.saver.create_attr('/Vfc_sweep/', 'units', 'Volts')

        self.saver.append('/wasoverloaded/',
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.make_dim('/wasoverloaded/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/wasoverloaded/', 1, 'aflux_num', '/_num_aflux/', 
                            'index')
        self.saver.create_attr('/wasoverloaded/', 'units', 
                                'boolean (0 False, 1 True)')
        self.saver.append('/gain/',
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.make_dim('/gain/', 0, 'sbias', '/sbias/', 'sbias (uA)')
        self.saver.make_dim('/gain/', 1, 'aflux_num', '/_num_aflux/', 
                            'index')
        self.saver.create_attr('/gain/', 'units', 
                                'gain')

        self.saver.append('/Vspectrum_starttimes/',
                            np.full((self.sbias.shape[0],
                                     self.num_aflux),
                                    np.nan))
        self.saver.make_dim('/Vspectrum_starttimes/', 0, 'sbias', '/sbias/', 
                            'sbias (uA)')
        self.saver.make_dim('/Vspectrum_starttimes/', 1, 'aflux_num', 
                            '/_num_aflux/', 'index')
        self.saver.create_attr('/Vspectrum_starttimes/', 'units', 
                            'epoch time (seconds)')

        self.saver.append('/split_times/',
                            np.full((self.sbias.shape[0],
                                     self.num_aflux),
                                    np.nan))
        self.saver.make_dim('/split_times/', 0, 'sbias', '/sbias/', 
                            'sbias (uA)')
        self.saver.make_dim('/split_times/', 1, 'aflux_num', 
                            '/_num_aflux/', 'index')
        self.saver.create_attr('/split_times/', 'units', 
                            'epoch time (seconds)')


        self.saver.append('/Vfc_sweep_starttimes/',
                            np.full((self.sbias.shape[0],
                                     self.num_aflux),
                                    np.nan))
        self.saver.make_dim('/Vfc_sweep_starttimes/', 0, 'sbias', '/sbias/', 
                            'sbias (uA)')
        self.saver.make_dim('/Vfc_sweep_starttimes/', 1, 'aflux_num', 
                            '/_num_aflux/', 'index')
        self.saver.create_attr('/Vfc_sweep_starttimes/', 'units', 
                            'epoch time (seconds)')

        self.saver.append('/Vspectrum_asd/', 
                            np.full((self.sbias.shape[0],
                                     self.num_aflux,
                                     len_fft,
                                     ),
                                    np.nan))
        self.saver.make_dim('/Vspectrum_asd/', 0, 'sbias', '/sbias/', 
                            'sbias (uA)')
        self.saver.make_dim('/Vspectrum_asd/', 1, 'aflux_num', 
                            '/_num_aflux/', 'index')
        self.saver.make_dim('/Vspectrum_asd/', 2, 'frequency', 
                            '/f/', 'frequency (Hz)')
        self.saver.create_attr('/Vspectrum_asd/', 'units', r'$\Phi_0/\sqrt{Hz\rm}$')

        self.saver.append('/Vspectrum_asd_rms/',
                            np.full((self.sbias.shape[0],
                                     self.num_aflux,
                                     2), 
                                    np.nan))
        self.saver.make_dim('/Vspectrum_asd_rms/', 0, 'sbias', '/sbias/', 
                            'sbias (uA)')
        self.saver.make_dim('/Vspectrum_asd_rms/', 1, 'aflux_num', 
                            '/_num_aflux/', 'index')
        self.saver.make_dim('/Vspectrum_asd_rms/', 2, 'rms_data_names', 
                            '/_rms_data_names/', 'names of rms data')
        self.saver.create_attr('/Vspectrum_asd_rms/', 'units', r'$\Phi_0/\sqrt{Hz\rm}$')

        self.saver.create_attr_dict('/',
                {'sample_dur': sample_dur,
                 'sample_rate': sample_rate,
                 'fast_dur': fast_dur,
                 'fast_rate': fast_rate,
                 'fft_fspace': fft_fspace,
                 'fc_Is': fc_Is,
                 'fc_R': fc_R,
                 'fc_rate': fc_rate,
                 'rms_range': self.rms_range,
                })

    def _make_aflux(self, i, sbias):
        '''
        determine afluxes you wish to sweep
        by default, it sweeps all afluxes between the max and 
        min value
        '''
        [istunned, r] = self.tune_squid(sbias, aflux_offset=0)

        #r = self.daq.monitor(['saa'], self.fast_dur,
        #                     sample_rate=self.fast_rate)

        print(np.max(r['saa']), np.min(r['saa']))

        span = np.abs(np.max(r['saa']) - np.min(r['saa']))
        print(span, -span/2-span/(self.num_aflux-2))
        aflux = np.linspace(-span/2 - span/(self.num_aflux-2), 
                             span/2 + span/(self.num_aflux-2),  
                             self.num_aflux) # include 2 points that are not valid
        self.saver.append('/aflux/', aflux, slc=(i,))
        return aflux

    def _take_spectrum(self, i, j, phi0perV):
        '''
        Take a noise spectrum and populate
        the disk at i,j
        '''
        # take and save spectrum
        starttime = time.time()
        r = self.daq.monitor(['dc'], self.sample_dur, 
                             sample_rate=self.sample_rate)
        self.saver.append('/Vspectrum/', r['dc']/self.preamp.gain,
                            slc=(i,j))
        self.saver.append('/wasoverloaded/', self.preamp.is_OL(), 
                            slc=(i,j))
        self.saver.append('/gain/', self.preamp.gain, slc=(i,j))
        self.saver.append('/Vspectrum_starttimes/', starttime, slc=(i,j))
        
        # save amplitude spectral density
        [f, psd] = Welch.welchf(r['dc']/self.preamp.gain, self.sample_rate,
                                self.fft_fspace)
        asd = np.sqrt(psd) * phi0perV/10 # High sensitivity
        self.saver.append('/Vspectrum_asd/', asd, slc=(i,j))
        
        # save rms
        [rms, rms_sigma] = NL_util.make_rms(f, psd, self.rms_range, sigma=2)
        rms = rms*phi0perV/10
        rms_sigma = rms_sigma*phi0perV/10
        self.saver.append('/Vspectrum_asd_rms/', 
                          np.array([rms, rms_sigma]), slc=(i,j))
                            
    def _take_conversion(self, i, j):
        '''
        Measure phi0/V

        State Before:
        ~~~~~~~~~~~~
        SQUID locked on Medium
        Test Signal Off

        State After:
        ~~~~~~~~~~~~
        Same as before
        '''
        [found, phi0perV, _] = self._findconversion('S_flux', 
                                                    self.saa.S_flux_lim, 
                                                    stepsize=20) 
        if not found:
            return self.phi0perVmed

        if np.abs(phi0perV - self.phi0perVmed) > self.phi0perVmed:
            return self.phi0perVmed

        self.saver.append('/phi_0_per_V/', phi0perV, slc=(i,j))
        return phi0perV

    def _prep_spectrum(self):
        #self.saa.reset()
        self.saa.sensitivity = 'High'
        self.testSignal = 'Off'
        self.preamp.filter = (1,30000)
        self._prep_preamp()
        #self.saa.reset()

    def _prep_fc_linearity(self):
        self.saa.sensitivity = 'Med'
        self.saa.reset()
        #self.preamp.filter = (1,300)
        self.preamp.gain = 1
        self.saa.reset()

    def _take_fc_linearity(self, i, j):
        '''
        Measure fc
        i,j is the index of sbias, aflux_offset we are at
        saves after completion
        '''
        fc_Vs = self.fc_Is * self.fc_R
        starttime = time.time()

        _,_ = self.daq.singlesweep('fieldcoil', fc_Vs[0],
                                    numsteps=self.fc_Is.shape[0]/2,
                                    sample_rate=self.fc_rate)
        out, rec = self.daq.sweep(Vstart ={'fieldcoil':fc_Vs[0]},
                                  Vend   ={'fieldcoil':fc_Vs[-1]},
                                  chan_in=['dc'],
                                  sample_rate=self.fc_rate,
                                  numsteps=self.fc_Is.shape[0])
        _,_ = self.daq.singlesweep('fieldcoil', 0,
                                    numsteps=self.fc_Is.shape[0]/2,
                                    sample_rate=self.fc_rate)
        
        self.saver.append('/Vfc_sweep/', out['fieldcoil'], slc=(i,j,0))
        self.saver.append('/Vfc_sweep/', rec['dc'], slc=(i,j,1))
        self.saver.append('/Vfc_sweep_starttimes/', starttime, slc=(i,j))

    def _tune(self, aflux, sbias, i, j):
        '''
        tunes the squid at aflux, sbias
        i,j are the sbias, aflux_offset index
        saves squid characteristic
        '''
        [istunned, r] = self.tune_squid(sbias, aflux_offset=aflux)
        self.saver.append('/wastuned/', int(istunned),
                            slc=(i,j))

        self.saver.append('/Vsquidchar/', r['test'],
                            slc=(i,j,0))
        self.saver.append('/Vsquidchar/', r['saa'],
                            slc=(i,j,1))
        return istunned

    def _lock(self, i, j, sensitivity='Med'):
        '''
        lock the squid at aflux aflux_offset
        i,j are the sbias, aflux_offset index
        saves state (islocked)

        State Before:
        ~~~~~~~~~~~~
        SQUID tuned

        State After:
        ~~~~~~~~~~~
        SQUID locked
        saa
            sensitivity = sensitivity
            testSignal = Off
        '''
        self.saa.sensitivity = sensitivity 
        islocked = self.lock_squid(attempts=4)
        if not islocked:
            print('Cannot Lock at {0}.  Giving a Push'.format(sensitivity))
            offset = 100
            if self.saa.S_flux > self.saa.S_flux_lim/2:
                offset = -100
            self.saa.S_flux = self.saa.S_flux + offset
            islocked = self.lock_squid(attempts=3)

        if sensitivity=='Med':
            name = '/waslocked_med/'
        else:
            name = '/waslocked_high/'

        self.saver.append(name, int(islocked), slc=(i,j))

        return islocked



    def run(self):
        '''
        Run Measurement!

        State Before:
        ~~~~~~~~~~~~
        Locked Array
        
        '''
        for i in range(self.sbias.shape[0]):
            aflux = self._make_aflux(i, self.sbias[i])

            if (aflux.max() - aflux.min()) < .01: 
                print('No afluxes, SQUID characteristic amplitude is too small')
            else:
                self._run_over_afluxes(aflux, i)

    def _split_time(self, i,j):
        t = time.time()
        self.saver.append('/split_times/', t, slc=(i,j))

    def _run_over_afluxes(self, aflux, i):
        '''
        Helper method for run.  Iterates through the afluxes
        '''
        for j in range(self.num_aflux):
            self._split_time(i,j)
            istunned = self._tune(aflux[j], self.sbias[i], i, j)

            if istunned:
                islock_med = self._lock(i,j, 'Med')

                if islock_med:
                    phi0perV = self._take_conversion(i,j)

                    islock_high = self._lock(i,j, 'High')

                    if islock_high:
                        print('Locked: sbias: {0}, aflux: {1}'.format(
                            self.sbias[i], aflux[j]))
                        self._prep_spectrum()
                        self._take_spectrum(i,j, phi0perV)
                        self._prep_fc_linearity()
                        self._take_fc_linearity(i,j)

                    else:
                        print('Cannot lock on High')
                else:
                    print('Cannot lock on Medium so we cannot lock at High')
            else:
                print('Cannot Tune the SQUID')
                    
class xarray_fncts:
    
    @staticmethod
    def make_aflux_sbiasfull(ds, dataarrayname):
        afluxfull = (('sbias','_num_aflux'), ds.aflux)
        sbiasfull = (('sbias', '_num_aflux'), 
                    np.tile(ds.sbias.values, (ds._num_aflux.shape[0], 1)).T
                    )
        #ds.get(dataarrayname).coords['sbiasfull'] = sbiasfull
        #ds.get(dataarrayname).coords['afluxfull'] = afluxfull

        return [afluxfull, sbiasfull]
