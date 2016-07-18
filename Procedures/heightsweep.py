import numpy as np
from . import planefit
import matplotlib.pyplot as plt
from ..Utilities import dummy
from ..Instruments import piezos, nidaq, montana
import time, os

class Heightsweep():
    def __init__(self, instruments = None, x =0, y=0, plane=dummy.Dummy(planefit.Planefit), acx_in = 0, acy_in=1, dc_in = 2):
        if instruments:
            self.piezos = instruments['piezos']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.daq = dummy.Dummy(nidaq.NIDAQ)
            self.montana = dummy.Dummy(montana.Montana)

        self.x = x
        self.y = y
        self.plane = plane
        self.acx_in = 'ai%s' %acx_in
        self.acy_in = 'ai%s' %acy_in
        self.dc_in = 'ai%s' %dc_in

        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_heightsweep'

    def do(self):
        self.temp_start = self.montana.temperature['platform']

        Vstart = {'z': self.plane.plane(self.x, self.y)}
        Vend = {'z': -self.piezos.Vmax['z']}

        self.piezos.V = {'x':self.x, 'y':self.y, 'z': Vstart['z']}
        time.sleep(3) # wait at the surface

        self.daq.add_input(self.acx_in)
        self.daq.add_input(self.acy_in)
        self.daq.add_input(self.dc_in)
        out, V, t = self.piezos.sweep(Vstart, Vend)

        self.z = self.plane.plane(self.x, self.y)-np.array(out['z'])
        self.Vacx = V[self.acx_in]
        self.Vacy = V[self.acy_in]
        self.Vdc = V[self.dc_in]

        self.piezos.zero()

        self.plot()

        self.save()



    def plot(self):
        #self.fig, self.ax = plt.subplots()
        #plt.title('%s\nHeight sweep at (%f, %f)' %(self.filename, self.x, self.y), fontsize=20)
        #self.ax.set_xlabel(r'$V_z^{samp} - V_z (V)$', fontsize=20)
        #self.ax.set_ylabel('AC Response (V)', fontsize=20)

        #self.ax2 = self.ax.twinx()
        #self.ax2.plot(self.z, self.Vdc, '.r', markersize=6, alpha=0.5)
        #self.ax.plot(self.z, self.Vac, '.k', markersize=6, alpha=0.5)
        #self.ax2.set_ylabel('DC Magnetometry (V)', color='r', fontsize=20)
        self.fig = plt.figure()

        self.ax_dc = self.fig.add_subplot(311)
        self.ax_dc.set_xlabel(r'$V_z^{samp} - V_z (V)$')
        self.ax_dc.set_title('DC Magnetometry (V)')
        self.ax_dc.plot(self.z, self.Vdc, '.k', markersize=6, alpha=0.5)

        self.ax_ac_x = self.fig.add_subplot(312)
        self.ax_ac_x.set_xlabel(r'$V_z^{samp} - V_z (V)$')
        self.ax_ac_x.set_title('X component AC Response (V)')
        self.ax_ac_x.plot(self.z, self.Vacx, '.k', markersize=6)

        self.ax_ac_y = self.fig.add_subplot(313)
        self.ax_ac_y.set_xlabel(r'$V_z^{samp} - V_z (V)$')
        self.ax_ac_y.set_title('Y component AC Response (V)')
        self.ax_ac_y.plot(self.z, self.Vacy, '.k', markersize=6)

    def save(self):
        home = os.path.expanduser("~")
        data_folder = os.path.join(home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'Height sweeps')

        filename = os.path.join(data_folder, self.filename)

        with open(filename+'.csv', 'w') as f:
            f.write('x = %f\n' %self.x)
            f.write('y = %f\n' %self.y)
            for s in ['a','b','c']:
                f.write('plane.%s = %f\n' %(s, float(getattr(self.plane, s))))
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('starting temperature: %f\n' %self.temp_start)

            f.write('Z(V), Vacx(V), Vacy, Vdc(V)\n')
            for i in range(len(self.z)):
                f.write('%f, %f, %f, %f\n' %(self.z[i], self.Vacx[i], self.Vacy[i], self.Vdc[i]))

        self.fig.savefig(filename+'.pdf', bbox_inches='tight')
