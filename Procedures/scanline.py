import numpy as np
from .planefit import Planefit
import time, os
from datetime import datetime
import matplotlib.pyplot as plt
from ..Utilities import plotting, conversions
from ..Instruments import piezos, nidaq, montana, squidarray
from ..Utilities.save import Measurement, get_todays_data_path
from ..Utilities.utilities import AttrDict


class Scanline(Measurement):
    _chan_labels = ['dc','cap','acx','acy']
    _conversions = AttrDict({
        'dc': conversions.Vsquid_to_phi0,
        'cap': conversions.V_to_C,
        'acx': conversions.Vsquid_to_phi0,
        'acy': conversions.Vsquid_to_phi0,
        'piezo': conversions.Vxy_to_um
    })
    instrument_list = ['piezos','montana','squidarray','preamp','lockin_squid','lockin_cap','atto']

    V = AttrDict({
        chan: np.nan for chan in _chan_labels + ['piezo']
    })
    Vout = np.nan

    def __init__(self, instruments={}, plane=None, start=(-100,-100), end=(100,100), scanheight=15, scan_rate=120, return_to_zero=True):
        super().__init__()

        self._load_instruments(instruments)

        self.start = start
        self.end = end
        self.return_to_zero = return_to_zero

        self.plane = plane

        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? If not, enter \'quit.\'')
            if inp == 'quit':
                raise Exception('Terminated by user')
        self.scanheight = scanheight
        self.scan_rate = scan_rate


    def do(self):
        tstart = time.time()
        self.temp_start = self.montana.temperature['platform']

        ## Start and end points
        Vstart = {'x': self.start[0],
                'y': self.start[1],
                'z': self.plane.plane(self.start[0],self.start[1]) - self.scanheight
                }
        Vend = {'x': self.end[0],
                'y': self.end[1],
                'z': self.plane.plane(self.end[0],self.end[1]) - self.scanheight
                }

        ## Explicitly go to first point of scan
        self.piezos.V = Vstart
        self.squidarray.reset()
        # time.sleep(3)

        ## Do the sweep
        in_chans = self._chan_labels
        output_data, received = self.piezos.sweep(Vstart, Vend, chan_in=in_chans, sweep_rate=self.scan_rate) # sweep over Y

        for axis in ['x','y','z']:
            self.V[axis] = output_data[axis]

        dist_between_points = np.sqrt((self.V['x'][0]-self.V['x'][-1])**2+(self.V['y'][0]-self.V['y'][-1])**2)
        self.Vout = np.linspace(0, dist_between_points, len(self.V['x'])) # plots vs 0 to whatever the maximum distance travelled was

        # Store this line's signals for Vdc, Vac x/y, and Cap
        # Convert from DAQ volts to lockin volts
        for chan in self._chan_labels:
            self.V[chan] = received[chan]

        for chan in ['acx','acy']:
            self.V[chan] = self.lockin_squid.convert_output(self.V[chan])
        self.Vfull['cap'] = self.lockin_cap.convert_output(self.Vfull['cap'])

        self.plot()

        if self.return_to_zero:
            self.piezos.V = 0
        self.save()

        tend = time.time()
        print('Scan took %f minutes' %((tend-tstart)/60))


    def plot(self):
        '''
        Set up all plots.
        '''
        super().plot()

        for chan in self._chan_labels:
            self.ax[chan].plot(self.Vout*self._conversions['piezo'], self.V[chan], '-b')

        self.fig.tight_layout()
        self.fig.canvas.draw()


    def setup_plots(self):
        self.fig = plt.figure(figsize=(8,5))
        self.ax = AttrDict()

        self.ax['dc'] = self.fig.add_subplot(221)
        self.ax['acx'] = self.fig.add_subplot(223)
        self.ax['acy'] = self.fig.add_subplot(224)
        self.ax['cap'] = self.fig.add_subplot(222)

        for label, ax in self.ax.items():
            ax.set_xlabel(r'$\sim\mu\mathrm{m} (|V_{piezo}|*%.2f)$'
                                %conversions.Vpiezo_to_micron
                    )
            ax.set_ylabel('%s ($\phi_0$)' %label)
            ax.set_title(self.filename)
        self.ax['cap'].set_ylabel('cap (C)')
