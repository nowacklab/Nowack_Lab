import numpy as np
import matplotlib.pyplot as plt
from ..Instruments import piezos, nidaq, montana
import time, os
from datetime import datetime
from .measurement import Measurement
from ..Utilities import conversions
from ..Utilities.utilities import AttrDict

class Heightsweep(Measurement):
    _daq_inputs = ['dc','cap', 'acx','acy']
    _conversions = AttrDict({
        # Assume high; changed in init when array loaded
        'dc': conversions.Vsquid_to_phi0['High'],
        'cap': conversions.V_to_C,
        'acx': conversions.Vsquid_to_phi0['High'],
        'acy': conversions.Vsquid_to_phi0['High'],
        'x': conversions.Vx_to_um,
        'y': conversions.Vy_to_um
    })
    instrument_list = ['piezos','montana','squidarray']


    def __init__(self, instruments = {}, plane=None, x=0, y=0, zstart=0, zend=None, scan_rate=60):
        '''
        Measure while sweeping the z piezo away from the sample, starting at zstart piezo volts below the plane and ending at zend
        If zend is None, sweep to maximum piezo voltage
        '''
        super().__init__(instruments=instruments)

        self.plane = plane
        self.x = x
        self.y = y
        self.zstart = self.plane.plane(self.x, self.y) - zstart
        if zend is None:
            self.zend = -self.piezos.z.Vmax
        else:
            self.zend = self.plane.plane(self.x, self.y) - zend
        self.scan_rate = scan_rate
        self.V = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo', 'z']
        })

        # Load the correct SAA sensitivity based on the SAA feedback resistor
        try:  # try block enables creating object without instruments
            Vsquid_to_phi0 = conversions.Vsquid_to_phi0[self.squidarray.sensitivity]
            self._conversions['acx'] = Vsquid_to_phi0
            self._conversions['acy'] = Vsquid_to_phi0
            # doesn't consider preamp gain. If preamp communication fails, then
            # this will be recorded
            self._conversions['dc'] = Vsquid_to_phi0
            # Divide out the preamp gain for the DC channel
            self._conversions['dc'] /= self.preamp.gain
        except:
            pass

    def do(self, **kwargs):

        self.temp_start = self.montana.temperature['platform']

        Vstart = {'z': self.zstart}
        Vend = {'z': self.zend}

        self.piezos.V = {'x':self.x, 'y':self.y, 'z': Vstart['z']}
        self.squidarray.reset()
        time.sleep(10) # wait at the surface

        output_data, received = self.piezos.sweep(Vstart, Vend,
                                        chan_in = self._daq_inputs,
                                        sweep_rate = self.scan_rate)

        for chan in self._daq_inputs:
            self.V[chan] = received[chan]
        self.V['z'] = self.zstart - np.array(output_data['z'])

        self.piezos.zero()

        self.plot()


    def plot(self):
        super().plot()

        for chan in self._daq_inputs:
            self.ax[chan].plot(self.V['z'], self.V[chan]*self._conversions[chan], '.k', markersize=6, alpha=0.5)
        self.fig.tight_layout()
        self.fig.canvas.draw()


    def setup_plots(self):
        self.fig = plt.figure(figsize=(5,10))
        self.ax = AttrDict({})

        self.ax['dc'] = self.fig.add_subplot(411)
        self.ax['cap'] = self.fig.add_subplot(412)
        self.ax['acx'] = self.fig.add_subplot(413)
        self.ax['acy'] = self.fig.add_subplot(414)

        self.ax['acy'].set_xlabel(r'$V_z^{samp} - V_z (V)$')
        self.ax['dc'].set_title('%s\nat (%.2f V, %.2f V)' %(self.filename, self.x, self.y))

        for label, ax in self.ax.items():
            ax.set_ylabel('%s (V)' %label)
            if label != 'acy':
                ax.set_xticks([])

        self.fig.subplots_adjust(hspace=0)
