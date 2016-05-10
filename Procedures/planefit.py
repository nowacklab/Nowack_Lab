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
        ## Initial touchdown
        start_pos = [self.center[0], self.center[1], 0] # center of plane
        self.nav.goto_seq(start_pos[0], start_pos[1], start_pos[2]) # go to center of plane
        self.td.do(planescan=False) # Will to initial touchdown at center of plane to (1) find the plane (2) make touchdown voltage near center of piezo's positive voltage range
        
        check_td = input('Does the initial touchdown look good? Enter \'quit\' to abort.')
        if check_td == 'quit':
            raise Exception('Terminated by user')
        
        self.piezos.check_lim({'x': self.X, 'y': self.Y}) # make sure we won't scan outside X, Y piezo ranges!
        
        ## Loop over points sampled from plane.
        for i in range(self.X.shape[0]): 
            for j in range(self.X.shape[1]):
                self.nav.goto_seq(self.X[i,j], self.Y[i,j], -self.piezos.Vmax['z']) #Retract Z, then move to (X,Y)
                self.td = touchdown2.Touchdown(self.piezos, self.atto, self.lockin, self.daq, self.cap_input) # new touchdown at this point
                self.Z[i,j] = self.td.do(planescan=True) # Do the touchdown. Planescan True prevents attocubes from moving and only does one touchdown
       
        self.nav.goto_seq(start_pos[0], start_pos[1], start_pos[2]) # return to center of plane
        self.plane(0, 0, True) # calculates plane. Calculates origin voltage too, but we won't use it.
        
    def plane(self, x, y, recal=False):
        X = self.X.flatten()
        Y = self.Y.flatten()
        Z = self.Z.flatten()
        if self.a == None or recal: #calculate plane from current X, Y data
            A = numpy.vstack([X, Y, numpy.ones(len(X))]).T
            self.a, self.b, self.c = lstsq(A, Z)[0]

        return self.a*x + self.b*y + self.c
        
    def plot():
        from mpl_toolkits.mplot3d import Axes3D
        import matplotlib.pyplot as plt
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        X = self.X
        Y = self.Y
        Z = self.Z

        ax.scatter(X, Y, Z)

        Zfit = self.plane(X,Y)
        ax.plot_surface(X,Y,Zfit,alpha=0.2, color = [0,1,0])
        xlabel('x')
        
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