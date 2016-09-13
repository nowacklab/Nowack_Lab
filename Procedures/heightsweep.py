import numpy as np
from . import planefit
import matplotlib.pyplot as plt
from ..Instruments import piezos, nidaq, montana
import time, os
from datetime import datetime
from ..Utilities.save import Measurement
from ..Utilities.plotting import plot_bokeh as pb

_home = os.path.expanduser("~")
DATA_FOLDER = os.path.join(_home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'heightsweeps')

class Heightsweep(Measurement):
    def __init__(self, instruments = None, x=0, y=0, plane=None, inp_acx = 0, inp_acy=1, inp_dc = 2):
        if instruments:
            self.piezos = instruments['piezos']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
        else:
            self.piezos = None
            self.daq = None
            self.montana = None
            print('Instruments not loaded... can only plot!')

        self.x = x
        self.y = y
        # if plane is None:
        #     plane = planefit.Planefit()
        self.plane = plane
        self.inp_acx = 'ai%s' %inp_acx
        self.inp_acy = 'ai%s' %inp_acy
        self.inp_dc = 'ai%s' %inp_dc

        self.z = np.array([])
        self.Vacx = np.array([])
        self.Vacy = np.array([])
        self.Vdc = np.array([])

        self.filename = ''

    def __getstate__(self):
        super().__getstate__() # from Measurement superclass,
                               # need this in every getstate to get save_dict
        self.save_dict.update({"timestamp": self.timestamp,
                          "piezos": self.piezos,
                          "daq": self.daq,
                          "montana": self.montana,
                          "x": self.x,
                          "y": self.y,
                          "plane": self.plane,
                          "inp_acx": self.inp_acx,
                          "inp_acy": self.inp_acy,
                          "inp_dc": self.inp_dc
                      })
        return self.save_dict

    def do(self):
        #record the time when the measurement starts
        super().make_timestamp_and_filename('spectra')

        self.temp_start = self.montana.temperature['platform']

        Vstart = {'z': self.plane.plane(self.x, self.y)}
        Vend = {'z': -self.piezos.Vmax['z']}

        self.piezos.V = {'x':self.x, 'y':self.y, 'z': Vstart['z']}
        time.sleep(3) # wait at the surface

        self.daq.add_input(self.inp_acx)
        self.daq.add_input(self.inp_acy)
        self.daq.add_input(self.inp_dc)
        out, V, t = self.piezos.sweep(Vstart, Vend)

        self.z = self.plane.plane(self.x, self.y)-np.array(out['z'])
        self.Vacx = V[self.inp_acx]
        self.Vacy = V[self.inp_acy]
        self.Vdc = V[self.inp_dc]

        self.piezos.zero()

        self.plot()

        self.save()


    def plot(self):
        self.fig_dc = pb.figure(
            title = self.filename + '@(%f, %f)'%(self.x, self.y),
            ylabel = 'DC (V)',
            show_legend=False
        )
        self.fig_dc.fig.plot_width = 1000
        self.fig_dc.fig.min_border_bottom = 0

        self.fig_acx = pb.figure(
            ylabel = 'AC X (V)',
            show_legend=False,
            x_range = self.fig_dc.fig.x_range #link pan
        )
        self.fig_acx.fig.plot_width = 1000
        self.fig_acx.fig.min_border_top = 0
        self.fig_acx.fig.min_border_bottom = 0

        self.fig_acy = pb.figure(
            xlabel = "Voltage below touchdown (Vpiezo)",
            ylabel = 'AC Y (V)',
            show_legend=False,
            x_range = self.fig_dc.fig.x_range
        )
        self.fig_acy.fig.plot_width = 1000
        self.fig_acy.fig.min_border_top = 0


        self.line_dc = pb.line(self.fig_dc, self.z, self.Vdc, linestyle='o')
        self.line_acx = pb.line(self.fig_acx, self.z, self.Vacx, linestyle='o')
        self.line_acy = pb.line(self.fig_acy, self.z, self.Vacy, linestyle='o')

        self.grid = pb.plot_grid([[self.fig_dc.fig], [self.fig_acx.fig], [self.fig_acy.fig]])
        pb.show(self.grid)

    def save(self, savefig=True):
        '''
        Saves the heightsweep object to json in .../TeamData/Montana/heightsweeps/
        Also saves the figure as pdf, if wanted.
        '''

        self.tojson(DATA_FOLDER, self.filename)

        if savefig:
            pb.save(self.fig, os.path.join(DATA_FOLDER, self.filename))
