import numpy as np
from . import navigation, planefit
import matplotlib.pyplot as plt
from ..Utilities import dummy
from ..Instruments import piezos, nidaq, montana
import time, os 

class Heightsweep():
    def __init__(self, instruments = None, x =0, y=0, plane=dummy.Dummy(planefit.Planefit), ac_in = 0, dc_in = 1):
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
        self.ac_in = 'ai%s' %ac_in
        self.dc_in = 'ai%s' %dc_in

        self.nav = navigation.Goto(self.piezos)
        
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_heightsweep'
        
    def do(self):
        self.temp_start = self.montana.temperature['platform']
        
        Vstart = {'z': self.plane.plane(self.x, self.y)}
        Vend = {'z': -self.piezos.Vmax['z']}
        
        self.nav.goto_seq(self.x, self.y, Vstart['z'])
        time.sleep(3) # wait at the surface
        
        self.daq.add_input(self.ac_in)
        self.daq.add_input(self.dc_in)
        out, V, t = self.piezos.sweep(Vstart, Vend)
        
        self.z = self.plane.plane(self.x, self.y)-np.array(out['z'])
        self.Vac = V[self.ac_in]
        self.Vdc = V[self.dc_in]
        
        self.nav.goto_seq(0,0,0)

        self.plot()
        
        self.save()

        
        
    def plot(self):
        self.fig, self.ax = plt.subplots()
        plt.title('%s\nHeight sweep at (%f, %f)' %(self.filename, self.x, self.y), fontsize=20)
        self.ax.set_xlabel(r'$V_z^{samp} - V_z (V)$', fontsize=20)
        self.ax.set_ylabel('AC Response (V)', fontsize=20)
        
        self.ax2 = self.ax.twinx()
        self.ax2.plot(self.z, self.Vdc, '.r', markersize=6, alpha=0.5)
        self.ax.plot(self.z, self.Vac, '.k', markersize=6, alpha=0.5)
        self.ax2.set_ylabel('DC Magnetometry (V)', color='r', fontsize=20)
        
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
            f.write('starting temperature: %f' %self.temp_start)

            f.write('Z(V), Vac(V), Vdc(V)')
            for i in range(len(self.z)): 
                f.write('%f, %f, %f' %(self.z[i], self.Vac[i], self.Vdc[i]))
                
        self.fig.savefig(filename+'.pdf', bbox_inches='tight')
