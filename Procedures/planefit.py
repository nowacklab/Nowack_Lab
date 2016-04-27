import numpy
from numpy.linalg import lstsq
import touchdown, navigation
        
class Planefit():
    def __init__(self, instruments, cap_input, span, center, numpts):
        self.x_piezo = instruments[0]
        self.y_piezo = instruments[1]
        self.z_piezo = instruments[2]
        self.atto = instruments[3]
        self.lockin = instruments[4]
        self.cap_input = cap_input
        
        self.span = span
        self.center = center
        self.numpts = numpts
        
        self.td = Touchdown(self.z_piezo, self.atto, self.lockin, self.cap_input)
        self.nav = Navigation(self.x_piezo, self.y_piezo, self.z_piezo)
        
        self.x = numpy.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = numpy.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])
        
        self.X, self.Y = numpy.meshgrid(self.x, self.y)
        self.Z = numpy.nan*self.X # makes array of zeros same size as grid
        
        self.a = None
        self.b = None
        self.c = None
        
    def do(self):
        start_pos = [getattr(self, '%s_piezo.V' %i) for i in ['x', 'y', 'z']]
        self.x_piezo.check_lim(self.X)
        self.y_piezo.check_lim(self.Y)
        for i in range(size(self.X, 0)):
            for j in range(size(self.X, 1)):
                self.nav.goto(self.X[i,j], self.Y[i,j], -40)
                self.Z[i,j] = self.td.do()
        self.nav.goto(start_pos[0], start_pos[1], start_pos[2])
        self.plane(0, 0, True) # calculates plane then returns origin z-value
        
    def plane(self, x, y, recal=False):
        if self.a == None or recal: #calculate plane from current X, Y data
            A = numpy.vstack([self.X, self.Y, numpy.ones(len(self.X))]).T
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