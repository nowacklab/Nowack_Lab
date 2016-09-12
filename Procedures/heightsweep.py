import numpy as np
from . import planefit
import matplotlib.pyplot as plt
from ..Instruments import piezos, nidaq, montana
import time, os
from datetime import datetime
from ..Utilities.save import Measurement

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

        self.z = np.nan
        self.Vacx = np.nan
        self.Vacy = np.nan
        self.Vdc = np.nan

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
        Vend = {'z': -self.piezos.z.Vmax}

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
        self.fig = plt.figure()

        self.ax_dc = self.fig.add_subplot(311)
        self.ax_dc.set_xlabel(r'$V_z^{samp} - V_z (V)$')
        self.ax_dc.set_title('%s\nDC Magnetometry (V) at (%f,%f)' %(self.filename, self.x, self.y))
        self.ax_dc.plot(self.z, self.Vdc, '.k', markersize=6, alpha=0.5)

        self.ax_ac_x = self.fig.add_subplot(312)
        self.ax_ac_x.set_xlabel(r'$V_z^{samp} - V_z (V)$')
        self.ax_ac_x.set_title('%s\nX component AC Response (V) at (%f,%f)' %(self.filename, self.x, self.y))
        self.ax_ac_x.plot(self.z, self.Vacx, '.k', markersize=6)

        self.ax_ac_y = self.fig.add_subplot(313)
        self.ax_ac_y.set_xlabel(r'$V_z^{samp} - V_z (V)$')
        self.ax_ac_y.set_title('%s\nY component AC Response (V) at (%f,%f)' %(self.filename, self.x, self.y))
        self.ax_ac_y.plot(self.z, self.Vacy, '.k', markersize=6)

    def save(self, savefig=True):
        '''
        Saves the heightsweep object to json in .../TeamData/Montana/heightsweeps/
        Also saves the figure as pdf, if wanted.
        '''

        self.tojson(DATA_FOLDER, self.filename)

        if savefig:
            self.fig.savefig(os.path.join(DATA_FOLDER, self.filename+'.pdf')+'.pdf', bbox_inches='tight')
