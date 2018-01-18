from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import os
import re
from ..Instruments import nidaq, preamp
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict
from ..Utilities import conversions
import time


class DaqSpectrum(Measurement):
    """Monitor a DAQ channel and compute the power spectral density

    Acqurire a number of time traces from the channel labeled 'dc' on the DAQ.
    Average the time traces and compute the power spectral density.
    """
    _daq_inputs = ['dc']  
    instrument_list = ['daq', 'preamp']

    def __init__(
            self,
            instruments={},
            measure_time=0.5,
            measure_freq=256000,
            averages=30,
            annotate_notes=False,
            preamp_gain_override = True,
            preamp_gain = 1,
            preamp_filter_override = True,
            preamp_filter = (0,100e3),
            preamp_dccouple_override = True,
            preamp_dccouple=True,
            preamp_autoOL=False,
            preamp_diff_mode = False
            ):
        """Create a DaqSpectrum object
        
        Args:
        instruments (dict): instruments used to collect data
        measure_time (float): time in seconds that DAQ monitors the output 
            channel
        measure_freq (int?): frequency that the DAQ measures the output channel
        averages (int): number of time traces averaged before computing the FFT

        annotate_notes           Boolean, turns on and off the notes on the plot
        preamp_gain_override     Boolean, if True, code won't change gain
        preamp_gain              int, value to set the preamp gain
        preamp_filter_override   Boolean, if true, code won't change filter
        preamp_filter            two-ple of ints, (0,100e3), sets filter freq
        preamp_dccouple_override Boolean, if true, code won't change dc/ac 
                                 couple.  This persists in the auto overload
                                 functionality
        preamp_autoOL            Boolean, if true, allows the code to try and
                                 adjust the ac/dc coupling (disable with 
                                 preamp_dccouple_override=True) and the gain to
                                 prevent the preamp from overloading
        """
        super().__init__(instruments=instruments)
        
        for arg in ['measure_time', 
                    'measure_freq', 
                    'averages',
                    'annotate_notes',
                    'preamp_gain',
                    'preamp_gain_override',
                    'preamp_filter',
                    'preamp_filter_override',
                    'preamp_dccouple',
                    'preamp_dccouple_override',
                    'preamp_autoOL',
                    'preamp_diff_mode'
                    ]:
            setattr(self, arg, eval(arg))

        # set default values so DaqSpectrum works
        self.units = 'V';
        self.conversion = 1;

        self.V = np.zeros( 
            ( self.averages, int(self.measure_time * self.measure_freq) )
        );

    def do(self, welch=False):
        """Do the DaqSpectrum measurment."""
        self.setup_preamp()

        if welch:
            self.psdAve = self.get_spectrum_welch()
        else:
            self.psdAve = self.get_spectrum()

        self.plot()

    def get_spectrum_welch(self):
        received = self.daq.monitor('dc', self.measure_time*self.averages,
                                          sample_rate=self.measure_freq)
        self.V = received['dc'] / self.preamp.gain
        self.t = received['t']
        self.f, self.psd = signal.welch(self.V, fs = self.measure_freq)

        return np.sqrt(self.psd)

    def get_spectrum(self):
        """Collect time traces from the DAQ and compute the FFT.
        
        Returns:
        psdAve (np.ndarray): power spectral density
        """
        Nfft = int((self.measure_freq * self.measure_time / 2) + 1)
        psdAve = np.zeros(Nfft)

        for i in range(self.averages):
            received = self.daq.monitor('dc', self.measure_time,
                                        sample_rate=self.measure_freq
                                        )
            # Unpack data recieved from daq.
            # Divide out any preamp gain applied.
            self.V[i] = received['dc'] / self.preamp.gain
            self.t = received['t']

            # Note: this is barlett's method
            self.f, psd = signal.periodogram(self.V[i], self.measure_freq,
                                             'blackmanharris')
            psdAve = psdAve + psd
            
        # Normalize by the number of averages
        psdAve = psdAve / self.averages  
        # Convert spectrum to V/sqrt(Hz)
        return np.sqrt(psdAve)  
    
    def plot(self):
        """Plot the PDS on a loglog and semilog scale"""
        super().plot()
        self.ax['loglog'].loglog(self.f, self.psdAve*self.conversion)
        self.ax['semilog'].semilogy(self.f, self.psdAve*self.conversion)
        self.ax['semilog'].set_xlim([self.f[0],1e3]);
        for ax in [self.ax['loglog'], self.ax['semilog']]:
            if self.annotate_notes:
                ax.annotate(self.notes, xy=(0.02,.45), xycoords='axes fraction',
                        fontsize=8, ha='left', va='top', family='monospace'
                );


    def setup_plots(self):
        """Setup loglog and semilog plots for PSD"""
        self.fig = plt.figure(figsize=(12, 6))
        self.ax = AttrDict()
        self.ax['loglog'] = self.fig.add_subplot(121)
        self.ax['semilog'] = self.fig.add_subplot(122)

        for ax in self.ax.values():
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel(
                r'Power Spectral Density ($\mathrm{%s/\sqrt{Hz}}$)' %
                self.units)
            #apply a timestamp to the plot
            ax.annotate(self.timestamp, xy=(0.02,.98), xycoords='axes fraction',
                fontsize=10, ha='left', va = 'top', family='monospace'
            )

        self.fig.canvas.draw();
        plt.pause(0.01);

    def setup_preamp(self):
        """Set preamplifier settings appropriate for taking spectra"""
        if not hasattr(self, 'preamp') or self.preamp is None:
            print('No preamp!')
            return
        if not self.preamp_gain_override:
            self.preamp.gain = self.preamp_gain;
        if not self.preamp_filter_override:
            self.preamp.filter = self.preamp_filter;
        if not self.preamp_dccouple_override:
            self.preamp.dc_coupling(self.preamp_dccouple)

        self.preamp.diff_input(self.preamp_diff_mode)
        self.preamp.filter_mode('low', 12)

        if self.preamp.is_OL() and self.preamp_autoOL:
            self.preamp_OL();

    def preamp_OL(self):
        '''
        Try to fix overloading preamp
        '''
        if self.preamp_dccouple_override: #cannot change dccouple
            self._preamp_OL_changegain();
        else:
            # If not AC coupling, AC couple
            if self.preamp_dccouple is True:
                self.preamp_dccouple = False;
                self.preamp.dc_coupling(self.preamp_dccouple);
                self._preamp_OL_changegain();

        # Now I've done all we can do.  Set to minimum and record if its bad
        if self.preamp.is_OL():
            self.preamp_gain = 1;
            self.preamp.gain=self.preamp_gain;
            self.preamp.recover();
            time.sleep(12);
            if self.preamp.is_OL():
                self.preamp_OL = True;
        self.preamp_OL = False;

    def _preamp_OL_changegain(self):
        '''
        Lower preamp gain until no longer overloading
        Waits 10 s (max AC couple time constant) if ac coupled
        '''
        GAIN = np.array([1,2,3,4,5,10,25,50,100,250]);
        while self.preamp.is_OL() and self.preamp.gain > 1:
            thisgainindex = np.abs(GAIN-self.preamp.gain).argmin();
            if thisgainindex == 0:
                self.preamp.gain=1;
                return;
            self.preamp_gain = GAIN[thisgainindex-1];
            self.preamp.gain = self.preamp_gain;
            self.preamp.recover();
            if self.preamp_dccouple is False:
                time.sleep(12) # >10, in case slow communication








