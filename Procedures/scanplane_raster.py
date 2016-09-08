import numpy as np
from numpy.linalg import lstsq
from . import navigation, planefit
import time, os
from datetime import datetime
from scipy.interpolate import interp1d as interp
import matplotlib.pyplot as plt
from IPython import display
from numpy import ma
from ..Utilities import dummy, plotting
from ..Instruments import piezos, nidaq, montana, squidarray
from ..Utilities.save import Measurement

class Scanplane(Measurement):
    def __init__(self, instruments=None, span=[100,100], center=[0,0], numpts=[50,50], plane=dummy.Dummy(planefit.Planefit), scanheight=5, sig_in=0, cap_in=1, sig_in_ac_x=None, sig_in_ac_y=None, freq=1500):
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

        self.freq = freq

        self.sig_in = 'ai%s' %sig_in
        self.daq.add_input(self.sig_in)

        self.sig_in_ac_x = 'ai%s' %sig_in_ac_x
        self.daq.add_input(self.sig_in_ac_x)

        self.sig_in_ac_y = 'ai%s' %sig_in_ac_y
        self.daq.add_input(self.sig_in_ac_y)

        self.cap_in = 'ai%s' %cap_in
        self.daq.add_input(self.cap_in)

        self.span = span
        self.center = center
        self.numpts = numpts

        self.plane = plane
        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? \'q\' to quit.')
            if inp == 'q':
                raise Exception('Terminated by user')
        self.scanheight = scanheight

        self.x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y, indexing='ij') # indexing ij follows matrix indexing convention
        self.Z = self.plane.plane(self.X, self.Y) - self.scanheight

        self.V = np.full(self.X.shape, np.nan)
        self.Vac_x = np.full(self.X.shape, np.nan)
        self.Vac_y = np.full(self.X.shape, np.nan)
        self.C = np.full(self.X.shape, np.nan)

        self.last_full_out = []
        self.last_full_sweep = []
        self.last_interp_out = []
        self.last_interp_sweep = []
        self.linecuts = {}

        # self.swap = swap
        # if swap: # Will rotate scan 90 degrees? Not really tested. Got bugs if false. Keep it true for now. #20160717: just noticed kwarg default is False. Don't touch this for now...
        #     self.X = self.X.transpose()
        #     self.Y = self.Y.transpose()
        #     self.Z = self.Z.transpose()

        self.filename = ''

        home = os.path.expanduser("~")
        self.path = os.path.join(home,
                                'Dropbox (Nowack lab)',
                                'TeamData',
                                'Montana',
                                'Scans'
                            )

    def __getstate__(self):
        self.save_dict = {"start_time": self.timestamp.strftime("%Y-%m-%d %I:%M:%S %p"),
                          "end_time": self.end_time.strftime("%Y-%m-%d %I:%M:%S %p"),
                          "piezos": self.piezos,
                          "frequency": self.freq,
                          "daq": self.daq,
                          "montana": self.montana,
                          "array": self.array,
                          "linecuts": self.linecuts,
                          "V": self.V,
                          "Vac_x": self.Vac_x,
                          "Vac_y": self.Vac_y,
                          "C": self.C,
                          "plane": self.plane,
                          "span": self.span,
                          "center": self.center,
                          "numpts": self.numpts,
                          "preamp": self.preamp,
                          "squid_lockin": self.squid_lockin,
                          "capacitance_lockin": self.cap_lockin,
                          "attocubes": self.atto}
        return self.save_dict

    def do(self):
        self.setup_plots()

        ## Start time and temperature
        self.timestamp = datetime.now()
        self.filename = self.timestamp.strftime('%Y%m%d_%H%M%S') + '_scan'
        tstart = time.time()
        #temporarily commented out so we can scan witout internet on montana
        #computer
        #self.temp_start = self.montana.temperature['platform']

        ## make sure all points are not out of range of piezos before starting anything
        for i in range(self.X.shape[0]):
            self.piezos.check_lim({'x':self.X[i,:],
                                    'y':self.Y[i,:],
                                    'z':self.Z[i,:]
                                    }
                                )

        ## Loop over Y values
        for i in range(int(self.X.shape[1])): # loop over every line

            if i%2 == 0: # if even
                k = 0 # k is used to determine Vstart/Vend. For forward, will sweep from the 0th element to the -(k+1) = -1st = last element
            else: # if odd
                k = -1 # k is used to determine Vstart/Vend. For forward, will sweep from the -1st = last element to the -(k+1) = 0th = first element

            ## Explicitly go to first point of scan
            self.piezos.V = {'x': self.X[k,i], #k=0 for forward, k=-1 for backward
                            'y': self.Y[k,i],
                            'z': self.Z[k,i]
                            }
            self.array.reset()
            time.sleep(3)

            ## Do the sweep
            Vstart = {'x': self.X[k,i], 'y': self.Y[k,i], 'z': self.Z[k,i]}
            Vend = {'x': self.X[-(k+1),i], 'y': self.Y[-(k+1),i], 'z': self.Z[-(k+1),i]}
            out, V, t = self.piezos.sweep(Vstart, Vend, freq=self.freq) # sweep over X

            ## Flip the backwards sweeps
            if k == -1: # flip only the backwards sweeps
                for d in out, V:
                    for key, value in d.items():
                        d[key] = value[::-1] # flip the 1D array

            ## Save linecuts
            self.linecuts[str(i)] = {"Vstart": Vstart,
                                "Vend": Vend,
                                "Vsquid": {"Vdc": np.array(V[self.sig_in]).tolist(),  #why convert to array and then back to list??
                                           "Vac_x": np.array(V[self.sig_in_ac_x]).tolist(),
                                           "Vac_y": np.array(V[self.sig_in_ac_y]).tolist()}}

            ## Interpolate to the number of lines
            interp_func = interp(out['x'], V[self.sig_in])
            self.V[:,i] = interp_func(self.X[:,i]) # changes from actual output data to give desired number of points

            interp_func = interp(out['x'], V[self.sig_in_ac_x])
            self.Vac_x[:,i] = interp_func(self.X[:,i])

            interp_func = interp(out['x'], V[self.sig_in_ac_y])
            self.Vac_y[:,i] = interp_func(self.X[:,i])

            interp_func = interp(out['x'], V[self.cap_in])
            self.C[:,i] = interp_func(self.X[:,i])

            self.last_full_out = out['x']
            self.last_full_sweep = V[self.sig_in]
            self.save_line(i, Vstart)

            self.last_interp_out = self.X[:,i]
            self.last_interp_sweep = self.V[:,i]

            self.plot()


        self.piezos.V = 0
        self.save()

        self.end_time = datetime.now()
        tend = time.time()
        print('Scan took %f minutes' %((tend-tstart)/60))
        return


    def plot(self):
        '''
        Update all plots.
        '''
        plotting.update2D(self.im_squid, self.V)
        plotting.update2D(self.im_cap, self.C)
        plotting.update2D(self.im_ac_x, self.Vac_x)
        plotting.update2D(self.im_ac_y, self.Vac_y)
        self.plot_line()

        self.fig.canvas.draw()


    def setup_plots(self):
        '''
        Set up all plots.
        '''
        self.fig = plt.figure(figsize=(11,11))

        ## DC magnetometry
        self.ax_squid = self.fig.add_subplot(321)
        self.im_squid = plotting.plot2D(self.ax_squid,
                                        self.X,
                                        self.Y,
                                        self.V,
                                        title = '%s\nDC SQUID signal' %self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'Voltage from %s' %self.sig_in
                                    )

        ## AC x
        self.ax_ac_x = self.fig.add_subplot(323)
        self.im_ac_x = plotting.plot2D(self.ax_ac_x,
                                        self.X,
                                        self.Y,
                                        self.Vac_x,
                                        cmap='rainbow',
                                        title = '%s\nAC x SQUID signal' %self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'Voltage from %s' %self.sig_in_ac_x
                                    )

        ## AC y
        self.ax_ac_y = self.fig.add_subplot(325)
        self.im_ac_y = plotting.plot2D(self.ax_ac_y,
                                        self.X,
                                        self.Y,
                                        self.Vac_y,
                                        cmap='rainbow',
                                        title = '%s\nAC y SQUID signal' %self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'Voltage from %s' %self.sig_in_ac_y
                                    )

        ## Capacitance
        self.ax_cap = self.fig.add_subplot(324)
        self.im_cap = plotting.plot2D(self.ax_cap,
                                    self.X,
                                    self.Y,
                                    self.C,
                                    cmap='afmhot',
                                    title = '%s\nCapacitance' %self.filename,
                                    xlabel = r'$X (V_{piezo})$',
                                    ylabel = r'$Y (V_{piezo})$',
                                    clabel = 'Voltage from %s' %self.cap_in
                                )

        ## "Last full scan" plot
        self.ax_line = self.fig.add_subplot(326)
        self.ax_line.set_title('last full line scan', fontsize=8)
        self.line_full = self.ax_line.plot(self.last_full_out, self.last_full_sweep, '-.k') # commas only take first element of array? ANyway, it works.
        self.line_interp = self.ax_line.plot(self.last_interp_out, self.last_interp_sweep, '.r', markersize=12)
        self.ax_line.set_xlabel('X (a.u.)', fontsize=8)
        self.ax_line.set_ylabel('V', fontsize=8)

        self.line_full = self.line_full[0] # it is given as an array
        self.line_interp = self.line_interp[0]

        ## Draw everything in the notebook
        self.fig.canvas.draw()


    def plot_line(self):
        self.line_full.set_xdata(self.last_full_out)
        self.line_full.set_ydata(self.last_full_sweep)
        self.line_interp.set_xdata(self.last_interp_out)
        self.line_interp.set_ydata(self.last_interp_sweep)

        self.ax_line.relim()
        self.ax_line.autoscale_view()

        plotting.aspect(self.ax_line, .3)

    def save(self):
        filename = os.path.join(self.path, self.filename)

        self.fig.savefig(filename+'.pdf')

        with open(filename+'.csv', 'w') as f:
            for s in ['span', 'center', 'numpts']:
                f.write('%s = %f, %f \n' %(s, float(getattr(self, s)[0]),float(getattr(self, s)[1])))
            for s in ['a','b','c']:
                f.write('plane.%s = %f\n' %(s, float(getattr(self.plane, s))))
            f.write('scanheight = %f\n' %self.scanheight)
            f.write('Montana info: \n'+self.montana.log()+'\n')
            #f.write('starting temperature: %f' %self.temp_start)

            f.write('DC signal\n')
            f.write('X (V),Y (V),V (V)\n')
            for i in range(self.X.shape[0]):
                for j in range(self.X.shape[1]):
                    if self.V[i][j] != None:
                        f.write('%f' %self.X[i][j] + ',' + '%f' %self.Y[i][j] + ',' + '%f' %self.V[i][j] + '\n')

            f.write('AC x signal\n')
            f.write('X (V),Y (V),V (V)\n')
            for i in range(self.X.shape[0]):
                for j in range(self.X.shape[1]):
                    if self.Vac_x[i][j] != None:
                        f.write('%f' %self.X[i][j] + ',' + '%f' %self.Y[i][j] + ',' + '%f' %self.Vac_x[i][j] + '\n')

            f.write('AC y signal\n')
            f.write('X (V),Y (V),V (V)\n')
            for i in range(self.X.shape[0]):
                for j in range(self.X.shape[1]):
                    if self.Vac_y[i][j] != None:
                        f.write('%f' %self.X[i][j] + ',' + '%f' %self.Y[i][j] + ',' + '%f' %self.Vac_y[i][j] + '\n')


    def save_line(self, i, Vstart):
        filename = os.path.join(self.path, self.filename)

        with open(filename+'_lines.csv', 'a') as f:
            f.write('Line %i, starting at: ' %i)
            for k in ['x','y','z']:
                f.write(str(Vstart[k])+',')
            f.write('\n Vpiezo:\n ')
            for x in self.last_full_sweep:
                f.write(str(x)+',')
            f.write('\n Vsquid:\n')
            for x in self.last_full_out:
                f.write(str(x)+',')

if __name__ == '__main__':
    'hey'
