import numpy as np
from .planefit import Planefit
import time, os
from datetime import datetime
import matplotlib.pyplot as plt
from ..Utilities import plotting, conversions
from ..Instruments import piezos, nidaq, montana, squidarray
from ..Utilities.save import Measurement, get_todays_data_path


class Scanline(Measurement):
    _chan_labels = ['dc','cap','ac x','ac y']
    instrument_list = ['piezos','montana','squidarray','preamp','lockin_squid','lockin_cap','atto']

    Vout = np.nan
    Vdc = np.nan
    Vac_x = np.nan
    Vac_y = np.nan
    C = np.nan
    output_data = np.nan
    _append = 'line'

    def __init__(self, instruments={}, plane=None, start=(-100,-100), end=(100,100), scanheight=15, scan_rate=120, return_to_zero=True):
        super().__init__(self._append)

        self._load_instruments(instruments)

        self.start = start
        self.end = end
        self.return_to_zero = return_to_zero

        if not plane:
            plane = Planefit()
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
        self.output_data, received = self.piezos.sweep(Vstart, Vend, chan_in=in_chans, sweep_rate=self.scan_rate) # sweep over Y

        dist_between_points = np.sqrt((self.output_data['x'][0]-self.output_data['x'][-1])**2+(self.output_data['y'][0]-self.output_data['y'][-1])**2)
        self.Vout = np.linspace(0, dist_between_points, len(self.output_data['x'])) # plots vs 0 to whatever the maximum distance travelled was

        # Store this line's signals for Vdc, Vac x/y, and Cap
        # Convert from DAQ volts to lockin volts
        Vdc = received['dc']
        self.Vdc = self.lockin_squid.convert_output(Vdc)

        Vac_x = received['ac x']
        self.Vac_x = self.lockin_squid.convert_output(Vac_x)

        Vac_y = received['ac y']
        self.Vac_y = self.lockin_squid.convert_output(Vac_y)

        Vcap = received['cap']
        Vcap = self.lockin_cap.convert_output(Vcap) # convert to a lockin voltage
        self.C = Vcap*conversions.V_to_C # convert to capacitance (fF)


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

        self.ax['dc'].plot(self.Vout*conversions.Vpiezo_to_micron, self.Vdc*conversions.Vsquid_to_phi0, '-b')
        self.ax['ac x'].plot(self.Vout*conversions.Vpiezo_to_micron, self.Vac_x*conversions.Vsquid_to_phi0, '-b')
        self.ax['ac y'].plot(self.Vout*conversions.Vpiezo_to_micron, self.Vac_y*conversions.Vsquid_to_phi0, '-b')
        self.ax['cap'].plot(self.Vout*conversions.Vpiezo_to_micron, self.C, '-b')

        self.fig.canvas.draw()


    def save(self, savefig=True):
        '''
        Saves the scanline object.
        Also saves the figure as a pdf, if wanted.
        '''

        self._save(get_todays_data_path(), self.filename)

        if savefig and hasattr(self, 'fig'):
            self.fig.savefig(os.path.join(get_todays_data_path(), self.filename+'.pdf'), bbox_inches='tight')


    def setup_plots(self):
        self.fig = plt.figure(figsize=(8,5))

        self.ax['dc'] = self.fig.add_subplot(221)
        self.ax['ac x'] = self.fig.add_subplot(223)
        self.ax['ac y'] = self.fig.add_subplot(224)
        self.ax['cap'] = self.fig.add_subplot(222)

        for label, ax in self.ax.items():
            ax.set_xlabel(r'$\sim\mu\mathrm{m} (|V_{piezo}|*%.2f)$'
                                %conversions.Vpiezo_to_micron
                    )
            ax.set_ylabel('%s ($\phi_0$)' %label)
            ax.set_title(self.filename)
