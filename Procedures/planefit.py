import numpy as np
from numpy.linalg import lstsq
from . import touchdown, navigation
import time, os, glob
from datetime import datetime
import matplotlib.pyplot as plt
from ..Utilities import dummy
from ..Instruments import piezos, montana
from IPython import display
from ..Utilities.utilities import reject_outliers_quick
from ..Utilities.save import Measurement, get_todays_data_path

_home = os.path.expanduser("~")
DATA_FOLDER = get_todays_data_path()

class Planefit(Measurement):
    '''
    For fitting to the plane of the sample. Will do a series of touchdowns in a grid of size specified by numpts. Vz_max sets the maximum voltage the Z piezo will reach. If None, will use the absolute max safe voltage set in the Piezos class.
    '''
    def __init__(self, instruments=None, cap_input=None, span=[400,400], center=[0,0], numpts=[4,4], Vz_max = None):
        if instruments:
            self.instruments = instruments
            self.piezos = instruments['piezos']
            self.montana = instruments['montana']
        else:
            self.instruments = None
            self.piezos = None
            self.montana = None
            print('Instruments not loaded... can only plot!')

        self.span = span
        self.center = center
        self.numpts = numpts

        if Vz_max == None:
            try:
                self.Vz_max = self.piezos.z.Vmax
            except:
                self.Vz_max = None # Will reach here if dummy piezos are used, unfortunately.
        else:
            self.Vz_max = Vz_max

        self.cap_input = cap_input

        self.x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y)
        self.Z = np.nan*self.X # makes array of nans same size as grid

        self.a = None
        self.b = None
        self.c = None

        self.filename = ''

    def __getstate__(self):
        super().__getstate__() # from Measurement superclass,
                               # need this in every getstate to get save_dict
        self.save_dict.update({"timestamp": self.timestamp,
                          "a": self.a,
                          "b": self.b,
                          "c": self.c,
                          "span": self.span,
                          "center": self.center,
                          "numpts": self.numpts,
                          "piezos": self.piezos,
                          "montana": self.montana,
                          "cap_input": self.cap_input,
                          "Vz_max": self.Vz_max,
                          "X": self.X,
                          "Y": self.Y,
                          "Z": self.Z
                      })
        return self.save_dict


    def __setstate__(self, state):
        state.pop('piezos')
        state.pop('montana')
        self.__dict__.update(state)

    def calculate_plane(self):
        '''
        Calculates the plane parameters a, b, and c.
        z = ax + by + c
        '''
        X = self.X.flatten()
        Y = self.Y.flatten()
        Z = reject_outliers_quick(self.Z)
        Z = Z.flatten()
        A = np.vstack([X, Y, np.ones(len(X))]).T
        self.a, self.b, self.c = lstsq(A, Z)[0]


    def do(self):
        if not self.cap_input:
            raise Exception('Cap_input not set!')

        super().make_timestamp_and_filename('plane')

        self.piezos.x.check_lim(self.X)
        self.piezos.y.check_lim(self.Y) # make sure we won't scan outside X, Y piezo ranges!

        ## Initial touchdown
        print('Sweeping z piezo down...')
        self.piezos.V = {'x': self.center[0], 'y':self.center[1], 'z':-self.Vz_max}
        print('...done.')
        td = touchdown.Touchdown(self.instruments, self.cap_input, Vz_max = self.Vz_max)
        center_z_value = td.do() # Will do initial touchdown at center of plane to (1) find the plane (2) make touchdown voltage near center of piezo's positive voltage range

        check_td = input('Does the initial touchdown look good? Enter \'q\' to abort.')
        if check_td == 'q':
            raise Exception('Terminated by user')

        ## Loop over points sampled from plane.
        counter = 0
        for i in range(self.X.shape[0]):
            for j in range(self.X.shape[1]):
                counter = counter + 1
                display.clear_output(wait=True)

                ## Go to location of next touchdown
                print('Moving to next location...')
                self.piezos.V = {'x':self.X[i,j], 'y':self.Y[i,j], 'z': 0}
                print('...done.')

                td = touchdown.Touchdown(self.instruments, self.cap_input, Vz_max = self.Vz_max, planescan=True) # new touchdown at this point
                td.title = '(%i, %i). TD# %i' %(i,j, counter)

                self.Z[i,j] = td.do() # Do the touchdown. Planescan True prevents attocubes from moving and only does one touchdown

        self.piezos.V = 0
        self.calculate_plane()
        self.c = center_z_value # take the first slow touchdown as a more accurate center
        self.save()


    @staticmethod
    def load(instruments=None, json_file=None):
        '''
        Load method. If no json_file specified, will load the last plane taken.
        Useful if you lose the object while scanning.
        '''
        if json_file is None:
            # finds the newest plane saved as json
            try:
                json_file =  max(glob.iglob(os.path.join(DATA_FOLDER,'*_plane.json')),
                                        key=os.path.getctime)
            except: # we must have taken one during the previous day's work
                folders = list(glob.iglob(os.path.join(DATA_FOLDER,'..','*')))
                # -2 should be the previous day (-1 is today)
                json_file =  max(glob.iglob(os.path.join(folders[-2],'*_plane.json')),
                                        key=os.path.getctime)

        plane = Measurement.load(json_file)

        if plane.cap_input is None:
            print('cap_input not loaded! Set this manually!!!')

        if instruments is None:
            print('Didn\'t load instruments')
        else:
            plane.instruments = instruments
            plane.piezos = instruments['piezos']
            plane.montana = instruments['montana']

        return plane


    def plane(self, x, y, recal=False):
        '''
        Given points x and y, calculates a point z on the plane.
        '''
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


    def save(self, savefig=True):
        '''
        Saves the planefit object to json in .../TeamData/Montana/Planes/
        Also saves the figure as a pdf, if wanted.
        '''

        self.tojson(DATA_FOLDER, self.filename)

        if savefig:
            self.plot()
            plt.savefig(os.path.join(DATA_FOLDER, self.filename+'.pdf'), bbox_inches='tight')


    def update_c(self):
        '''
        Does a single touchdown to find the plane again (at Vx=Vy=0).
        Do this after moving the attocubes.
        '''
        super().make_timestamp_and_filename('plane')

        old_c = self.c
        td = touchdown.Touchdown(self.instruments, self.cap_input, Vz_max = self.Vz_max)
        self.c = td.do()
        for x in [-self.piezos.x.Vmax, self.piezos.x.Vmax]:
            for y in [-self.piezos.y.Vmax, self.piezos.y.Vmax]:
                z_maxormin = self.plane(x,y)
                if z_maxormin > self.piezos.z.Vmax or z_maxormin < 0:
                    self.c = old_c
                    raise Exception('Plane now extends outside range of piezos! Move the attocubes and try again.')
        self.save(savefig=False)


if __name__ == '__main__':
    """ just testing fitting algorithm - pretty sure this is way out of date"""
    import random
    from mpl_toolkits.mplot3d import Axes3D

    def gauss(X, a):
        random.seed(random.random())
        r = [(random.random()+1/2+x) for x in X]
        return np.exp(-a*(r-X)**2)

    xx, yy = np.meshgrid(np.linspace(0,10,10), np.linspace(0,10,10))
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
