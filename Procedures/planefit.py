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
    _chan_labels = ['daq']
    instrument_list = ['piezos','montana']

    a = np.nan
    b = np.nan
    c = np.nan
    _append = 'plane'

    def __init__(self, instruments={}, span=[400,400], center=[0,0], numpts=[4,4], Vz_max = None):
        super().__init__(self._append)

        self._load_instruments(instruments)
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

        self.x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y)
        self.Z = np.nan*self.X # makes array of nans same size as grid


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

        self.piezos.x.check_lim(self.X)
        self.piezos.y.check_lim(self.Y) # make sure we won't scan outside X, Y piezo ranges!

        ## Initial touchdown
        print('Sweeping z piezo down...')
        self.piezos.V = {'x': self.center[0], 'y':self.center[1], 'z':-self.Vz_max}
        print('...done.')
        td = touchdown.Touchdown(self.instruments, Vz_max = self.Vz_max)
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

                td = touchdown.Touchdown(self.instruments, Vz_max = self.Vz_max, planescan=True) # new touchdown at this point
                td.title = '(%i, %i). TD# %i' %(i,j, counter)

                self.Z[i,j] = td.do() # Do the touchdown, starting 200 V below the location of the surface at the center of the plane. Hopefully planes are not more tilted than this.

                self.piezos.V = 0 # return to zero between points

        if edges_only:
            self.Z = np.ma.masked_array(self.Z, mask) # to prepare it for lstsq

        self.piezos.V = 0
        self.calculate_plane()

        ## take the first slow touchdown as a more accurate center
        c_fit = self.c
        self.c = center_z_value - self.a*self.center[0] - self.b*self.center[1]
        self.Z -= (c_fit-self.c) # c was lowered by the correction, so we lower the plane.

        self.save()


    @classmethod
    def load(cls, json_file=None, instruments={}, unwanted_keys=[]):
        '''
        Plane load method.
        If no json_file specified, will load the last plane taken.
        Useful if you lose the object while scanning.
        '''
        unwanted_keys.append('preamp')
        obj = super(Planefit, cls).load(json_file, instruments, unwanted_keys)
        obj.instruments = instruments

        return obj


    def plane(self, x, y, recal=False):
        '''
        Given points x and y, calculates a point z on the plane.
        '''
        return self.a*x + self.b*y + self.c


    def plot(self):
        super().plot()

        ax.scatter(self.X, self.Y, self.Z)

        Zfit = self.plane(self.X, self.Y)
        self.ax.plot_surface(self.X, self.Y, Zfit,alpha=0.2, color = [0,1,0])


    def save(self, savefig=True):
        '''
        Saves the planefit object to json.
        Also saves the figure as a pdf, if wanted.
        '''
        logging.log('Plane saved. a=%.4f, b=%.4f, c=%.4f' %(self.a, self.b, self.c))

        self._save(get_todays_data_path(), self.filename)

        if savefig and hasattr(self, 'fig'):
            self.fig.savefig(os.path.join(get_todays_data_path(), self.filename+'.pdf'), bbox_inches='tight')


    def setup_plots(self):
        from mpl_toolkits.mplot3d import Axes3D
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')

        self.ax.set_xlabel('x')
        self.ax.set_ylabel('y')
        self.ax.set_zlabel('z')
        plt.title(self.filename,fontsize=15)


    def surface(self, x, y):
        '''
        Does an interpolation on the surface to give an array of z values
        for x, y points specified by arrays.
        '''
        from scipy.interpolate import interp2d
        f = interp2d(self.X[0,:],self.Y[:,0],self.Z)
        return f(x,y)


    def update_c(self, Vx=0, Vy=0, start=None):
        '''
        Does a single touchdown to find the plane again (at a given (Vx, Vy) point).
        Do this after moving the attocubes.
        '''
        super().__init__('plane')

        old_c = self.c
        self.piezos.V = {'x': Vx, 'y': Vy, 'z': 0}
        td = touchdown.Touchdown(self.instruments, Vz_max = self.Vz_max)
        center_z_value = td.do(start=start)
        self.c = center_z_value - self.a*Vx - self.b*Vy

        for x in [-self.piezos.x.Vmax, self.piezos.x.Vmax]:
            for y in [-self.piezos.y.Vmax, self.piezos.y.Vmax]:
                z_maxormin = self.plane(x,y)
                if z_maxormin > self.piezos.z.Vmax or z_maxormin < 0:
                    self.c = old_c
                    raise Exception('Plane now extends outside range of piezos! Move the attocubes and try again.')
        self.Z -= (old_c-self.c) # for example, if c decreased, then we want to subtract a positive number from the plane
        self.save(savefig=False)
