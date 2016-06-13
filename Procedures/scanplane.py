import numpy
from numpy.linalg import lstsq
from . import navigation
import time
from scipy.interpolate import interp1d as interp
import matplotlib.pyplot as plt
from IPython import display
from numpy import ma 
        
class Scanplane():
    def __init__(self, instruments, span, center, numpts, plane, scanheight, sig_in, cap_in, swap=False):
        self.piezos = instruments['piezos']
        self.daq = instruments['daq']
        self.montana = instruments['montana']
        
        self.sig_in = sig_in
        self.daq.add_input(sig_in)
        
        self.cap_in = cap_in
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
                
        self.x = numpy.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = numpy.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = numpy.meshgrid(self.x, self.y)
        self.Z = self.plane.plane(self.X, self.Y) - self.scanheight
        
        self.V = numpy.array([[float('nan')]*self.X.shape[0]]*self.X.shape[1])
        self.C = numpy.array([[float('nan')]*self.X.shape[0]]*self.X.shape[1])

        self.fig = plt.figure(figsize=(14,10))

        self.swap = swap 
        if swap: # Will rotate scan 90 degrees? Not really tested. Got bugs if false. Keep it true for now.
            self.X = numpy.swapaxes(self.X, 0, 1)
            self.Y = numpy.swapaxes(self.Y, 0, 1)
            self.Z = numpy.swapaxes(self.Z, 0, 1)
            
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_scan'


        
    def do(self):
        tstart = time.time()
    
        for i in range(self.X.shape[0]): # make sure all points are not out of range of piezos
            self.nav.check_range(self.X[i][0], self.Y[i][0], self.Z[i][0])
    
        ## Loop over X values
        for i in range(self.X.shape[0]):
            end = self.X.shape[1]-1
            self.nav.goto(self.X[i][0], self.Y[i][0], self.Z[i][0]) # goes to beginning of scan
            
            Vstart = {'x': self.X[i][0], 'y': self.Y[i][0], 'z': self.Z[i][0]} 
            Vend = {'x': self.X[i][end], 'y': self.Y[i][end], 'z': self.Z[i][end]}
            
            out, V, t = self.piezos.sweep(Vstart, Vend) # sweep over Y
            
            interp_func = interp(out['y'], V[self.sig_in])
            self.V[i][:] = interp_func(self.Y[i][:]) # changes from actual output data to give desired number of points
            
            self.last_full_sweep = V[self.sig_in]
            
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
        
    def plot_SQUID(self):
        Vm = ma.masked_where(numpy.isnan(self.V),self.V) #hides data not yet collected

        plt.title('%s\nSQUID signal' %self.filename, fontsize=20)
        plt.pcolor(self.X, self.Y, Vm, cmap='RdBu', vmin=-abs(Vm).max(), vmax= abs(Vm).max())
        plt.xlabel(r'$X (V_{piezo})$', fontsize=20)
        plt.ylabel(r'$Y (V_{piezo})$', fontsize=20)
        cb = plt.colorbar()
        cb.set_label(label = 'Voltage from %s' %self.sig_in, fontsize=20)
        
    def plot_cap(self):
        Cm = ma.masked_where(numpy.isnan(self.C),self.C) #hides data not yet collected

        plt.title('%s\ncapacitance' %self.filename, fontsize=20)
        plt.pcolor(self.X, self.Y, Cm, cmap='RdBu')
        plt.xlabel(r'$X (V_{piezo})$', fontsize=20)
        plt.ylabel(r'$Y (V_{piezo})$', fontsize=20)
        cb = plt.colorbar()
        cb.set_label(label = 'Voltage from %s' %self.cap_in, fontsize=20)
        
    def plot_last_sweep(self):
        plt.title('last full line scan', fontsize=20)
        plt.plot(self.last_full_sweep, '.-')
        plt.xlabel('Y (a.u.)', fontsize=20)
        plt.ylabel('V', fontsize=20)
        
    def save(self):
        data_folder = 'C:\\Users\\Hemlock\\Dropbox (Nowack lab)\\TeamData\\Montana\\Scans\\'
        filename = data_folder + self.filename
      
        with open(filename+'.csv', 'w') as f:
            for s in ['span', 'center', 'numpts']:
                f.write('%s = %f, %f \n' %(s, float(getattr(self, s)[0]),float(getattr(self, s)[1])))
            for s in ['a','b','c']:
                f.write('plane.%s = %f\n' %(s, float(getattr(self.plane, s))))
            f.write('scanheight = %f\n' %self.scanheight)
            f.write('swap = %i\n' %self.swap)
            f.write('Montana info: \n'+self.montana.log()+'\n')

            f.write('X (V)\tY (V)\tV (V)\n')
            for i in range(self.X.shape[0]): 
                for j in range(self.X.shape[1]):
                    if self.V[i][j] != None:
                        f.write('%f' %self.X[i][j] + '\t' + '%f' %self.Y[i][j] + '\t' + '%f' %self.V[i][j] + '\n')
        
        plt.figure()
        self.plot_SQUID()
        plt.savefig(filename+'.pdf', bbox_inches='tight')

        plt.figure()
        self.plot_cap()
        plt.savefig(filename+'_cap.pdf', bbox_inches='tight')
        
if __name__ == '__main__':
    'hey'