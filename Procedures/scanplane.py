import numpy as np
from numpy.linalg import lstsq
from . import navigation
import time
from scipy.interpolate import interp1d as interp
import matplotlib.pyplot as plt
from IPython import display
from numpy import ma 
from ..Utilities import dummy
from ..Instruments import piezos, daq, montana
        
class Scanplane():
    def __init__(self, instruments=None, span=[100,100], center=[0,0], numpts=[50,50], plane=dummy.Dummy(planefit.Planefit), scanheight=5, sig_in=0, cap_in=1, swap=False):
        if instruments:
            self.piezos = instruments['piezos']
            self.daq = instruments['daq']
            self.montana = instruments['montana']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.daq = dummy.Dummy(nidaq.NIDAQ)
            self.montana = dummy.Dummy(montana.Montana)
        
        self.sig_in = 'ai%s' %sig_in
        self.daq.add_input(sig_in)
        
        self.cap_in = 'ai%s' %cap_in
        self.daq.add_input(cap_in)
        
        self.span = span
        self.center = center
        self.numpts = numpts
    
        self.plane = plane
        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? If not, enter \'quit.\'')
            if inp == 'quit':
                raise Exception('Terminated by user')
        self.scanheight = scanheight
        
        self.nav = navigation.Goto(self.piezos)
        self.start_pos = (0,0,0)
        # self.start_pos = (self.piezos.V['x'],self.piezos.V['y'],self.piezos.V['z']) # current position before scan
        # self.start_pos = (self.center[0], self.center[1], 0) # center of scan
                
        self.x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y)
        self.Z = self.plane.plane(self.X, self.Y) - self.scanheight
        
        self.V = np.array([[float('nan')]*self.X.shape[0]]*self.X.shape[1])
        self.C = np.array([[float('nan')]*self.X.shape[0]]*self.X.shape[1])

        self.fig = plt.figure(figsize=(14,10))

        self.swap = swap 
        if swap: # Will rotate scan 90 degrees? Not really tested. Got bugs if false. Keep it true for now.
            self.X = self.X.transpose()
            self.Y = self.Y.transpose()
            self.Z = self.Z.transpose()
            
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_scan'


        
    def do(self):
        self.setup_plots()
    
        tstart = time.time()
        self.temp_start = montana.temperature['platform']
    
        for i in range(self.X.shape[0]): # make sure all points are not out of range of piezos
            self.nav.check_range(self.X[i][0], self.Y[i][0], self.Z[i][0])
    
        ## Loop over X values
        for i in range(self.X.shape[0]):
            self.nav.goto(self.X[i][0], self.Y[i][0], self.Z[i][0]) # goes to beginning of scan
            
            Vstart = {'x': self.X[i][0], 'y': self.Y[i][0], 'z': self.Z[i][0]} 
            Vend = {'x': self.X[i][-1], 'y': self.Y[i][-1], 'z': self.Z[i][-1]}
            
            out, V, t = self.piezos.sweep(Vstart, Vend) # sweep over Y
            
            interp_func = interp(out['y'], V[self.sig_in])
            self.V[i][:] = interp_func(self.Y[i][:]) # changes from actual output data to give desired number of points
            
            self.last_full_out = out['y']
            self.last_full_sweep = V[self.sig_in]
            
            self.last_interp_out = self.Y[i][:]
            self.last_interp_sweep = self.V[i][:]
            
            # Do the same for capacitance
            interp_func = interp(out['y'], V[self.cap_in])
            self.C[i][:] = interp_func(self.Y[i][:])
                        
            self.plot()  
            
        self.nav.goto_seq(*self.start_pos) #Go back whence you came! *arg expands the tuple
        self.save()
        
        tend = time.time()
        print('Scan took %f minutes' %((tend-tstart)/60))
        return
        
    def plot(self):    
        plt.clf()
   
        ax1 = plt.subplot(121, aspect=1)
        self.plot_SQUID()
        
        ax2 = plt.subplot(222,aspect=1)
        self.plot_cap()
        
        ax3 = plt.subplot(224)
        self.plot_last_sweep()
        x0,x1 = ax3.get_xlim()
        y0,y1 = ax3.get_ylim()
        ax3.set_aspect((x1-x0)/(y1-y0)/3)
        
        display.display(plt.gcf())
        display.clear_output(wait=True)
        
    def setup_plots(self):
        """ TO TEST """
        self.fig = plt.figure()
        
        self.ax_squid = self.fig.add_subplot(121, aspect=1)
        self.setup_plot_squid()
        
        self.ax_cap = self.fig.add_subplot(222, aspect=1)
        self.setup_plot_cap()
        
        self.ax_line = self.fig.add_subplot(224)
        self.setup_plot_line()
                
    def setup_plot_squid(self):
        """ TO TEST """
        Vm = ma.masked_where(np.isnan(self.V),self.V) #hides data not yet collected

        plt.title('%s\nSQUID signal' %self.filename, fontsize=20)
        self.im_squid = self.ax_squid.imshow(Vm, cmap='RdBu', interpolation='none',aspect='auto', extent=[min(self.X), max(self.X), min(self.Y), max(self.Y)])
        
        plt.xlabel(r'$X (V_{piezo})$', fontsize=20)
        plt.ylabel(r'$Y (V_{piezo})$', fontsize=20)
        self.cb_squid = plt.colorbar(self.im_squid, ax=self.ax_squid)
        self.cb_squid.set_label(label = 'Voltage from %s' %self.sig_in, fontsize=20)
        self.cb_squid.formatter.set_powerlimits((-2,2))
        
    def plot_squid(self):
        """ TO TEST """
        Vm = ma.masked_where(np.isnan(self.V),self.V) #hides data not yet collected
        self.im_squid.set_array(Vm)
        
        self.cb_squid.set_clim(-abs(Vm).max(), abs(Vm).max())
        self.cb_squid.draw_all()
                
    def setup_plot_cap(self):
        """ TO TEST """
        Cm = ma.masked_where(np.isnan(self.C),self.C) #hides data not yet collected

        plt.title('%s\ncapacitance' %self.filename, fontsize=20)
        self.im_cap = self.ax_cap.imshow(Cm, cmap='afmhot', interpolation='none', aspect='auto', extent=[min(self.X), max(self.X), min(self.Y), max(self.Y)])
        
        plt.xlabel(r'$X (V_{piezo})$', fontsize=20)
        plt.ylabel(r'$Y (V_{piezo})$', fontsize=20)
        
        self.cb_cap = plt.colorbar(self.im_cap, ax=self.ax_cap)
        self.cb_cap.set_label(label = 'Voltage from %s' %self.cap_in, fontsize=20)
        self.cb_cap.formatter.set_powerlimits((-2,2))
        
    def plot_cap(self):
        """ TO TEST """
        Cm = ma.masked_where(np.isnan(self.C),self.C) #hides data not yet collected
        self.im_cap.set_array(Cm)
        
    def setup_plot_line(self):
        """ TO TEST """
        
        plt.title('last full line scan', fontsize=20)
        self.line_full, = plt.plot(self.last_full_out, self.last_full_sweep, '-.k') # commas only take first element of array? ANyway, it works.
        self.line_interp, = plt.plot(self.last_interp_out, self.last_interp_sweep, '.r', markersize=12) 
        plt.xlabel('Y (a.u.)', fontsize=20)
        plt.ylabel('V', fontsize=20)
        
    def plot_line(self):
        """ TO TEST """
        self.line_full.set_ydata(self.last_full_sweep)
        self.line_interp.set_ydata(self.last_interp_sweep)
        plt.draw()
        
    def save(self):
        home = os.path.expanduser("~")
        data_folder = os.path.join(home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'Scans')

        filename = data_folder + self.filename
      
        with open(filename+'.txt', 'w') as f:
            for s in ['span', 'center', 'numpts']:
                f.write('%s = %f, %f \n' %(s, float(getattr(self, s)[0]),float(getattr(self, s)[1])))
            for s in ['a','b','c']:
                f.write('plane.%s = %f\n' %(s, float(getattr(self.plane, s))))
            f.write('scanheight = %f\n' %self.scanheight)
            f.write('swap = %i\n' %self.swap)
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('starting temperature: %f' %self.temp_start)

            f.write('X (V),Y (V),V (V)\n')
            for i in range(self.X.shape[0]): 
                for j in range(self.X.shape[1]):
                    if self.V[i][j] != None:
                        f.write('%f' %self.X[i][j] + ',' + '%f' %self.Y[i][j] + ',' + '%f' %self.V[i][j] + '\n')
        ##### MAY NOT WORK PROPERLY ANYMORE!!!
        plt.figure()
        self.plot_SQUID()
        plt.savefig(filename+'.pdf', bbox_inches='tight')

        plt.figure()
        self.plot_cap()
        plt.savefig(filename+'_cap.pdf', bbox_inches='tight')
        
if __name__ == '__main__':
    'hey'