import numpy as np
import matplotlib.pyplot as plt
from ..Instruments import piezos, nidaq, montana
import time, os
from datetime import datetime
from ..Utilities.save import Measurement
from ..Utilities import conversions
from ..Utilities.utilities import AttrDict

class Heightsweep(Measurement):
    _daq_inputs = ['dc','acx','acy']
    _conversions = AttrDict({
        'dc': conversions.Vsquid_to_phi0,
        'acx': conversions.Vsquid_to_phi0,
        'acy': conversions.Vsquid_to_phi0,
        'z': conversions.Vz_to_um
    })
    instrument_list = ['piezos','montana','squidarray']


    def __init__(self, instruments = {}, plane=None, x=0, y=0, z0=0, scan_rate=120):
        super().__init__()

        self.x = x
        self.y = y
        self.z0 = z0
        self.plane = plane
        self.scan_rate = scan_rate
        self.V = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo', 'z']
        })

    def do(self):

        self.temp_start = self.montana.temperature['platform']

        Vstart = {'z': self.plane.plane(self.x, self.y) - self.z0}
        Vend = {'z': -self.piezos.z.Vmax}

        self.piezos.V = {'x':self.x, 'y':self.y, 'z': Vstart['z']}
        self.squidarray.reset()
        time.sleep(10) # wait at the surface

        output_data, received = self.piezos.sweep(Vstart, Vend,
                                        chan_in = self._daq_inputs,
                                        sweep_rate = self.scan_rate)

        for chan in self._daq_inputs:
            self.V[chan] = received[chan]
        self.V['z'] = self.plane.plane(self.x, self.y)-np.array(output_data['z'])-self.z0

        self.piezos.zero()

        self.plot()


    def plot(self):
        super().plot()

        for chan in self._daq_inputs:
            self.ax[chan].plot(self.V['z'], self.V[chan]*self._conversions[chan], '.k', markersize=6, alpha=0.5)


    def setup_plots(self):
        self.fig = plt.figure()
        self.fig.subplots_adjust(hspace=1.2)
        self.ax = AttrDict({})

        self.ax['dc'] = self.fig.add_subplot(311)
        self.ax['acx'] = self.fig.add_subplot(312)
        self.ax['acy'] = self.fig.add_subplot(313)

        for label, ax in self.ax.items():
            ax.set_xlabel(r'$V_z^{samp} - V_z (V)$')
            ax.set_title('%s\n%s (V) at (%.2f, %.2f)' %(self.filename, label, self.x, self.y))
