import numpy as np
from . import planefit
import time, os
from datetime import datetime
import matplotlib.pyplot as plt
from ..Utilities import dummy, plotting
from ..Instruments import piezos, nidaq, montana, squidarray
from .save import Measurement

class Scanline(Measurement):
    def __init__(self, instruments=None, start=(-100,-100), end=(100,100), plane=dummy.Dummy(planefit.Planefit), scanheight=0, sig_in=0, cap_in=1, sig_in_ac_x=None, sig_in_ac_y=None, freq=1500, return_to_zero=True):
        if instruments:
            self.piezos = instruments['piezos']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
            self.array = instruments['squidarray']
            self.preamp = instruments['preamp']
            self.squid_lockin = instruments['squid_lockin']
            self.cap_lockin = instruments['cap_lockin']
            self.atto = instruments['attocube']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.daq = dummy.Dummy(nidaq.NIDAQ)
            self.montana = dummy.Dummy(montana.Montana)
            self.array = dummy.Dummy(squidarray.SquidArray)

        self.sig_in = 'ai%s' %sig_in
        self.daq.add_input(self.sig_in)

        self.sig_in_ac_x = 'ai%s' %sig_in_ac_x
        self.daq.add_input(self.sig_in_ac_x)

        self.sig_in_ac_y = 'ai%s' %sig_in_ac_y
        self.daq.add_input(self.sig_in_ac_y)

        self.cap_in = 'ai%s' %cap_in
        self.daq.add_input(self.cap_in)

        self.start = start
        self.end = end
        self.return_to_zero = return_to_zero

        self.plane = plane
        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? If not, enter \'quit.\'')
            if inp == 'quit':
                raise Exception('Terminated by user')
        self.scanheight = scanheight
        self.freq = freq

        self.filename = ''

        home = os.path.expanduser("~")
        self.path = os.path.join(home,
                                'Dropbox (Nowack lab)',
                                'TeamData',
                                'Montana',
                                'Scans'
                            )

    def __getstate__(self):
        self.save_dict = {"timestamp": self.timestamp,
                          "piezos": self.piezos,
                          "daq": self.daq,
                          "montana": self.montana,
                          "squidarray": self.array,
                          "lockin": self.lockin,
                          "preamp":self.preamp,
                          "start": self.start,
                          "end": self.end,
                          "freq": self.freq,
                          "V": self.V,
                          "Vac_x": self.Vac_x,
                          "Vac_y": self.Vac_y,
                          "squid_lockin": self.squid_lockin,
                          "capacitance_lockin": self.cap_lockin,
                          "attocubes": self.atto}
        return self.save_dict

    def do(self):
        ## Start time and temperature
        self.timestamp = datetime.now()
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_line'
        self.timestamp = time.strftime("%Y-%m-%d %I:%M:%S %p")
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
        self.array.reset()
        # time.sleep(3)

        ## Do the sweep
        self.out, V, t = self.piezos.sweep(Vstart, Vend, freq=self.freq) # sweep over Y

        dist_between_points = np.sqrt((self.out['x'][0]-self.out['x'][-1])**2+(self.out['y'][0]-self.out['y'][-1])**2)
        self.Vout = np.linspace(0, dist_between_points, len(self.out['x'])) # plots vs 0 to whatever the maximum distance travelled was
        self.V = V[self.sig_in]
        self.C = V[self.cap_in]
        self.Vac_x = V[self.sig_in_ac_x]
        self.Vac_y = V[self.sig_in_ac_y]

        self.plot()

        if self.return_to_zero:
            self.piezos.V = 0
        self.save()

        tend = time.time()
        print('Scan took %f minutes' %((tend-tstart)/60))
        return


    def plot(self):
        '''
        Set up all plots.
        '''
        self.fig = plt.figure(figsize=(8,5))

        ## DC magnetometry
        self.ax_squid = self.fig.add_subplot(221)
        self.ax_squid.plot(self.Vout, self.V, '-b')
        self.ax_squid.set_xlabel('$\sqrt{\Delta V_x^2+\Delta V_y^2}$')
        self.ax_squid.set_ylabel('Voltage from %s' %self.sig_in)
        self.ax_squid.set_title('%s\nDC SQUID signal' %self.filename)

        ## AC in-phase
        self.ax_squid = self.fig.add_subplot(223)
        self.ax_squid.plot(self.Vout, self.Vac_x, '-b')
        self.ax_squid.set_xlabel('$\sqrt{\Delta V_x^2+\Delta V_y^2}$')
        self.ax_squid.set_ylabel('Voltage from %s' %self.sig_in_ac_x)
        self.ax_squid.set_title('%s\nAC x SQUID signal' %self.filename)

        ## AC out-of-phase
        self.ax_squid = self.fig.add_subplot(224)
        self.ax_squid.plot(self.Vout, self.Vac_y, '-b')
        self.ax_squid.set_xlabel('$\sqrt{\Delta V_x^2+\Delta V_y^2}$')
        self.ax_squid.set_ylabel('Voltage from %s' %self.sig_in_ac_y)
        self.ax_squid.set_title('%s\nAC y SQUID signal' %self.filename)

        ## Capacitance
        self.ax_squid = self.fig.add_subplot(222)
        self.ax_squid.plot(self.Vout, self.C, '-b')
        self.ax_squid.set_xlabel('$\sqrt{\Delta V_x^2+\Delta V_y^2}$')
        self.ax_squid.set_ylabel('Voltage from %s' %self.cap_in)
        self.ax_squid.set_title('%s\nCapacitance signal' %self.filename)

        ## Draw everything in the notebook
        self.fig.canvas.draw()


    def save(self):
        filename = os.path.join(self.path, self.filename)

        self.fig.savefig(filename+'.pdf')

        with open(filename+'.csv', 'w') as f:
            for s in ['start', 'end']:
                f.write('%s = %f, %f \n' %(s, float(getattr(self, s)[0]),float(getattr(self, s)[1])))
            for s in ['a','b','c']:
                f.write('plane.%s = %f\n' %(s, float(getattr(self.plane, s))))
            f.write('scanheight = %f\n' %self.scanheight)
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('starting temperature: %f' %self.temp_start)

            f.write('\nDC signal\n')
            f.write('Xout (V),Yout (V), V (V)\n')
            for i in range(len(self.Vout)):
                f.write('%f' %self.out['x'][i] + ',' +'%f' %self.out['y'][i] + ',' + '%f' %self.V[i] + '\n')

            f.write('AC x signal\n')
            f.write('Xout (V),Yout (V), V (V)\n')
            for i in range(len(self.Vout)):
                f.write('%f' %self.out['x'][i] + ',' +'%f' %self.out['y'][i] + ',' + '%f' %self.Vac_x[i] + '\n')

            f.write('AC y signal\n')
            f.write('Xout (V),Yout (V), V (V)\n')
            for i in range(len(self.Vout)):
                f.write('%f' %self.out['x'][i] + ',' +'%f' %self.out['y'][i] + ',' + '%f' %self.Vac_y[i] + '\n')


if __name__ == '__main__':
    'hey'
