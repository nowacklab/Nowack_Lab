import numpy
from numpy.linalg import lstsq
from . import touchdown, navigation
import time
import matplotlib.pyplot as plt
        
class Planefit():
    def __init__(self, instruments, span, center, numpts, cap_input):
        self.instruments = instruments
        self.piezos = instruments['piezos']
        
        self.span = span
        self.center = center
        self.numpts = numpts
    
        self.cap_input = cap_input
        
        self.nav = navigation.Goto(self.piezos)
                
        self.x = numpy.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = numpy.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])
        
        self.X, self.Y = numpy.meshgrid(self.x, self.y)
        self.Z = numpy.nan*self.X # makes array of zeros same size as grid
        
        self.a = None
        self.b = None
        self.c = None
        
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_plane'

        
    def do(self):
        ## Initial touchdown
        start_pos = [self.center[0], self.center[1], 0] # center of plane
        self.nav.goto_seq(start_pos[0], start_pos[1], start_pos[2]) # go to center of plane
        td = touchdown.Touchdown(self.instruments, self.cap_input)
        td.do() # Will do initial touchdown at center of plane to (1) find the plane (2) make touchdown voltage near center of piezo's positive voltage range
        
        check_td = input('Does the initial touchdown look good? Enter \'quit\' to abort.')
        if check_td == 'quit':
            raise Exception('Terminated by user')
        
        self.piezos.check_lim({'x': self.X, 'y': self.Y}) # make sure we won't scan outside X, Y piezo ranges!
        
        ## Loop over points sampled from plane.
        for i in range(self.X.shape[0]): 
            for j in range(self.X.shape[1]):
                self.nav.goto_seq(self.X[i,j], self.Y[i,j], -self.piezos.Vmax['z']) #Retract Z, then move to (X,Y)
                print('X index: %i; Y index: %i' %(i, j))
                
                td = touchdown.Touchdown(self.instruments, self.cap_input, planescan=True) # new touchdown at this point
                self.Z[i,j] = td.do() # Do the touchdown. Planescan True prevents attocubes from moving and only does one touchdown
       
        self.nav.goto_seq(start_pos[0], start_pos[1], start_pos[2]) # return to center of plane
        self.plane(0, 0, True) # calculates plane. Calculates origin voltage too, but we won't use it.
        self.save()
        
    def plane(self, x, y, recal=False):
        X = self.X.flatten()
        Y = self.Y.flatten()
        Z = self.Z.flatten()
        if self.a == None or recal: #calculate plane from current X, Y data
            A = numpy.vstack([X, Y, numpy.ones(len(X))]).T
            self.a, self.b, self.c = lstsq(A, Z)[0]

        return self.a*x + self.b*y + self.c
        
    def plot(self):
        from mpl_toolkits.mplot3d import Axes3D
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        X = self.X
        Y = self.Y
        Z = self.Z

        ax.scatter(X, Y, Z)

        Zfit = self.plane(X,Y)
        ax.plot_surface(X,Y,Zfit,alpha=0.2, color = [0,1,0])
        plt.xlabel('x')
        plt.title(self.filename,fontsize=15)
        
    def save(self):
        data_folder = 'C:\\Users\\Hemlock\\Dropbox (Nowack lab)\\TeamData\\Montana\\Planes\\'
        filename = data_folder + self.filename
        
        with open(filename+'.txt', 'w') as f:
            for s in ['span', 'center', 'numpts']:
                f.write('%s = %f, %f \n' %(s, float(getattr(self, s)[0]),float(getattr(self, s)[1])))
            for s in ['a','b','c']:
                f.write('%s = %f\n' %(s, float(getattr(self, s))))
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('X (V)\tY (V)\tZ (V)\n')
            for i in range(self.X.shape[0]): 
                for j in range(self.X.shape[1]):
                    if self.Z[i][j] != None:
                        f.write('%f' %self.X[i][j] + '\t' + '%f' %self.Y[i][j] + '\t' + '%f' %self.Z[i][j] + '\n')
        
        self.plot()
        plt.savefig(filename+'.pdf', bbox_inches='tight')
        
    def update_c(self):
        old_c = self.c
        td = touchdown.Touchdown(self.instruments, self.cap_input)
        self.c = td.do()
        for x in [-self.piezos.Vmax['x'], self.piezos.Vmax['x']]:
            for y in [-self.piezos.Vmax['y'], self.piezos.Vmax['y']]:
                z_maxormin = self.plane(x,y)
                if z_maxormin > self.piezos.Vmax['z'] or z_maxormin < 0:
                    self.c = old_c
                    raise Exception('Plane now extends outside range of piezos! Move the attocubes and try again.')
        
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
    
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    ax.scatter(X, Y, Z)

    zz = planefit.plane(xx,yy)
    ax.plot_surface(xx, yy, zz, alpha=0.2, color=[0,1,0])
    plt.show()