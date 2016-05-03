import numpy
from numpy.linalg import lstsq
import navigation
import time
from scipy.interpolate import interp1d as interp
        
class Scanplane():
    def __init__(self, instruments, span, center, numpts, plane, scanheight, chan_in, swap=False):
        self.piezos = instruments[0]
        self.atto = instruments[1]
        self.lockin = instruments[2]
        self.daq = instruments[3]
        
        self.chan_in = chan_in
        if chan_in not in self.daq.inputs_to_monitor:
            self.daq.inputs_to_monitor.append(chan_in)
        
        self.span = span
        self.center = center
        self.numpts = numpts
    
        self.plane = plane
        self.scanheight = scanheight
        
        self.nav = navigation.Goto(self.piezos)
                
        self.x = numpy.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = numpy.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])
        
        self.start_pos = [self.center[0], self.center[1], 0]

        self.X, self.Y = numpy.meshgrid(self.x, self.y)
        self.Z = self.plane.plane(self.X, self.Y) - self.scanheight
        
        self.V = numpy.array([[None]*self.X.shape[0]]*self.X.shape[1])
        
        if swap:
            self.X = numpy.swapaxes(self.X, 0, 1)
            self.Y = numpy.swapaxes(self.Y, 0, 1)
            self.Z = numpy.swapaxes(self.Z, 0, 1)

        
    def do(self):
        for i in range(self.X.shape[0]):
            end = self.X.shape[1]-1
            self.nav.goto(self.X[i][0], self.Y[i][0], self.Z[i][0]) # goes to starting position
            
            Vstart = {'x': self.X[i][0], 'y': self.Y[i][0], 'z': self.Z[i][0]}
            Vend = {'x': self.X[i][end], 'y': self.Y[i][end], 'z': self.Z[i][end]}
            
            out, V, time = self.piezos.sweep(Vstart, Vend)
            
            interp_func = interp(out['y'], V[self.chan_in])
            V = interp_func(self.Y[i][:]) # changes from actual output data to give desired number of points
            self.V[i][:] = V
            
        self.nav.goto_seq(self.start_pos[0], self.start_pos[1], self.start_pos[2]) 
if __name__ == '__main__':
    'hey'