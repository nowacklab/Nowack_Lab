import numpy as np
from importlib import reload
import time

import Nowack_Lab.Utilities.datasaver
reload(Nowack_Lab.Utilities.datasaver)
from Nowack_Lab.Utilities.datasaver import Saver

import Nowack_Lab.Utilities.alexsave_david_meas
reload(Nowack_Lab.Utilities.alexsave_david_meas)
from Nowack_Lab.Utilities.alexsave_david_meas import Preamp_Util

class SQUID_Noise():
    _daq_inputs=['dc', 'saa', 'fieldcoil']
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

    def lock_squid(self, attempts=5, sflux_offset=0, squid_tol=.1):
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
        squid_tol       (float): signal is at least squid_tol from zero

        Returns:
        ~~~~~~~~
        If locked or not

        """
        self.saa.lock("Squid")
        self.saa.testSignal = "Off"
        self.saa.reset()
        [error, _] = self._minimize_attr("A_flux", 
                                    channels=['saa'], 
                                    evalchannel='saa',
                                    offset=aflux_offset, 
                                    tol=squid_tol)

        if self.debug:
            print('lock_squid error:', error)

        if np.abs(error) < squid_tol:
            print("locked with {} attempts".format(5-attempts))
            return True
        elif attempts == 0:
            print("Cannot lock SQUID. Cannot zero signal within squid_tol.")
            return False
        else:
            return self.lock_squid(attempts - 1)

    def findconversion(self, dur=.1, stepsize=1):
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
        [istuned,_] = self.tune_squid()
        if not istuned:
            return [False, np.nan, -1]
        islocked = self.lock_squid()
        if not islocked:
            return [False, np.nan, -1]
        sfluxlim = self.saa.S_flux_lim
        self.saa.sensitivity = 'Medium'
        return self._findconversion('S_flux', sfluxlim, stepsize, dur) 

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
        setattr(self.saa, attrname, 0)
        self.saa.reset()

        for attrval in np.arange(0, maxattrval+1, stepsize):
            self.saa.sensitivity = 'Medium'
            setattr(self.saa, attrname, attrval)
            premean, prestd = self._getmean()
            self.saa.reset()
            posmean, posstd = self._getmean()
            if np.abs(premean - posmean) > 8*np.maximum(prestd, posstd):
                print(attrname, '=', attrval)
                return [True, 1/abs(posmean - premean), attrval]

        return [False, np.nan, -1]

    def tune_squid(self, sbias, attempts=5, aflux_offset=0, aflux_tol=.01):
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
            aflux_tol < midpoint(characteristic) + aflux_offset

        Returns:
        ~~~~~~~
        [if tuned, 
         rec (dict): 't': measure times
                     'saa': saa voltages
                     'test': test signal voltages
        ]
        """
        self._tune_squid_setup(sbias)
        [error, rec] = self._minimize_attr("A_flux", 
                                    evalchannel='saa',
                                    channels=['saa','test'], 
                                    offset=aflux_offset, 
                                    tol=_tol)

        if self.debug:
            print('Tune_squid error:', error)
        if np.abs(error) < aflux_tol:
            return [True, rec]
        elif attempts == 0:
            print("Cannot tune SQUID.  No good place on characteristic")
            return [False, rec]
        else:
            return self.tune_squid(attempts = attempts-1)

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

        conversion = -1/(self._calibrate_adjust(attr))

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

    def _calibrate_adjust(self, attr, monitortime=.25, step=10):
        """
        Create conversion factor for adjust in V/[attr]
        For a given step size, how much does the SAA signal change?

        Parameters:
        -----------
        attr        (string): parameter of squidarray to change
        monitortime (float): time in seconds to monitor the saa signal
        step        (float): step size to change attr
        """
        conversion = 0
        attr_state = getattr(self.saa,attr)

        mean1,_ = self._getmean()
        setattr(self.saa, attr, attr_state + step)
        mean2,_ = self._getmean()

        conversion  = (mean2-mean1)/step
        conversion_ = np.sign(conversion) * np.minimum(
                            100, np.maximum(.001, np.abs(conversion)))
        if conversion != conversion_:
            print('Conversion (V/{0}) out of range: {1}'.format(
                attr, conversion))
            conversion = conversion_

        setattr(self.saa, attr, attr_state)

        return conversion

    def _getmean(self):
        received = self.daq.monitor('saa', self.fast_dur, 
                                    sample_rate=self.fast_rate)
        return np.mean(received['saa']), np.std(received['saa'])

