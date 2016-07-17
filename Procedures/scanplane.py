import numpy as np
from numpy.linalg import lstsq
from . import navigation, planefit
import time, os
from scipy.interpolate import interp1d as interp
import matplotlib.pyplot as plt
from IPython import display
from numpy import ma
from ..Utilities import dummy
from ..Instruments import piezos, nidaq, montana

class Scanplane():
    def __init__(self, instruments=None, span=[100,100], center=[0,0], numpts=[50,50], plane=dummy.Dummy(planefit.Planefit), scanheight=5, sig_in=0, cap_in=1, swap=False, sig_in_ac_x=None, sig_in_ac_y=None):
        if instruments:
            self.piezos = instruments['piezos']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.daq = dummy.Dummy(nidaq.NIDAQ)
            self.montana = dummy.Dummy(montana.Montana)

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
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? If not, enter \'quit.\'')
            if inp == 'quit':
                raise Exception('Terminated by user')
        self.scanheight = scanheight

        self.x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y)
        self.Z = self.plane.plane(self.X, self.Y) - self.scanheight

        self.V = np.array([[float('nan')]*self.X.shape[0]]*self.X.shape[1])
        self.Vac_x = np.array([[float('nan')]*self.X.shape[0]]*self.X.shape[1])
        self.Vac_y = np.array([[float('nan')]*self.X.shape[0]]*self.X.shape[1])

        self.C = np.array([[float('nan')]*self.X.shape[0]]*self.X.shape[1])

        self.last_full_out = []
        self.last_full_sweep = []
        self.last_interp_out = []
        self.last_interp_sweep = []

        self.swap = swap
        if swap: # Will rotate scan 90 degrees? Not really tested. Got bugs if false. Keep it true for now.
            self.X = self.X.transpose()
            self.Y = self.Y.transpose()
            self.Z = self.Z.transpose()

        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_scan'

        home = os.path.expanduser("~")
        self.path = os.path.join(home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'Scans')

    def aspect(self, ax, ratio):
        xvals,yvals = ax.get_xlim(), ax.get_ylim()

        xrange = xvals[1]-xvals[0]
        yrange = yvals[1]-yvals[0]
        ax.set_aspect(ratio*(xrange/yrange), adjustable='box')

    def do(self):
        self.setup_plots()

        ## Start time and temperature
        tstart = time.time()
        self.temp_start = self.montana.temperature['platform']

        ## make sure all points are not out of range of piezos before starting anything
        for i in range(self.X.shape[0]):
            self.piezos.check_lim({'x':self.X[i][:], 'y':self.Y[i][:], 'z':self.Z[i][:]})

        ## Loop over X values
        for i in range(self.X.shape[0]):

            ## Explicitly go to first point of scan
            self.piezos.V = {'x': self.X[i][0], 'y': self.Y[i][0], 'z': self.Z[i][0]}

            ## Do the sweep
            Vstart = {'x': self.X[i][0], 'y': self.Y[i][0], 'z': self.Z[i][0]}
            Vend = {'x': self.X[i][-1], 'y': self.Y[i][-1], 'z': self.Z[i][-1]}
            out, V, t = self.piezos.sweep(Vstart, Vend) # sweep over Y

            interp_func = interp(out['x'], V[self.sig_in])
            self.V[i][:] = interp_func(self.X[i][:]) # changes from actual output data to give desired number of points

            interp_func = interp(out['x'], V[self.sig_in_ac_x])
            self.Vac_x[i][:] = interp_func(self.X[i][:])

            interp_func = interp(out['x'], V[self.sig_in_ac_y])
            self.Vac_y[i][:] = interp_func(self.X[i][:])

            self.last_full_out = out['x']
            self.last_full_sweep = V[self.sig_in]
            self.save_line(i, Vstart)

            ## Interpolate to the number of lines
            interp_func = interp(out['y'], V[self.sig_in])
            self.V[i][:] = interp_func(self.Y[i][:]) # changes from actual output data to give desired number of points

            self.last_interp_out = self.X[i][:]
            self.last_interp_sweep = self.V[i][:]

            # Do the same for capacitance
            interp_func = interp(out['x'], V[self.cap_in])
            self.C[i][:] = interp_func(self.X[i][:])

            self.plot()

        self.piezos.V = 0
        self.save()

        tend = time.time()
        print('Scan took %f minutes' %((tend-tstart)/60))
        return

    def plot(self):
        self.plot_squid()
        self.plot_cap()
        self.plot_line()
        self.plot_ac_x()
        self.plot_ac_y()
        self.fig.canvas.draw()
        #display.display(plt.gcf());
        #display.clear_output(wait=True)

    def setup_plots(self):
        self.fig = plt.figure(figsize=(12,12))

        self.ax_squid = self.fig.add_subplot(321)
        self.setup_plot_squid()

        self.ax_ac_x = self.fig.add_subplot(323)
        self.setup_plot_ac_x()

        self.ax_ac_y = self.fig.add_subplot(325)
        self.setup_plot_ac_y()

        self.ax_cap = self.fig.add_subplot(324)
        self.setup_plot_cap()

        self.ax_line = self.fig.add_subplot(326)
        self.setup_plot_line()

        self.fig.canvas.draw()

    def setup_plot_squid(self):
        Vm = ma.masked_where(np.isnan(self.V),self.V) #hides data not yet collected

        plt.title('%s\nSQUID signal' %self.filename, fontsize=8)
        self.im_squid = self.ax_squid.imshow(Vm, cmap='RdBu', interpolation='none',aspect='auto',origin='lower', extent=[min(self.X.flatten()), max(self.X.flatten()), min(self.Y.flatten()), max(self.Y.flatten())])

        self.aspect(self.ax_squid, 1)

        plt.xlabel(r'$X (V_{piezo})$', fontsize=8)
        plt.ylabel(r'$Y (V_{piezo})$', fontsize=8)
        self.cb_squid = plt.colorbar(self.im_squid, ax=self.ax_squid)
        self.cb_squid.set_label(label = 'Voltage from %s' %self.sig_in, fontsize=8)
        self.cb_squid.formatter.set_powerlimits((-2,2))

    def setup_plot_ac_x(self):
        Vm = ma.masked_where(np.isnan(self.Vac_x),self.Vac_x) #hides data not yet collected

        plt.title('%s\nAC x SQUID signal' %self.filename, fontsize=8)
        self.im_ac_x = self.ax_ac_x.imshow(Vm, cmap='rainbow', interpolation='none',aspect='auto',origin='lower', extent=[min(self.X.flatten()), max(self.X.flatten()), min(self.Y.flatten()), max(self.Y.flatten())])

        self.aspect(self.ax_ac_x, 1)

        plt.xlabel(r'$X (V_{piezo})$', fontsize=8)
        plt.ylabel(r'$Y (V_{piezo})$', fontsize=8)
        self.cb_ac_x = plt.colorbar(self.im_ac_x, ax=self.ax_ac_x)
        self.cb_ac_x.set_label(label = 'Voltage from %s' %self.sig_in_ac_x, fontsize=8)
        self.cb_ac_x.formatter.set_powerlimits((-2,2))

    def setup_plot_ac_y(self):
        Vm = ma.masked_where(np.isnan(self.Vac_y),self.Vac_y) #hides data not yet collected

        plt.title('%s\nAC y SQUID signal' %self.filename, fontsize=8)
        self.im_ac_y = self.ax_ac_y.imshow(Vm, cmap='gist_earth', interpolation='none',aspect='auto',origin='lower', extent=[min(self.X.flatten()), max(self.X.flatten()), min(self.Y.flatten()), max(self.Y.flatten())])

        self.aspect(self.ax_ac_y, 1)

        plt.xlabel(r'$X (V_{piezo})$', fontsize=8)
        plt.ylabel(r'$Y (V_{piezo})$', fontsize=8)
        self.cb_ac_y = plt.colorbar(self.im_ac_y, ax=self.ax_ac_y)
        self.cb_ac_y.set_label(label = 'Voltage from %s' %self.sig_in_ac_y, fontsize=8)
        self.cb_ac_y.formatter.set_powerlimits((-2,2))

    def plot_squid(self):
        Vm = ma.masked_where(np.isnan(self.V),self.V) #hides data not yet collected
        self.im_squid.set_array(Vm)

        # self.cb_squid.set_clim(-abs(Vm).max(), abs(Vm).max())
        self.cb_squid.set_clim(Vm.min(), Vm.max())
        self.cb_squid.draw_all()

    def plot_ac_x(self):
        Vm = ma.masked_where(np.isnan(self.Vac_x),self.Vac_x) #hides data not yet collected
        self.im_ac_x.set_array(Vm)

        # self.cb_squid.set_clim(-abs(Vm).max(), abs(Vm).max())
        self.cb_ac_x.set_clim(Vm.min(), Vm.max())
        self.cb_ac_x.draw_all()

    def plot_ac_y(self):
        Vm = ma.masked_where(np.isnan(self.Vac_y),self.Vac_y) #hides data not yet collected
        self.im_ac_y.set_array(Vm)

        # self.cb_squid.set_clim(-abs(Vm).max(), abs(Vm).max())
        self.cb_ac_y.set_clim(Vm.min(), Vm.max())
        self.cb_ac_y.draw_all()

    def setup_plot_cap(self):
        Cm = ma.masked_where(np.isnan(self.C),self.C) #hides data not yet collected

        plt.title('%s\ncapacitance' %self.filename, fontsize=8)
        self.im_cap = self.ax_cap.imshow(Cm, cmap='afmhot', interpolation='none', aspect='auto',origin='lower', extent=[min(self.X.flatten()), max(self.X.flatten()), min(self.Y.flatten()), max(self.Y.flatten())])

        aspect=self.aspect(self.ax_cap, 1)

        plt.xlabel(r'$X (V_{piezo})$', fontsize=8)
        plt.ylabel(r'$Y (V_{piezo})$', fontsize=8)

        self.cb_cap = plt.colorbar(self.im_cap, ax=self.ax_cap)
        self.cb_cap.set_label(label = 'Voltage from %s' %self.cap_in, fontsize=8)
        self.cb_cap.formatter.set_powerlimits((-2,2))

    def plot_cap(self):
        Cm = ma.masked_where(np.isnan(self.C),self.C) #hides data not yet collected
        self.im_cap.set_array(Cm)

        self.cb_cap.set_clim(Cm.min(), Cm.max())
        self.cb_cap.draw_all()

    def setup_plot_line(self):
        plt.title('last full line scan', fontsize=8)
        self.line_full, = plt.plot(self.last_full_out, self.last_full_sweep, '-.k') # commas only take first element of array? ANyway, it works.
        self.line_interp, = plt.plot(self.last_interp_out, self.last_interp_sweep, '.r', markersize=12)
        plt.xlabel('Y (a.u.)', fontsize=8)
        plt.ylabel('V', fontsize=8)

    def plot_line(self):
        self.line_full.set_xdata(self.last_full_out)
        self.line_full.set_ydata(self.last_full_sweep)
        self.line_interp.set_xdata(self.last_interp_out)
        self.line_interp.set_ydata(self.last_interp_sweep)

        self.ax_line.relim()
        self.ax_line.autoscale_view(True,True,True)

        self.aspect(self.ax_line, .3)

    def save(self):
        filename = os.path.join(self.path, self.filename)

        with open(filename+'.csv', 'w') as f:
            for s in ['span', 'center', 'numpts']:
                f.write('%s = %f, %f \n' %(s, float(getattr(self, s)[0]),float(getattr(self, s)[1])))
            for s in ['a','b','c']:
                f.write('plane.%s = %f\n' %(s, float(getattr(self.plane, s))))
            f.write('scanheight = %f\n' %self.scanheight)
            f.write('swap = %i\n' %self.swap)
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('starting temperature: %f' %self.temp_start)

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
        ##### MAY NOT WORK PROPERLY ANYMORE!!!
        #plt.figure()
        #self.plot_squid()
        self.fig.savefig(filename+'.pdf')

        #plt.figure()
        #self.plot_cap()
        #plt.savefig(filename+'_cap.pdf', bbox_inches='tight')

    def save_line(self, i, Vstart):
        filename = os.path.join(self.path, self.filename)

        with open(filename+'_lines.csv', 'a') as f:
            f.write('Line %i, starting at: ' %i)
            for v in Vstart():
                f.write(v)
            f.write('\n Vpiezo: ')
            for x in self.last_full_sweep:
                f.write(x)
            f.write('\n Vsquid: ')
            for x in self.last_full_out:
                f.write(x)

if __name__ == '__main__':
    'hey'
