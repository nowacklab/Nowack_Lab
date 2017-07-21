import numpy as np, time, matplotlib.pyplot as plt, matplotlib
from IPython import display
from mpl_toolkits.axes_grid1 import make_axes_locatable

from .touchdown import Touchdown
from ..Utilities.utilities import reject_outliers_plane, fit_plane
from ..Utilities.save import Measurement
from ..Utilities.plotting.plot_mpl import extents, using_notebook_backend

class Planefit(Measurement):
    '''
    Take touchdowns in a grid to define a plane.
    '''
    instrument_list = ['daq', 'lockin_cap', 'piezos', 'atto']

    a = np.nan
    b = np.nan
    c = np.nan

    def __init__(self, instruments={}, span=[400, 400], center=[0, 0],
                 numpts=[4, 4], Vz_max=None):
        '''
        Take touchdowns in a grid to determine the slope of the sample
        surface.

        Args:
        instruments (dict): must contain the instruments required for
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
        daq, lockin_cap, atto, piezos, montana

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
            if hasattr(self, 'piezos'):
                Vz_max = self.piezos.z.Vmax
        self.Vz_max = Vz_max

        self.x = np.linspace(center[0] - span[0] / 2,
                             center[0] + span[0] / 2, numpts[0])
        self.y = np.linspace(center[1] - span[1] / 2,
                             center[1] + span[1] / 2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y)
        self.Z = np.nan * self.X  # makes array of nans same size as grid
        self.Zdiff = np.nan * self.X  # makes array of nans same size as grid


    def calculate_plane(self, no_outliers=False): # disabled 7/21/2017
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
                         'y': self.center[1],
                         'z': -self.Vz_max
                     }
        self.td = Touchdown(self.instruments, Vz_max=self.Vz_max, planescan=True)
        self.td.run()

        # If the initial touchdown generates a poor fit, try again
        n = 0
        while self.td.error_flag and n < 5:
            self.td = Touchdown(self.instruments, Vz_max=self.Vz_max, planescan=True)
            self.td.run()
            n = n + 1

        if self.td.error_flag:
            raise Exception(r'Can\'t fit capacitance signal.')
        else:
            center_z_value = self.td.Vtd

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
                self.td = Touchdown(self.instruments,
                               Vz_max=self.Vz_max, planescan=True)

                n = 0
                while td.error_flag is True and n < 5:
                    print('Redo')
                    self.td = Touchdown(self.instruments,
                                   Vz_max = self.Vz_max, planescan=True)
                    self.td.title = '(%i, %i). TD# %i' % (i, j, counter)
                    self.td.run()
                    n = i + 1
                    plt.close(self.td.fig)

                # Record the touchdown voltage and update the plots
                self.Z[i, j] = self.td.Vtd
                self.calculate_plane()
                self.Zdiff = self.Z - self.plane(self.X, self.Y)
                self.plot(i,j)

                # Return to zero between points.
                self.piezos.V = 0

        if edges_only:
            # to prepare it for lstsq
            self.Z = np.ma.masked_array(self.Z, mask)

        self.piezos.V = 0
        self.calculate_plane()

    @classmethod
    def load(cls, json_file=None, instruments={}, unwanted_keys=[]):
        '''
        Plane load method.
        If no json_file specified, will load the last plane taken.
        Useful if you lose the object while scanning.
        '''
        obj = super(Planefit, cls).load(json_file, instruments, unwanted_keys)
        obj.instruments = instruments

        return obj

    def plane(self, x, y):
        '''
        Given points x and y, calculates a point z on the plane.
        '''
        return self.a * x + self.b * y + self.c

    def plot(self, i=None, j=None):
        '''
        First plot:
        Grid of individual touchdowns
        Arguments:
        i, j - indices of the current x,y point.

        Second plot:
        Visualize a plane and compare to touchdown voltages.

        Generates two colorplots:
        1. Plots the touchdown voltages in a grid.
        2. Plots the difference between the measured touchdown voltage
        and the fit plane.
        '''
        if hasattr(self, 'td'):
            self.td.gridplot(self.ax_grid[-(i+1),j]) #FIXME indices...?

        self.im[0].set_data(self.Z)
        self.im[1].set_data(self.Zdiff)

        # Adjust colorbar limits for new data
        self.im[0].colorbar.set_clim([np.nanmin(self.Z), np.nanmax(self.Z)])
        self.im[1].colorbar.set_clim([np.nanmin(self.Zdiff.flatten()),
                                        np.nanmax(self.Zdiff.flatten())])
        # Update the colorbars
        self.im[0].colorbar.draw_all()
        self.im[1].colorbar.draw_all()

        self.fig_grid.canvas.draw()
        self.fig.canvas.draw()

        # Do not flush events for inline or notebook backends
        if using_notebook_backend()
            return

        self.fig.canvas.flush_events()


    def save(self, savefig=True):
        '''
        Saves the planefit object to json.
        Also saves the figure as a pdf, if wanted.
        '''
        self._save(self.filename, savefig)


    def setup_plots(self):
        '''
        Set up a grid plot for the individual touchdowns on the plane.
        '''
        # Set up grid of touchdowns
        numX, numY = self.numpts
        self.fig_grid = plt.figure(figsize=(numX*2, numY*2))
        axes = []
        for i in range(numX*numY):
            ax = self.fig_grid.add_subplot(numX, numY, i+1)
            ax.set_xticks([])
            ax.set_yticks([])
            axes.append(ax)
        self.fig_grid.subplots_adjust(wspace=0, hspace=0)
        self.ax_grid = np.reshape(axes, self.numpts)

        # Set up colorplot figure
        self.fig, self.ax = plt.subplots(1, 2, figsize=(12,6))

        extent = extents(self.X, self.Y)
        im0 = self.ax[0].imshow(self.Z, origin='lower', extent=extent)
        im1 = self.ax[1].imshow(self.Zdiff, origin='lower', cmap='RdBu', extent=extent)
        self.im = [im0, im1]

        self.ax[0].set_title('Touchdown Voltages', size='medium')
        self.ax[1].set_title(r'$V_{\rm td} - V_{\rm fit}$', size='medium')

        for ax, im in zip(self.ax, self.im):
            ax.set_xlabel('X Position (V)')
            ax.set_ylabel('Y Position (V)')

            # Add colorbars
            d = make_axes_locatable(ax)
            cax = d.append_axes('right', size=0.1, pad=0.1)
            cbar = plt.colorbar(im, cax)

        self.fig.tight_layout(pad=5)


    def update_c(self, Vx=0, Vy=0, start=None, move_attocubes=False):
        '''
        Does a single touchdown to update the offset of the plane.

        After the touchdown the corners of thep plane are checked
        to see if any of the voltages within the X,Y scanrange
        exceed the limits set for the voltage on the Z piezo.

        Args:
        Vx (float): X piezo voltage for the touchdown
        Vy (float): Y piezo voltage for the thouchdown
        start (float): Z piezo voltage where touchdown sweep starts
        move_attocubes (bool): If False, attocube motion is disabled
        '''
        self.make_timestamp_and_filename()

        old_c = self.c
        self.piezos.V = {'x': Vx, 'y': Vy, 'z': 0}
        self.td = Touchdown(self.instruments,
                       disable_attocubes = not move_attocubes,
                       Vz_max = self.Vz_max,
                       )
        self.td.run(start=start)
        center_z_value = self.td.Vtd
        self.c = center_z_value - self.a * Vx - self.b * Vy

        # Check that no points within the scan range exceed the limits
        # set on the voltage over the piezos.
        for x in [-self.piezos.x.Vmax, self.piezos.x.Vmax]:
            for y in [-self.piezos.y.Vmax, self.piezos.y.Vmax]:
                z_maxormin = self.plane(x, y)
                if z_maxormin > self.piezos.z.Vmax or z_maxormin < 0:
                    self.c = old_c
                    raise Exception(
                        'Plane now extends outside positive range of Z piezo! '+
                        'Move the attocubes and try again.')
        # Subtract old c, add new c
        self.Z -= (old_c - self.c)
        self.save(savefig=False)
