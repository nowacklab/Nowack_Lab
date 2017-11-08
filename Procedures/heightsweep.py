
import numpy as np
import matplotlib.pyplot as plt
from ..Instruments import piezos, nidaq, montana
import time, os
from datetime import datetime
from ..Utilities.save import Measurement
from ..Utilities import conversions
from ..Utilities.utilities import AttrDict

class Heightsweep(Measurement):
    _daq_inputs = ['dc','acx','acy','cap']
    _conversions = AttrDict({
        'dc': conversions.Vsquid_to_phi0,
        'acx': conversions.Vsquid_to_phi0,
        'acy': conversions.Vsquid_to_phi0,
        'z': conversions.Vz_to_um
    })
    instrument_list = ['piezos','montana','squidarray']


    def __init__(self, instruments = {}, plane=None, x=0, y=0, z0=0, scan_rate=120):
        super().__init__(instruments=instruments)

        self.x = x
        self.y = y
        self.z0 = z0
        self.plane = plane
        self.scan_rate = scan_rate
        self.Vup = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo', 'z']
        })
        self.Vdown = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo', 'z']
        })


    def do(self, zstart=0.0):

        Vend = {'z': self.plane.plane(self.x, self.y) - self.z0}
        Vstart = {'z': zstart}

        self.piezos.V = {'x':self.x, 'y':self.y, 'z': Vstart['z']}
        self.squidarray.reset()
        time.sleep(1) # wait before sweeping

        output_data, received = self.piezos.sweep(Vstart, Vend,
                                        chan_in = self._daq_inputs,
                                        sweep_rate = self.scan_rate)

        for chan in self._daq_inputs:
            self.Vup[chan] = received[chan]
        self.Vup['z'] = np.array(output_data['z'])

        time.sleep(1)

        output_data, received = self.piezos.sweep(Vend, Vstart,
                                        chan_in = self._daq_inputs,
                                        sweep_rate = self.scan_rate)

        for chan in self._daq_inputs:
            self.Vdown[chan] = received[chan]
        self.Vdown['z'] = np.array(output_data['z'])

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
        #super().plot()
        labels = {'dc':'DC Flux (A.U.)', 'cap':"Capacitance (A.U.)", 
                'acx':"AC X (A.U.)", 'acy':"AC Y (A.U.)"}

        #self.fig, self.axes = plt.subplots(4, 1, figsize=(6,10), sharex=True)
        self.fig.subplots_adjust(hspace=0)
        axes = [self.axes[0], self.axes[1], self.axes[2], self.axes[3]]
        for chan, ax in zip(self._daq_inputs, axes):
            ax.plot(self.Vup['z'], self.Vup[chan])
            ax.plot(self.Vdown['z'], self.Vdown[chan])
            ax.set_ylabel(labels[chan])

        self.axes[3].set_xlabel("Z Position (V)")
        self.axes[0].set_title(self.timestamp, size="medium")


    #def save(self, filename=None, savefig=True, **kwargs):
        # the problem is axes is not an attrdict
    #    self._save(filename, savefig=True, ignored=["axes"], **kwargs)
