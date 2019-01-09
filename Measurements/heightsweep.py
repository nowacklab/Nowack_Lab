
import numpy as np
import matplotlib.pyplot as plt
from ..Instruments import piezos, nidaq, montana
import time, os
from datetime import datetime
from .measurement import Measurement
from ..Utilities import conversions
from ..Utilities.utilities import AttrDict

class Heightsweep(Measurement):
    _daq_inputs = ['dc','acx','acy','cap']
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
        self.Vup = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo', 'z']
        })
        self.Vdown = AttrDict({
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

    def do(self):

        Vstart = {'z': self.zstart}
        Vend = {'z': self.zend}

        self.piezos.V = {'x':self.x, 'y':self.y, 'z': Vstart['z']}
        self.squidarray.reset()
        time.sleep(1) # wait before sweeping

        output_data, received = self.piezos.sweep(Vstart, Vend,
                                        chan_in = self._daq_inputs,
                                        sweep_rate = self.scan_rate)

        for chan in self._daq_inputs:
            self.V[chan] = received[chan]
        self.V['z'] = self.zstart - np.array(output_data['z'])

        self.piezos.zero()

        self.plot()

    def setup_plots(self):
        self.fig = plt.figure(figsize=(6,10))
        self.axes = AttrDict()
        self.axes[0] = self.fig.add_subplot(411)
        self.axes[1] = self.fig.add_subplot(412, sharex=self.axes[0])
        self.axes[2] = self.fig.add_subplot(413, sharex=self.axes[0])
        self.axes[3] = self.fig.add_subplot(414, sharex=self.axes[0])

    def plot(self):
        super().plot()

        for chan in self._daq_inputs:
            self.ax[chan].plot(self.V['z'], self.V[chan]*self._conversions[chan], '.k', markersize=6, alpha=0.5)
        self.fig.tight_layout()
        self.fig.canvas.draw()

        #self.fig, self.axes = plt.subplots(4, 1, figsize=(6,10), sharex=True)
        self.fig.subplots_adjust(hspace=0)
        axes = [self.axes[0], self.axes[1], self.axes[2], self.axes[3]]
        for chan, ax in zip(self._daq_inputs, axes):
            ax.plot(self.Vup['z'], self.Vup[chan])
            ax.plot(self.Vdown['z'], self.Vdown[chan])
            # ax.set_ylabel(labels[chan])

        self.axes[3].set_xlabel("Z Position (V)")
        self.axes[0].set_title(self.timestamp, size="medium")


    #def save(self, filename=None, savefig=True, **kwargs):
        # the problem is axes is not an attrdict
    #    self._save(filename, savefig=True, ignored=["axes"], **kwargs)