class SQUIDSpectrum(DaqSpectrum):
    """Wrapper for DAQSpectrum that converts from V to Phi_o."""
    instrument_list = ['daq', 'preamp', 'squidarray']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.units = '\phi_0'
        self.conversion = conversions.Vsquid_to_phi0[self.squidarray.sensitivity]

class AnnotatedSpectrum(DaqSpectrum):
    instrument_list=['daq','lockin_cap','preamp','squidarray', 'piezos'];

    def __init__(self, CAP_I, *args, 
        notes='Annotated Spectrum',
        annotate_piezos = True,
        annotate_cap    = True,
        annotate_preamp = True,
        annotate_saa    = True,
        **kwargs
    ):
        '''
        '''
        super().__init__(*args, annotate_notes=True, **kwargs)
        self.notes = notes;
        self.CAP_I = CAP_I;
        self.annotate_piezos = annotate_piezos;
        self.annotate_cap    = annotate_cap;
        self.annotate_preamp = annotate_preamp;
        self.annotate_saa    = annotate_saa;



    def squidspectra(self):
        self.units = '\phi_0';
        self.conversion = conversions.Vsquid_to_phi0[self.squidarray.sensitivity]

    def vspectra(self):
        self.units = 'V';
        self.conversion = 1;

    def arrayspectra(self):
        self.units = '\phi_0';
        self.conversion = conversions.Varray_to_phi0[self.squidarray.sensitivity]
        return;


    def plot(self, *args, **kwargs):
        '''
        Overloaded plot to force the generation of notes
        '''
        # Stupid order because I want the notes to be changed before any one
        # has a chance to plot anything
        self.notes = self.notes + (
        "\n"+
        "[time, averages] = [{0:2.2f}, {1:d}]\n".format(
                self.measure_time,
                self.averages
            )+
        "[units, conversion] = [{0},{1:2.4f}]\n".format(
                self.units,
                self.conversion
            )
        )
        if self.annotate_piezos:
            self.notes = self.notes + (
                "[x,y,z] = [{0:d},{1:d},{2:d}]\n".format(
                    int(self.piezos.V['x']), 
                    int(self.piezos.V['y']), 
                    int(self.piezos.V['z'])
                )
            )
            self.X = self.piezos.V['x']
            self.Y = self.piezos.V['y']
            self.Z = self.piezos.V['z']
        if self.annotate_cap:
            self.notes = self.notes + (
                "[c, c0] = [{0:2.2e}, {1:2.2e}]\n".format(
                    self.lockin_cap.R,
                    self.CAP_I
                )
            )
            self.cap = self.lockin_cap.R
        if self.annotate_preamp:
            self.notes = self.notes + (
            "[gain, filter f, dc couple?, OL?] = " + 
            "[{0:d}, {1:2.2e}, {2}, {3}]\n".format(
                self.preamp.gain,
                self.preamp.filter[1],
                self.preamp.is_dc_coupled(),
                self.preamp.is_OL()
            )
            )
            self.gain = self.preamp.gain
        if self.annotate_saa:
            self.notes = self.notes + (
            "[A_bias, A_flux, S_bias, S_flux] = " + 
            "[{0:2.2f}, {1:2.2f}, {2:2.2f}, {3:2.2f}]\n".format(
                self.squidarray.A_bias,
                self.squidarray.A_flux,
                self.squidarray.S_bias,
                self.squidarray.S_flux
            )+
            "[Alocked, Slocked, sensitivity] = [{0}, {1}, {2}]\n".format(
                self.squidarray.__getstate__()['Array locked'],
                self.squidarray.__getstate__()['SQUID locked'],
                self.squidarray.__getstate__()['sensitivity']
            )
            )

        super().plot(*args, **kwargs);
