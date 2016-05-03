import numpy
from numpy.linalg import lstsq
import touchdown2, navigation
import time
        
class Planefit():
    def __init__(self, instruments, span, center, numpts, cap_input):
        self.piezos = instruments[0]
        self.atto = instruments[1]
        self.lockin = instruments[2]
        self.daq = instruments[3]
        
        self.span = span
        self.center = center
        self.numpts = numpts
    
        self.cap_input = cap_input
        
        self.td = touchdown2.Touchdown(self.piezos, self.atto, self.lockin, self.daq, self.cap_input)
        self.nav = navigation.Goto(self.piezos)
                
        self.x = numpy.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = numpy.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])
        
        self.X, self.Y = numpy.meshgrid(self.x, self.y)
        self.Z = numpy.nan*self.X # makes array of zeros same size as grid
        
        self.a = None
        self.b = None
        self.c = None
        
    def do(self):
        start_pos = [self.center[0], self.center[1], 0]
        self.nav.goto_seq(start_pos[0], start_pos[1], start_pos[2])
        self.td.do(planescan=False) # to position z attocube so that V_td is near the center of sweep range at the center of the scan
        input('good?')
        self.piezos.check_lim({'x': self.X, 'y': self.Y})
        for i in range(self.X.shape[0]): #SWAPPED INDICES 0 1 i j
            for j in range(self.X.shape[1]):
                self.nav.goto_seq(self.X[i,j], self.Y[i,j], -40)
                self.td = touchdown2.Touchdown(self.piezos, self.atto, self.lockin, self.daq, self.cap_input) #refresh touchdown object
                self.Z[i,j] = self.td.do(planescan=True)
        self.nav.goto_seq(start_pos[0], start_pos[1], start_pos[2])
        self.plane(0, 0, True) # calculates plane then returns origin z-value
        
    def plane(self, x, y, recal=False):
        X = self.X.flatten()
        Y = self.Y.flatten()
        Z = self.Z.flatten()
        if self.a == None or recal: #calculate plane from current X, Y data
            A = numpy.vstack([X, Y, numpy.ones(len(X))]).T
            self.a, self.b, self.c = lstsq(A, Z)[0]

        return self.a*x + self.b*y + self.c
        
if __name__ == '__main__':
    """ just testing fitting algorithm """
    import random
    from mpl_toolkits.mplot3d import Axes3D

    def gauss(X, a):
        random.seed(random.random())
        r = [(random.random()+1/2+x) for x in X]
        return numpy.exp(-a*(r-X)**2)

    xx, yy = numpy.meshgrid(numpy.linspace(0,10,10), numpy.linspace(0,10,10))
    X = xx.flatten()
    Y = yy.flatten()

    Z = X + 2*Y + 3

    Z = Z*gauss(Z,1)
    
    planefit = Planefit(X, Y, Z)
    
    import matplotlib.pyplot as plt
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    ax.scatter(X, Y, Z)

    zz = planefit.plane(xx,yy)
    ax.plot_surface(xx, yy, zz, alpha=0.2, color=[0,1,0])
    plt.show()