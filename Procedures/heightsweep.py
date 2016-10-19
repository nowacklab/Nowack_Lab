import numpy as np
from . import planefit
import matplotlib.pyplot as plt
from ..Instruments import piezos, nidaq, montana
import time, os
from datetime import datetime
from ..Utilities.save import Measurement, get_todays_data_path


class Heightsweep(Measurement):
    instrument_list = ['piezos','montana','squidarray']

    z = np.nan
    Vacx = np.nan
    Vacy = np.nan
    Vdc = np.nan
    _append = 'heightsweep'

    def __init__(self, instruments = {}, x=0, y=0, z0=0, plane=None, inp_acx = 0, inp_acy=1, inp_dc = 2, scan_rate=120):
        super().__init__(self._append)

        self._load_instruments(instruments)

        self.x = x
        self.y = y
        self.z0 = z0
        # if plane is None:
        #     plane = planefit.Planefit()
        self.plane = plane
        self.inp_acx = 'ai%s' %inp_acx
        self.inp_acy = 'ai%s' %inp_acy
        self.inp_dc = 'ai%s' %inp_dc
        self.scan_rate = scan_rate


    def do(self):

        self.temp_start = self.montana.temperature['platform']

        Vstart = {'z': self.plane.plane(self.x, self.y) - self.z0}
        Vend = {'z': -self.piezos.z.Vmax}

        self.piezos.V = {'x':self.x, 'y':self.y, 'z': Vstart['z']}
        self.squidarray.reset()
        time.sleep(10) # wait at the surface

        output_data, received = self.piezos.sweep(Vstart, Vend,
                                        chan_in = [self.inp_acx,
                                                    self.inp_acy,
                                                    self.inp_dc
                                                ],
                                        sweep_rate = self.scan_rate)

        self.z = self.plane.plane(self.x, self.y)-np.array(output_data['z'])-self.z0
        self.Vacx = received[self.inp_acx]
        self.Vacy = received[self.inp_acy]
        self.Vdc = received[self.inp_dc]

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
        Saves the heightsweep object.
        Also saves the figure as pdf, if wanted.
        '''

        self._save(get_todays_data_path(), self.filename)

        if savefig and hasattr(self, 'fig'):
            self.fig.savefig(os.path.join(get_todays_data_path(), self.filename+'.pdf')+'.pdf', bbox_inches='tight')
