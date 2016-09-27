import numpy as np
from numpy.linalg import lstsq
from . import touchdown, navigation
import time, os, glob
from datetime import datetime
import matplotlib.pyplot as plt
from ..Utilities import logging
from ..Instruments import piezos, montana
from IPython import display
from ..Utilities.utilities import reject_outliers_plane, fit_plane
from ..Utilities.save import Measurement, get_todays_data_path


class Planefit(Measurement):
    '''
    For fitting to the plane of the sample. Will do a series of touchdowns in a grid of size specified by numpts. Vz_max sets the maximum voltage the Z piezo will reach. If None, will use the absolute max safe voltage set in the Piezos class.
    '''
    instrument_list = ['piezos','montana']
    def __init__(self, instruments={}, cap_input=None, span=[400,400], center=[0,0], numpts=[4,4], Vz_max = None):
        super().__init__('plane')

        self.load_instruments(instruments)
        self.instruments = instruments

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

        self.a = np.nan
        self.b = np.nan
        self.c = np.nan

    def __getstate__(self):
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

    def calculate_plane(self, no_outliers=True):
        '''
        Calculates the plane parameters a, b, and c.
        z = ax + by + c
        '''
        ## Remove outliers
        if no_outliers:
            Z = reject_outliers_plane(self.Z)
        else:
            Z = self.Z

        self.a, self.b, self.c = fit_plane(self.X, self.Y, Z)


    def do(self, edges_only=False):
        '''
        Do the planefit.
        set edges_only to true, and will only do the outermost points of the plane.
        '''
        if not self.cap_input:
            raise Exception('Cap_input not set!')

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

        ## If only taking plane from edges, make masked array
        if edges_only:
            mask = np.full(self.X.shape, True)
            mask[0,:] = False
            mask[-1,:] = False
            mask[:,0] = False
            mask[:,-1] = False

            self.X = np.ma.masked_array(self.X, mask)
            self.Y = np.ma.masked_array(self.Y, mask)

        ## Loop over points sampled from plane.
        counter = 0
        for i in range(self.X.shape[0]):
            for j in range(self.X.shape[1]):
                if np.ma.is_masked(self.X[i,j]):
                    continue

                counter = counter + 1
                display.clear_output(wait=True)

                ## Go to location of next touchdown
                logging.log('Start moving to (%.2f, %.2f)...' %(self.X[i,j], self.Y[i,j]))
                self.piezos.V = {'x':self.X[i,j], 'y':self.Y[i,j], 'z': 0}
                logging.log('Done moving to (%.2f, %.2f).' %(self.X[i,j], self.Y[i,j]))

                td = touchdown.Touchdown(self.instruments, self.cap_input, Vz_max = self.Vz_max, planescan=True) # new touchdown at this point
                td.title = '(%i, %i). TD# %i' %(i,j, counter)

                self.Z[i,j] = td.do() # Do the touchdown, starting 200 V below the location of the surface at the center of the plane. Hopefully planes are not more tilted than this.

        if edges_only:
            self.Z = np.ma.masked_array(self.Z, mask) # to prepare it for lstsq

        self.piezos.V = 0
        self.calculate_plane()

        ## take the first slow touchdown as a more accurate center
        c_fit = self.c
        self.c = center_z_value - self.a*self.center[0] - self.b*self.center[1]
        self.Z -= (c_fit-self.c) # c was lowered by the correction, so we lower the plane.

        self.save()


    @staticmethod
    def load(json_file=None, instruments={}, unwanted_keys=[]):
        '''
        Plane load method.
        If no json_file specified, will load the last plane taken.
        Useful if you lose the object while scanning.
        '''
        if json_file is None:
            # finds the newest plane saved as json
            try:
                json_file =  max(glob.iglob(os.path.join(get_todays_data_path(),'*_plane.json')),
                                        key=os.path.getctime)
            except: # we must have taken one during the previous day's work
                folders = list(glob.iglob(os.path.join(get_todays_data_path(),'..','*')))
                # -2 should be the previous day (-1 is today)
                json_file =  max(glob.iglob(os.path.join(folders[-2],'*_plane.json')),
                                        key=os.path.getctime)

        unwanted_keys += Planefit.instrument_list
        obj = Measurement.fromjson(json_file, unwanted_keys)
        obj.load_instruments(instruments)
        obj.instruments = instruments

        if obj.cap_input is None:
            print('cap_input not loaded! Set this manually!!!')

        return obj


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
        logging.log('Plane saved. a=%.4f, b=%.4f, c=%.4f' %(self.a, self.b, self.c))

        self.tojson(get_todays_data_path(), self.filename)

        if savefig:
            self.plot()
            plt.savefig(os.path.join(get_todays_data_path(), self.filename+'.pdf'), bbox_inches='tight')


    def surface(self, x, y):
        '''
        Does an interpolation on the surface to give an array of z values
        for x, y points specified by arrays.
        '''
        from scipy.interpolate import interp2d
        f = interp2d(self.X[0,:],self.Y[:,0],self.Z)
        return f(x,y)


    def update_c(self):
        '''
        Does a single touchdown to find the plane again (at Vx=Vy=0).
        Do this after moving the attocubes.
        '''
        super().__init__('plane')

        old_c = self.c
        td = touchdown.Touchdown(self.instruments, self.cap_input, Vz_max = self.Vz_max)
        self.c = td.do()
        for x in [-self.piezos.x.Vmax, self.piezos.x.Vmax]:
            for y in [-self.piezos.y.Vmax, self.piezos.y.Vmax]:
                z_maxormin = self.plane(x,y)
                if z_maxormin > self.piezos.z.Vmax or z_maxormin < 0:
                    self.c = old_c
                    raise Exception('Plane now extends outside range of piezos! Move the attocubes and try again.')
        self.Z -= (old_c-self.c) # for example, if c decrased, then we want to subtract a positive number from the plane
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
