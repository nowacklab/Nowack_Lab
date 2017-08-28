import numpy as np
import time, os
import matplotlib.pyplot as plt
from ..Utilities import conversions
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict


class Scanline(Measurement):
    _daq_inputs = ['dc','cap','acx','acy']
    _conversions = AttrDict({
        # Assume high; changed in init when array loaded
        'dc': conversions.Vsquid_to_phi0['High'],
        'cap': conversions.V_to_C,
        'acx': conversions.Vsquid_to_phi0['High'],
        'acy': conversions.Vsquid_to_phi0['High'],
        'x': conversions.Vx_to_um,
        'y': conversions.Vy_to_um
    })
    _units = AttrDict({
        'dc': 'phi0',
        'cap': 'C',
        'acx': 'phi0',
        'acy': 'phi0',
        'x': '~um',
        'y': '~um',
    })
    instrument_list = ['piezos','montana','squidarray','preamp','lockin_squid','lockin_cap','atto']

    def __init__(self, instruments={}, plane=None, start=(-100,-100),
                 end=(100,100), scanheight=15, scan_rate=120, zero=True):
        super().__init__(instruments=instruments)

        # Load the correct SAA sensitivity based on the SAA feedback
        # resistor
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

        self.start = start
        self.end = end
        self.zero = zero

        self.plane = plane

        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? If not, enter \'quit.\'')
            if inp == 'quit':
                raise Exception('Terminated by user')
        self.scanheight = scanheight
        self.scan_rate = scan_rate

        self.V = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo']
        })
        self.Vout = np.nan

        for chan in self._daq_inputs:
            # If no conversion factor is given then directly record the
            # voltage by setting conversion = 1
            if chan not in self._conversions.keys():
                self._conversions[chan] = 1
            if chan not in self._units.keys():
                self._units[chan] = 'V'

    def do(self):
        # Start and end points
        Vstart = {'x': self.start[0],
                'y': self.start[1],
                'z': self.plane.plane(self.start[0],self.start[1]) - self.scanheight
                }
        Vend = {'x': self.end[0],
                'y': self.end[1],
                'z': self.plane.plane(self.end[0],self.end[1]) - self.scanheight
                }

        # Explicitly go to first point of scan
        self.piezos.V = Vstart
        self.squidarray.reset()
        time.sleep(3*self.lockin_squid.time_constant)

        # Do the sweep
        output_data, received = self.piezos.sweep(Vstart, Vend,
                                                  chan_in=self._daq_inputs,
                                                  sweep_rate=self.scan_rate
                                                  ) # sweep over Y

        for axis in ['x','y','z']:
            self.V[axis] = output_data[axis]

        dist_between_points = np.sqrt((self.V['x'][0]-self.V['x'][-1])**2+(self.V['y'][0]-self.V['y'][-1])**2)
        self.Vout = np.linspace(0, dist_between_points, len(self.V['x'])) # plots vs 0 to whatever the maximum distance travelled was

        # Store this line's signals for Vdc, Vac x/y, and Cap
        # Convert from DAQ volts to lockin volts
        for chan in self._daq_inputs:
            self.V[chan] = received[chan]

        for chan in ['acx','acy']:
            self.V[chan] = self.lockin_squid.convert_output(self.V[chan])
        self.V['cap'] = self.lockin_cap.convert_output(self.V['cap'])

        self.plot()

        if self.zero:
            self.piezos.V = 0

    def plot(self):
        '''
        Set up all plots.
        '''
        super().plot()

        for chan in self._daq_inputs:
            self.ax[chan].plot(self.Vout*self._conversions['x'], self.V[chan], '-')

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
                                %self._conversions['x']
                    )
            ax.set_ylabel('%s ($\phi_0$)' %label)
            ax.set_title(self.filename)
            ax.yaxis.get_major_formatter().set_powerlimits((-2, 2))

        self.ax['cap'].set_ylabel('cap (C)')
