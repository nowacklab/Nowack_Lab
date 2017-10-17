import numpy as np
from numpy.linalg import lstsq
from .touchdown import Touchdown
import time
import os
import glob
from datetime import datetime
import matplotlib.pyplot as plt
from ..Utilities import logging
from ..Instruments import piezos, montana
from IPython import display
from ..Utilities.utilities import reject_outliers_plane, fit_plane
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict


class Planefit(Measurement):
    '''
    Take touchdowns in a grid to define a plane.
    '''
    instrument_list = ['piezos', 'montana']

    a = np.nan
    b = np.nan
    c = np.nan

    def __init__(self, instruments={}, span=[400, 400], center=[0, 0],
                 numpts=[4, 4], Vz_max=None):
        '''
        Take touchdowns in a grid to determine the slope of the sample
        surface.

        Args:
        instruments (dict) -- must contain the instruments required for
        the touchdown.

        span (list): Specifices the size [X span, Y span] of the plane
        in voltage applied to the X and Y peizos.

        center (list): Specifies the center of the plane
        [X center, Y center] in voltage applied to the X and Y peizos.

        numpts (list): The numper of touchdowns to take on each axis
        [X number, Y number].

        Vz_max (float):Maximum voltage that can be applied to the Zpiezo.
        If None then the the max voltage for the piezo is used.

        Required instruments:
        daq, lockin_cap, attocubes, piezos, montana

        Required daq inputs:
        'cap', 'capx', 'capy', 'theta'

        Required daq outputs:
        'x', 'y', 'z'

        Examples:
        plane = Planefit(instruments, span=[100, 200], center=[50, 50]
        plane.run(edges_only = True)
        '''
        super().__init__(instruments=instruments)

        self.instruments = instruments

        self.span = span
        self.center = center
        self.numpts = numpts

        if Vz_max == None:
            try:
                self.Vz_max = self.piezos.z.Vmax
            except:
                # Will reach here if dummy piezos are used, unfortunately.
                self.Vz_max = None
        else:
            self.Vz_max = Vz_max

        self.x = np.linspace(center[0] - span[0] / 2,
                             center[0] + span[0] / 2, numpts[0])
        self.y = np.linspace(center[1] - span[1] / 2,
                             center[1] + span[1] / 2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y)
        self.Z = np.nan * self.X  # makes array of nans same size as grid

    def calculate_plane(self, no_outliers=True):
        '''
        Calculates the plane parameters a, b, and c.
        z = ax + by + c
        '''
        # Remove outliers
        if no_outliers:
            Z = reject_outliers_plane(self.Z)
        else:
            Z = self.Z

        self.a, self.b, self.c = fit_plane(self.X, self.Y, Z)

    def do(self, edges_only=False):
        '''
        Do the planefit.

        Args:
        edges_only (bool): If True touchdowns are taken only around the
        edges of the grid.
        '''
        # make sure we won't scan outside X, Y piezo ranges!
        self.piezos.x.check_lim(self.X)
        self.piezos.y.check_lim(self.Y)

        # Initial touchdown at center of plane
        self.piezos.V = {'x': self.center[0],
                         'y': self.center[1], 'z': -self.Vz_max}
        td = Touchdown(self.instruments, Vz_max=self.Vz_max, planescan=True)
        td.run()
        # If the initial touchdown generates a poor fit, try again
        n = 0
        while td.flagged and n < 5:
            td = Touchdown(self.instruments, Vz_max=self.Vz_max, planescan=True)
            td.run()
            n = n + 1

        if td.flagged:
            raise Exception("Can't fit capacitance signal.")
        else:
            center_z_value = td.Vtd

        # If only taking plane from edges, make masked array
        if edges_only:
            mask = np.full(self.X.shape, True)
            mask[0, :] = False
            mask[-1, :] = False
            mask[:, 0] = False
            mask[:, -1] = False

            self.X = np.ma.masked_array(self.X, mask)
            self.Y = np.ma.masked_array(self.Y, mask)

        # Loop over points sampled from plane.
        counter = 0
        for i in range(self.X.shape[0]):
            for j in range(self.X.shape[1]):
                # If this point is masked, like in edges only, skip it
                if np.ma.is_masked(self.X[i, j]):
                    continue

                counter = counter + 1
                display.clear_output(wait=True)

                # Go to location of next touchdown
                self.piezos.V = {'x': self.X[i, j],
                                 'y': self.Y[i, j],
                                 'z': 0}

                # New touchdown at this point
                # Take touchdowns until the fitting algorithm gives a
                # good result, up to 5 touchdowns
                td = Touchdown(self.instruments,
                               Vz_max=self.Vz_max, planescan=True)
                td.title = '(%i, %i). TD# %i' % (i, j, counter)
                td.run()
                plt.close(td.fig)
                n = 0
                while td.flagged is True and n < 5:
                    print("Redo")
                    td = Touchdown(self.instruments,
                                   Vz_max = self.Vz_max, planescan=True)
                    td.title = '(%i, %i). TD# %i' % (i, j, counter)
                    td.run()
                    n = i + 1
                    plt.close(td.fig)
                # Record the touchdown voltage and update the gridplot
                self.Z[i, j] = td.Vtd
                td.gridplot(self.axes[-(i+1),j])
                self.fig.canvas.draw()

                # Return to zero between points.
                self.piezos.V = 0

        if edges_only:
            # to prepare it for lstsq
            self.Z = np.ma.masked_array(self.Z, mask)

        self.piezos.V = 0
        self.calculate_plane()

        # take the first slow touchdown as a more accurate center
        c_fit = self.c
        self.c = center_z_value - self.a * \
            self.center[0] - self.b * self.center[1]
        # c was lowered by the correction, so we lower the plane.
        self.Z -= (c_fit - self.c)

        self.plot()
        self.axes = list(self.axes.flatten())

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
        return self.a * x + self.b * y + self.c


    def colorplot(self):
        fig, ax = plt.subplots(figsize=(6,6))
        im = ax.matshow(self.Z, origin="lower")
        ax.xaxis.set_ticks_position("bottom")
        # Label the axes in voltage applied to piezos
        ax.set_xticks([0,1,2,3])
        ax.set_yticks([0,1,2,3])
        ax.set_xticklabels(['{:.0f}'.format(x) for x in self.X[0,:]])
        ax.set_yticklabels(['{:.0f}'.format(y) for y in self.Y[:,0]])
        ax.xaxis.set_ticks_position("both")
        ax.set_xlabel("X Position (V)")
        ax.set_ylabel("Y Position (V)")
        plt.tight_layout()
        return fig, ax

    def save(self, savefig=True):
        '''
        Saves the planefit object to json.
        Also saves the figure as a pdf, if wanted.
        '''
        logging.log('Plane saved. a=%.4f, b=%.4f, c=%.4f' %
                    (self.a, self.b, self.c))

        self._save(self.filename, savefig)

    def setup_plots(self):
        numX, numY = self.numpts
        self.fig = plt.figure(figsize=(numX*2,numY*2))
        axes = []
        for i in range(numX*numY):
            ax = self.fig.add_subplot(numX, numY, i+1)
            ax.set_xticks([])
            ax.set_yticks([])
            axes.append(ax)
        self.fig.subplots_adjust(wspace=0, hspace=0)
        self.axes = np.reshape(axes, self.numpts)

    def surface(self, x, y):
        '''
        Does an interpolation on the surface to give an array of z values
        for x, y points specified by arrays.
        '''
        from scipy.interpolate import interp2d
        f = interp2d(self.X[0, :], self.Y[:, 0], self.Z)
        return f(x, y)

    def update_c(self, Vx=0, Vy=0, start=None, move_attocubes=False):
        '''
        Does a single touchdown to update the offset of the plane.

        After the touchdown the corners of thep plane are checked
        to see if any of the voltages within the X,Y scanrange
        exceed the limits set for the voltage on the Z piezo.

        Args:
        Vx (float): X peizo voltage for the touchdown
        Vy (float): Y piezo voltage for the thouchdown
        start (float): Z piezo voltage where touchdown sweep starts
        move_attocubes (bool): If False attocube motion is disabled
        '''
        super().__init__(instruments=self.instruments)

        old_c = self.c
        self.piezos.V = {'x': Vx, 'y': Vy, 'z': 0}
        td = Touchdown(self.instruments,
                       Vz_max=self.Vz_max,
                       # planescan = True means don't move attocubes
                       planescan=(not move_attocubes)
                       )
        td.run(start=start)
        center_z_value = td.Vtd
        self.c = center_z_value - self.a * Vx - self.b * Vy

        # Check that no points within the scan range exceed the limits
        # set on the voltage over the piezos.
        for x in [-self.piezos.x.Vmax, self.piezos.x.Vmax]:
            for y in [-self.piezos.y.Vmax, self.piezos.y.Vmax]:
                z_maxormin = self.plane(x, y)
                if z_maxormin > self.piezos.z.Vmax or z_maxormin < 0:
                    self.c = old_c
                    raise Exception(
                        'Plane now extends outside range of piezos!'
                        'Move the attocubes and try again.')
        # If c decreased, then we subtract a positive number from the plane
        self.Z -= (old_c - self.c)
        self.save(savefig=False)
