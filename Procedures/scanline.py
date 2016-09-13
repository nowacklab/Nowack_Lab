import numpy as np
from . import planefit
import time, os
from datetime import datetime
import matplotlib.pyplot as plt
from ..Utilities import plotting
from ..Instruments import piezos, nidaq, montana, squidarray
from ..Utilities.save import Measurement
from ..Utilities.plotting import plot_bokeh as pb

_home = os.path.expanduser("~")
DATA_FOLDER = os.path.join(_home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'Scans')

class Scanline(Measurement):
    def __init__(self, instruments=None, start=(-100,-100), end=(100,100), plane=None, scanheight=0, inp_dc=0, inp_cap=1, inp_acx=None, inp_acy=None, freq=1500, return_to_zero=True):
        self.inp_dc = 'ai%s' %inp_dc
        self.inp_acx = 'ai%s' %inp_acx
        self.inp_acy = 'ai%s' %inp_acy
        self.inp_cap = 'ai%s' %inp_cap

        if instruments:
            self.piezos = instruments['piezos']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
            self.squidarray = instruments['squidarray']
            self.preamp = instruments['preamp']
            self.lockin_squid = instruments['lockin_squid']
            self.lockin_cap = instruments['lockin_cap']
            self.attocube = instruments['attocube']

            self.daq.add_input(self.inp_dc)
            self.daq.add_input(self.inp_acx)
            self.daq.add_input(self.inp_acy)
            self.daq.add_input(self.inp_cap)
        else:
            self.piezos = None
            self.daq = None
            self.montana = None
            self.squidarray = None
            self.preamp = None
            self.lockin_squid = None
            self.lockin_cap = None
            self.attocube = None
            print('Instruments not loaded... can only plot!')

        self.start = start
        self.end = end
        self.return_to_zero = return_to_zero

        if not plane:
            plane = planefit.Planefit()
        self.plane = plane

        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? If not, enter \'quit.\'')
            if inp == 'quit':
                raise Exception('Terminated by user')
        self.scanheight = scanheight
        self.freq = freq

        self.Vout = np.array([])
        self.V = np.array([])
        self.Vac_x = np.array([])
        self.Vac_y = np.array([])
        self.C = np.array([])

        self.filename = ''


    def __getstate__(self):
        super().__getstate__() # from Measurement superclass,
                               # need this in every getstate to get save_dict
        self.save_dict.update({"timestamp": self.timestamp,
                          "piezos": self.piezos,
                          "daq": self.daq,
                          "montana": self.montana,
                          "squidarray": self.squidarray,
                          "preamp":self.preamp,
                          "start": self.start,
                          "end": self.end,
                          "freq": self.freq,
                          "V": self.V,
                          "Vac_x": self.Vac_x,
                          "Vac_y": self.Vac_y,
                          "lockin_squid": self.lockin_squid,
                          "lockin_cap": self.lockin_cap,
                          "attocube": self.attocube
                      })
        return self.save_dict


    def do(self):
        super().make_timestamp_and_filename('scan_line')

        tstart = time.time()
        self.temp_start = self.montana.temperature['platform']

        ## Start and end points
        Vstart = {'x': self.start[0],
                'y': self.start[1],
                'z': self.plane.plane(self.start[0],self.start[1])
                }
        Vend = {'x': self.end[0],
                'y': self.end[1],
                'z': self.plane.plane(self.end[0],self.end[1])
                }

        ## Explicitly go to first point of scan
        self.piezos.V = Vstart
        self.squidarray.reset()
        # time.sleep(3)

        ## Do the sweep
        self.out, V, t = self.piezos.sweep(Vstart, Vend, freq=self.freq) # sweep over Y

        dist_between_points = np.sqrt((self.out['x'][0]-self.out['x'][-1])**2+(self.out['y'][0]-self.out['y'][-1])**2)
        self.Vout = np.linspace(0, dist_between_points, len(self.out['x'])) # plots vs 0 to whatever the maximum distance travelled was
        self.V = V[self.inp_dc]
        self.C = V[self.inp_cap]
        self.Vac_x = V[self.inp_acx]
        self.Vac_y = V[self.inp_acy]

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
        self.fig_dc = pb.figure(
            title = self.filename,
            ylabel = 'DC %s (V)' %self.inp_dc
        )
        self.line_dc = pb.line(self.fig_dc, self.Vout, self.V)

        self.fig_cap = pb.figure(
            xlabel = 'Distance (V)',
            ylabel = 'Cap %s (V)' %self.inp_cap,
            x_range = self.fig_dc.fig.x_range
        )
        self.line_cap = pb.line(self.fig_cap, self.Vout, self.C)

        self.fig_acx = pb.figure(
            ylabel = 'AC X %s (V)' %self.inp_acx,
            x_range = self.fig_dc.fig.x_range
        )
        self.line_cap = pb.line(self.fig_acx, self.Vout, self.Vac_x)

        self.fig_acy = pb.figure(
            ylabel = 'AC Y %s (V)' %self.inp_acy,
            x_range = self.fig_dc.fig.x_range
        )
        self.line_cap = pb.line(self.fig_acy, self.Vout, self.Vac_y)

        self.grid = pb.plot_grid([[self.fig_dc.fig, self.fig_acx.fig],[self.fig_cap.fig, self.fig_acy.fig]])
        pb.show(self.grid)

    def save(self, savefig=True):
        '''
        Saves the scanline object to json in .../TeamData/Montana/Scans/
        Also saves the figure as a pdf, if wanted.
        '''

        self.tojson(DATA_FOLDER, self.filename)

        if savefig:
            pb.save(self.grid, os.path.join(DATA_FOLDER, self.filename))


if __name__ == '__main__':
    'hey'