class SQUID_Noise_Open_Loop(SQUID_Noise):
    def __init__(self,
            instruments,
            sbias = [],
            sflux = [],
            sample_dur=1,
            sample_rate=25600,
            fast_dur = .05,
            fast_rate=25600,
            fft_fspace=1,
            fc_Is=[],
            fc_R=336,
            fc_rate=100,
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
                set_preamp_gain,
                set_preamp_filter,
                set_preamp_dccouple,
                set_preamp_diffmode,
                )

        self.sbias = np.asarray(sbias)
        self.sflux = np.asarray(sflux)

        self.saver = Saver(name='SQUID_Noise_Open_Loop')

        self.saver.append('/sflux/', self.sflux)
        self.saver.append('/sbias/', self.sbias)

        self.saver.append('/Vsaa/', 
                            np.full((self.sbias.shape[0],
                                     self.sflux.shape[0],
                                     2,
                                     int(self.sample_dur*self.sample_rate)
                                     ),
                                    np.nan))
        self.saver.append('/Voverview/',
                            np.full((self.sbias.shape[0],
                                    3,
                                     int(self.fast_dur*self.fast_rate)
                                     ),
                                    np.nan))

        self.saver.append('/Vsaa_per_sflux/', 
                            np.full((self.sbias.shape[0],
                                     self.sflux.shape[0]),
                                    np.nan))
        self.saver.append('/_dims/', 
                {'Vsaa': ['sbias', 'sflux', 'Vsaa_data', 'samples_vsaa'],
                 'Voverview': ['sbias', 'Vover_data', 'samples_vover'],
                  'Vsaa_per_sflux': ['sbias' ,'sflux']
                                })
        self.saver.append('/_coords/',
                {'Vsaa_data': ['time', 'Vdc'],
                {'Vover_data': ['time', 'Vsaa', 'Vdc'],
                    })

    def _localconversion(self, span=.5):
        '''
        Returns the Vsaa (V) /S_flux (uA) at the current S_flux
        '''
        orig = self.saa.S_flux
        self.saa.S_flux = orig-span/2
        r = self.daq.monitor('dc',
                             self.fast_dur,
                             sample_rate=self.fast_rate)

        low = np.mean(r['dc']/self.preamp.gain)

        self.saa_S_flux = orig+span/2
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

            # TODO center about zero so preamp can have gain?
            _ = self._minimize_attr('A_flux')

            # get Vsaa/sflux conversion for each sbias, sflux
            conv = self._localconversion()
            self.saver.append('/Vsaa_per_sflux/', conv, slc=(i,j))

            # take noise spectrum
            r = self.daq.monitor(['dc'],
                                 self.sample_dur,
                                 sample_rate=self.sample_rate)
            self.saver.append('/Vsaa/', 
                              r['t'],
                              slc=(i,j,0))
            self.saver.append('/Vsaa/', 
                              r['dc']/self.preamp.gain, 
                              slc=(i,j,1))

            # save fourier transformed data

    def _get_overview(self, i):

        self.saa.testSignal = 'On'
        self.saa.sensitivity = 'High'

        _ = self._minimize_attr('A_flux')

        r = self.daq.monitor(['dc','saa'], 
                             self.fast_dur,
                             sample_rate=self.fast_rate)
        self.saver.append('/Voverview/',
                          r['t'],
                          slc=(i,0))
        self.saver.append('/Voverview/',
                          r['dc']/self.preamp.gain,
                          slc=(i,1))
        self.saver.append('/Voverview/',
                          r['saa'],
                          slc=(i,2))

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
                 sample_dur=1,
                 sample_rate=128000,
                 fast_dur=.05,
                 fast_rate=128000,
                 fft_fspace=1,
                 fc_Is=[],
                 fc_R=300,
                 fc_rate=1000,
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
                fft_fspace,
                fc_Is,
                fc_R,
                fc_rate,
                set_preamp_gain,
                set_preamp_filter,
                set_preamp_dccouple,
                set_preamp_diffmode
                )

        self.sbias = np.asarray(sbias)
        self.num_aflux = int(num_aflux)


        self.saver = Saver(name='SQUID_Noise_Closed_Loop')
        
        self.saver.append('/Vspectrum/', 
                            np.full((self.sbias.shape[0],
                                     self.num_aflux,
                                     2, # 0 time, 1 Voltage
                                     int(self.sample_rate*self.sample_dur),
                                     ), np.nan))
        self.saver.append('/sbias/', self.sbias)
        self.saver.append('/aflux/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.append('/wastuned/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.append('/waslocked_med/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.append('/waslocked_high/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
        self.saver.append('/Vsquidchar/', 
                            np.full((self.sbias.shape[0],
                                         self.num_aflux,
                                         3, # 0 time 1 test, 2 saa 
                                         int(self.fast_dur*self.fast_rate)),
                                         np.nan))
        self.saver.append('/Vfc_sweep/', 
                            np.full((self.sbias.shape[0],
                                     self.num_aflux,
                                     3, # 0 time, 1 Vsrc, 2 Vmeas
                                     int(self.fc_rate*self.fc_Is.shape[0])
                                     ), np.nan))
        self.saver.append('/wasoverloaded/',
                            np.full((self.sbias.shape[0],
                                         self.num_aflux),
                                         np.nan))
                            
    def _make_aflux(self, i):
        '''
        determine afluxes you wish to sweep
        by default, it sweeps all afluxes between the max and 
        min value
        '''
        self.saa.testSignal = 'On'
        self.saa.testInput = 'S_flux'
        self.saa.sensitivity = 'Med'
        self.reset()
        r = self.daq.monitor(['saa'], self.fast_dur,
                             sample_rate=self.fast_rate)
        span = np.max(r['saa']) - np.min(r['saa'])
        aflux = np.linspace(-span/2, span/2, self.num_aflux)
        self.saver.append('/aflux/', aflux, slc=(i,))

    def _take_spectrum(self, i, j):
        '''
        Take a noise spectrum and populate
        the disk at i,j
        '''
        starttime = time.time()
        r = self.daq.monitor(['dc'], self.sample_dur, 
                             sample_rate=self.sample_rate)
        
        self.saver.append('/Vspectrum/', r['t']+starttime,
                            slc=(i, j, 1))
        self.saver.append('/Vspectrum/', r['dc']/self.preamp.gain,
                            slc=(i,j,1))
        self.saver.append('/wasoverloaded/', self.preamp.is_OL(), 
                            slc=(i,j))
                            

    def _prep_spectrum(self):
        self.saa.sensitivity = 'High'
        self.testSignal='Off'
        self.preamp.filter=(1,10000)
        self.preamp.gain=10 #auto-gain?
        self.reset()

    def _prep_fc_linearity(self):
        self.saa.sensitivity = 'Med'
        self.saa.reset()
        self.preamp.filter = (1,300)
        self.preamp.gain = 1
        self.saa.reset()

    def _take_fc_linearity(self, i, j):
        '''
        Measure fc
        i,j is the index of sbias, aflux_offset we are at
        saves after completion
        '''
        fc_Vs = self.fc_Is * self.fc_R

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
        
        self.saver.append('/Vfc_sweep/', rec['t'], slc=(i,j,0))
        self.saver.append('/Vfc_sweep/', out['fieldcoil'], slc=(i,j,1))
        self.saver.append('/Vfc_sweep/', rec['fieldcoil'], slc=(i,j,2))

    def _tune(self, aflux, sbias, i, j):
        '''
        tunes the squid at aflux, sbias
        i,j are the sbias, aflux_offset index
        saves squid characteristic
        '''
        [istunned, r] = self.tune_squid(sbias, aflux_offset=aflux)
        self.saver.append('/wastuned/', int(istunned),
                            slc=(i,j))

        self.saver.append('/Vsquidchar/', r['t'],
                            slc=(i,j,0))
        self.saver.append('/Vsquidchar/', r['test'],
                            slc=(i,j,1))
        self.saver.append('/Vsquidchar/', r['saa'],
                            slc=(i,j,2))
        return istunned

    def _lock(self, aflux, i, j):
        '''
        lock the squid at aflux aflux_offset
        i,j are the sbias, aflux_offset index
        saves state (islocked)
        '''
        islocked = self.lock_squid()
        self.saver.append('/waslocked_med/', int(islocked),
                            slc=(i,j))

        self._prep_spectrum(aflux)
        islocked = self.lock_squid()
        self.saver.append('/waslocked_high/', int(islocked),
                            slc=(i,j))
        return islocked

    def run(self):
        for i in range(self.sbias.shape[0]):

            aflux = self._make_aflux(i)
            for j in range(self.num_aflux):
                istunned = False
                islocked = False

                istunned = self._tune(aflux[j], sbias[i], i, j)

                if istunned:
                    islocked = self._lock(aflux[j], i, j)
                    
                    if islocked:
                        self._prep_spectrum()
                        self._take_spectrum(i,j)
                        self._prep_fc_linearity()
                        self._take_fc_linearity(i,j)


