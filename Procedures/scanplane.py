import numpy
from numpy.linalg import lstsq
import navigation
import time
        
class Scanplane():
    def __init__(self, instruments, span, center, numpts, plane, scanheight):
        self.x_piezo = instruments[0]
        self.y_piezo = instruments[1]
        self.z_piezo = instruments[2]
        self.atto = instruments[3]
        self.lockin = instruments[4]
        self.daq = instruments[5]
        
        self.span = span
        self.center = center
        self.numpts = numpts
    
        self.plane = plane
        self.scanheight = scanheight
        
        self.nav = navigation.Goto(self.x_piezo, self.y_piezo, self.z_piezo)
                
        self.x = numpy.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = numpy.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])
        
        self.X, self.Y = numpy.meshgrid(self.x, self.y)
        self.Z = self.plane.plane(self.X, self.Y) - self.scanheight
        
    def do(self):
        for i in range(self.X.shape[0]):
            self.nav.goto(self.X[i][0], self.Y[i][0], self.Z[i][0]) # goes to starting position
            # next need to sweep all piezos at once, can't use piezo sweep function anymore, need send/receive
            # maybe just make piezos all one object
            
        ### EVERYTHING BELOW IS COPYPASTA'D FROM PLANEFIT
        
        start_pos = [self.center[0], self.center[1], 0]
        self.nav.goto(start_pos[0], start_pos[1], start_pos[2])
        self.td.do(planescan=False) # to position z attocube so that V_td is near the center of sweep range at the center of the scan
        input('good?')
        self.x_piezo.check_lim(self.X)
        self.y_piezo.check_lim(self.Y)
        for i in range(self.X.shape[0]): #SWAPPED INDICES 0 1 i j
            for j in range(self.X.shape[1]):
                self.nav.goto(self.X[i,j], self.Y[i,j], -40)
                self.td = touchdown.Touchdown(self.z_piezo, self.atto, self.lockin, self.daq, self.cap_input) #refresh touchdown object
                self.Z[i,j] = self.td.do(planescan=True)
        self.nav.goto(start_pos[0], start_pos[1], start_pos[2])
        self.plane(0, 0, True) # calculates plane then returns origin z-value
        
        
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