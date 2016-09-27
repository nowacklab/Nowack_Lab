import numpy as np
from . import planefit
import time, os
from datetime import datetime
import matplotlib.pyplot as plt
from ..Utilities import plotting, conversions
from ..Instruments import piezos, nidaq, montana, squidarray
from ..Utilities.save import Measurement, get_todays_data_path


class Scanline(Measurement):
    instrument_list = ['piezos','montana','squidarray','preamp','lockin_squid','lockin_cap','atto']

    Vout = np.nan
    V = np.nan
    Vac_x = np.nan
    Vac_y = np.nan
    C = np.nan

    def __init__(self, instruments={}, start=(-100,-100), end=(100,100), plane=None, scanheight=0, inp_dc=0, inp_cap=1, inp_acx=None, inp_acy=None, scan_rate=120, return_to_zero=True):
        super().__init__('scan_line')

        self.inp_dc = 'ai%s' %inp_dc
        self.inp_acx = 'ai%s' %inp_acx
        self.inp_acy = 'ai%s' %inp_acy
        self.inp_cap = 'ai%s' %inp_cap

        self.load_instruments(instruments)

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
        self.scan_rate = scan_rate


    def __getstate__(self):
        self.save_dict.update({"timestamp": self.timestamp,
                          "piezos": self.piezos,
                          "montana": self.montana,
                          "squidarray": self.squidarray,
                          "preamp":self.preamp,
                          "start": self.start,
                          "end": self.end,
                          "scan_rate": self.scan_rate,
                          "V": self.V,
                          "Vac_x": self.Vac_x,
                          "Vac_y": self.Vac_y,
                          "lockin_squid": self.lockin_squid,
                          "lockin_cap": self.lockin_cap,
                          "atto": self.atto
                      })
        return self.save_dict


    def do(self):
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
        in_chans = [self.inp_dc, self.inp_acx, self.inp_acy, self.inp_cap]
        self.output_data, received = self.piezos.sweep(Vstart, Vend, chan_in=in_chans, sweep_rate=self.scan_rate) # sweep over Y

        dist_between_points = np.sqrt((self.output_data['x'][0]-self.output_data['x'][-1])**2+(self.output_data['y'][0]-self.output_data['y'][-1])**2)
        self.Vout = np.linspace(0, dist_between_points, len(self.output_data['x'])) # plots vs 0 to whatever the maximum distance travelled was
        self.V = received[self.inp_dc]
        Vcap = received[self.inp_cap]
        Vcap = self.lockin_cap.convert_output(Vcap) # convert to a lockin voltage
        self.C = Vcap*conversions.V_to_C # convert to true capacitance (fF)
        self.Vac_x = received[self.inp_acx]
        self.Vac_y = received[self.inp_acy]

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
        self.fig = plt.figure(figsize=(8,5))

        ## DC magnetometry
        self.ax_squid = self.fig.add_subplot(221)
        self.ax_squid.plot(self.Vout, self.V, '-b')
        self.ax_squid.set_xlabel('$\sqrt{\Delta V_x^2+\Delta V_y^2}$')
        self.ax_squid.set_ylabel('Voltage from %s' %self.inp_dc)
        self.ax_squid.set_title('%s\nDC SQUID signal' %self.filename)

        ## AC in-phase
        self.ax_squid = self.fig.add_subplot(223)
        self.ax_squid.plot(self.Vout, self.Vac_x, '-b')
        self.ax_squid.set_xlabel('$\sqrt{\Delta V_x^2+\Delta V_y^2}$')
        self.ax_squid.set_ylabel('Voltage from %s' %self.inp_acx)
        self.ax_squid.set_title('%s\nAC x SQUID signal' %self.filename)

        ## AC out-of-phase
        self.ax_squid = self.fig.add_subplot(224)
        self.ax_squid.plot(self.Vout, self.Vac_y, '-b')
        self.ax_squid.set_xlabel('$\sqrt{\Delta V_x^2+\Delta V_y^2}$')
        self.ax_squid.set_ylabel('Voltage from %s' %self.inp_acy)
        self.ax_squid.set_title('%s\nAC y SQUID signal' %self.filename)

        ## Capacitance
        self.ax_squid = self.fig.add_subplot(222)
        self.ax_squid.plot(self.Vout, self.C, '-b')
        self.ax_squid.set_xlabel('$\sqrt{\Delta V_x^2+\Delta V_y^2}$')
        self.ax_squid.set_ylabel('Capacitance from %s' %self.inp_cap)
        self.ax_squid.set_title('%s\nCapacitance signal' %self.filename)

        ## Draw everything in the notebook
        self.fig.canvas.draw()


    def save(self, savefig=True):
        '''
        Saves the scanline object to json in .../TeamData/Montana/Scans/
        Also saves the figure as a pdf, if wanted.
        '''

        self.tojson(get_todays_data_path(), self.filename)

        if savefig:
            self.fig.savefig(os.path.join(get_todays_data_path(), self.filename+'.pdf'), bbox_inches='tight')


if __name__ == '__main__':
    'hey'
