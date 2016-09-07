import numpy
from numpy.linalg import lstsq
from . import touchdown, navigation
import time, os, glob
import matplotlib.pyplot as plt
from ..Utilities import dummy
from ..Instruments import piezos, montana
from IPython import display
from .save import Measurement

class Planefit(Measurement):
    '''
    For fitting to the plane of the sample. Will do a series of touchdowns in a grid of size specified by numpts. Vz_max sets the maximum voltage the Z piezo will reach. If None, will use the absolute max safe voltage set in the Piezos class.
    '''
    def __init__(self, instruments=None, span=[400,400], center=[0,0], numpts=[4,4], Vz_max = None, cap_input=0):
        self.instruments = instruments
        if instruments:
            self.piezos = instruments['piezos']
            self.montana = instruments['montana']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.montana = dummy.Dummy(montana.Montana)

        self.span = span
        self.center = center
        self.numpts = numpts

        if Vz_max == None:
            try:
                self.Vz_max = self.piezos.Vmax['z']
            except:
                self.Vz_max = None # Will reach here if dummy piezos are used, unfortunately.
        else:
            self.Vz_max = Vz_max

        self.cap_input = cap_input

        self.x = numpy.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = numpy.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = numpy.meshgrid(self.x, self.y)
        self.Z = numpy.nan*self.X # makes array of zeros same size as grid

        self.a = None
        self.b = None
        self.c = None

        self.filename=''

    def __getstate__(self):
        self.save_dict = {"timestamp": timestamp,
                          "a": self.a,
                          "b": self.b,
                          "c": self.c,
                          "span": self.span,
                          "center": self.center,
                          "numpts": self.numpts,
                          "piezos": self.peizos,
                          "montnana": self.montana}
        return self.save_dict
                          
    def do(self):
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_plane'
        self.timestamp = time.strftime("%Y-%m-%d @%I:%M%:%S%p")
        
        self.piezos.check_lim({'x':self.X, 'y':self.Y}) # make sure we won't scan outside X, Y piezo ranges!

        ## Initial touchdown
        print('Sweeping z piezo down...')
        self.piezos.V = {'x': self.center[0], 'y':self.center[1], 'z':-self.Vz_max}
        print('...done.')
        td = touchdown.Touchdown(self.instruments, self.cap_input, Vz_max = self.Vz_max)
        td.do() # Will do initial touchdown at center of plane to (1) find the plane (2) make touchdown voltage near center of piezo's positive voltage range

        check_td = input('Does the initial touchdown look good? Enter \'quit\' to abort.')
        if check_td == 'quit':
            raise Exception('Terminated by user')

        ## Loop over points sampled from plane.
        counter = 0
        for i in range(self.X.shape[0]):
            for j in range(self.X.shape[1]):
                counter = counter + 1
                display.clear_output(wait=True)

                ## Go to location of next touchdown
                print('Moving to next location...')
                self.piezos.V = {'x':self.X[i,j], 'y':self.Y[i,j], 'z': -self.Vz_max}
                print('...done.')

                td = touchdown.Touchdown(self.instruments, self.cap_input, Vz_max = self.Vz_max, planescan=True) # new touchdown at this point
                td.title = '(%i, %i). TD# %i' %(i,j, counter)

                self.Z[i,j] = td.do() # Do the touchdown. Planescan True prevents attocubes from moving and only does one touchdown

        self.piezos.V = 0
        self.plane(0, 0, True) # calculates plane
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
        home = os.path.expanduser("~")
        data_folder = os.path.join(home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'Planes')
        filename = os.path.join(data_folder, self.filename)

        with open(filename+'.csv', 'w') as f:
            for s in ['span', 'center', 'numpts']:
                f.write('%s = %f, %f \n' %(s, float(getattr(self, s)[0]),float(getattr(self, s)[1])))
            for s in ['a','b','c']:
                f.write('%s = %f\n' %(s, float(getattr(self, s))))
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('X (V),Y (V),Z (V)\n')
            for i in range(self.X.shape[0]):
                for j in range(self.X.shape[1]):
                    if self.Z[i][j] != None:
                        f.write('%f' %self.X[i][j] + ',' + '%f' %self.Y[i][j] + ',' + '%f' %self.Z[i][j] + '\n')

        self.plot()
        plt.savefig(filename+'.pdf', bbox_inches='tight')

    def update_c(self):
        old_c = self.c
        td = touchdown.Touchdown(self.instruments, self.cap_input, Vz_max = self.Vz_max)
        self.c = td.do()
        for x in [-self.piezos.Vmax['x'], self.piezos.Vmax['x']]:
            for y in [-self.piezos.Vmax['y'], self.piezos.Vmax['y']]:
                z_maxormin = self.plane(x,y)
                if z_maxormin > self.piezos.Vmax['z'] or z_maxormin < 0:
                    self.c = old_c
                    raise Exception('Plane now extends outside range of piezos! Move the attocubes and try again.')


def load_last():
    plane = Planefit(None)

    home = os.path.expanduser("~")
    data_folder = os.path.join(home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'Planes')
    newest_plane =  max(glob.iglob(os.path.join(data_folder,'*.[ct][sx][vt]')), key=os.path.getctime) # finds the newest plane saved as a csv or txt
    with open(newest_plane, 'r') as f:
        for i, line in enumerate(f): # loop through lines
            if i in (3,4,5): # these lines contain the plane information
                exec('plane.'+line) # e.g., plane.c = 97.43
            elif i == 6: # don't care about the rest of the file
                break

    return plane

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
