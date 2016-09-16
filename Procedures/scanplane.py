import numpy as np
from numpy.linalg import lstsq
from . import navigation, planefit
import time, os
from datetime import datetime
from scipy.interpolate import interp1d as interp
import matplotlib.pyplot as plt
from IPython import display
from numpy import ma
from ..Utilities.plotting import plot_bokeh as pb
from ..Instruments import piezos, nidaq, montana, squidarray
from ..Utilities.save import Measurement

_home = os.path.expanduser("~")
DATA_FOLDER = os.path.join(_home, 'Dropbox (Nowack lab)', 'TeamData', 'Montana', 'Scans')

class Scanplane(Measurement):
    im_dc = None
    im_cap = None
    im_acx = None
    im_acy = None
    line_full = None
    line_interp = None

    def __init__(self, instruments=None, span=[100,100],
                        center=[0,0], numpts=[50,50], plane=None,
                        scanheight=5, inp_dc=0, inp_cap=1,
                        inp_acx=None, inp_acy=None,
                        freq=1500, raster=False):

        self.inp_dc = 'ai%s' %inp_dc
        self.inp_acx = 'ai%s' %inp_acx
        self.inp_acy = 'ai%s' %inp_acy
        self.inp_cap = 'ai%s' %inp_cap

        if instruments:
            self.piezos = instruments['piezos']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
            self.squidarray = instruments['squidarray']
            self.preamp = instruments['preamp']
            self.lockin_squid = instruments['lockin_squid']
            self.lockin_cap = instruments['lockin_cap']
            self.attocube = instruments['attocube']

            self.daq.add_input(self.inp_dc)
            self.daq.add_input(self.inp_acx)
            self.daq.add_input(self.inp_acy)
            self.daq.add_input(self.inp_cap)
        else:
            self.piezos = None
            self.daq = None
            self.montana = None
            self.squidarray = None
            self.preamp = None
            self.lockin_squid = None
            self.lockin_cap = None
            self.attocube = None
            print('Instruments not loaded... can only plot!')

        self.freq = freq
        self.raster = raster
        self.span = span
        self.center = center
        self.numpts = numpts
        if not plane:
            plane = planefit.Planefit()
        self.plane = plane

        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? \'q\' to quit.')
            if inp == 'q':
                raise Exception('Terminated by user')
        self.scanheight = scanheight

        self.x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y, indexing='ij') # indexing ij follows matrix indexing convention
        try:
            self.Z = self.plane.plane(self.X, self.Y) - self.scanheight
        except:
            print('plane not loaded... no idea where the surface is without a plane!')

        self.V = np.full(self.X.shape, np.nan)
        self.V_acx = np.full(self.X.shape, np.nan)
        self.V_acy = np.full(self.X.shape, np.nan)
        self.C = np.full(self.X.shape, np.nan)

        self.V_piezo_full = np.array([])
        self.V_squid_full = np.array([])
        self.V_piezo_interp = np.array([])
        self.V_squid_interp = np.array([])
        self.linecuts = {}

        self.filename = ''
        self.end_time = ''

    def __getstate__(self):
        super().__getstate__() # from Measurement superclass,
                               # need this in every getstate to get save_dict
        self.save_dict.update({"timestamp": self.timestamp,
                          "end_time": self.end_time,
                          "piezos": self.piezos,
                          "frequency": self.freq,
                          "daq": self.daq,
                          "montana": self.montana,
                          "squidarray": self.squidarray,
                          "linecuts": self.linecuts,
                          "V": self.V,
                          "V_acx": self.V_acx,
                          "V_acy": self.V_acy,
                          "C": self.C,
                          "plane": self.plane,
                          "span": self.span,
                          "center": self.center,
                          "numpts": self.numpts,
                          "preamp": self.preamp,
                          "lockin_squid": self.lockin_squid,
                          "lockin_cap": self.lockin_cap,
                          "attocube": self.attocube
                      })
        return self.save_dict

    def do(self, fast_axis = 'x'):
        ## Start time and temperature
        super().make_timestamp_and_filename('scan')
        tstart = time.time()
        #temporarily commented out so we can scan witout internet on montana
        #computer
        #self.temp_start = self.montana.temperature['platform']

        ## make sure all points are not out of range of piezos before starting anything
        for i in range(self.X.shape[0]):
            self.piezos.check_lim({'x':self.X[i,:],
                                    'y':self.Y[i,:],
                                    'z':self.Z[i,:]
                                    }
                                )

        ## Loop over Y values if fast_axis is x, X values if fast_axis is y
        if fast_axis == 'x':
            num_lines = int(self.X.shape[1]) # loop over Y
        elif fast_axis == 'y':
            num_lines = int(self.X.shape[0]) # loop over X
        else:
            raise Exception('Specify x or y as fast axis!')

        for i in range(num_lines): # loop over every line
            k = 0
            if self.raster:
                if i%2 == 0: # if even
                    k = 0 # k is used to determine Vstart/Vend. For forward, will sweep from the 0th element to the -(k+1) = -1st = last element
                else: # if odd
                    k = -1 # k is used to determine Vstart/Vend. For forward, will sweep from the -1st = last element to the -(k+1) = 0th = first element
            # if not rastering, k=0, meaning always forward sweeps

            ## Starting and ending piezo voltages for the line
            if fast_axis == 'x':
                Vstart = {'x': self.X[k,i], 'y': self.Y[k,i], 'z': self.Z[k,i]} # for forward, starts at 0,i; backward: -1, i
                Vend = {'x': self.X[-(k+1),i], 'y': self.Y[-(k+1),i], 'z': self.Z[-(k+1),i]} # for forward, ends at -1,i; backward: 0, i
            elif fast_axis == 'y':
                Vstart = {'x': self.X[i,k], 'y': self.Y[i,k], 'z': self.Z[i,k]} # for forward, starts at i,0; backward: i,-1
                Vend = {'x': self.X[i,-(k+1)], 'y': self.Y[i,-(k+1)], 'z': self.Z[i,-(k+1)]} # for forward, ends at i,-1; backward: i,0

            ## Explicitly go to first point of scan
            self.piezos.sweep(self.piezos.V, Vstart, freq=1500) # change this frequency to go back faster!!
            self.squidarray.reset()
            time.sleep(3)

            ## Do the sweep
            out, V, t = self.piezos.sweep(Vstart, Vend, freq=self.freq) # sweep over X

            ## Flip the backwards sweeps
            if k == -1: # flip only the backwards sweeps
                for d in out, V:
                    for key, value in d.items():
                        d[key] = value[::-1] # flip the 1D array

            ## Save linecuts
            self.linecuts[str(i)] = {"Vstart": Vstart,
                                "Vend": Vend,
                                "Vsquid": {"Vdc": np.array(V[self.inp_dc]).tolist(),  #why convert to array and then back to list??
                                           "V_acx": np.array(V[self.inp_acx]).tolist(),
                                           "V_acy": np.array(V[self.inp_acy]).tolist()}}

            ## Interpolate to the number of lines
            self.V_piezo_full = out[fast_axis] # actual voltages swept in x or y direction
            if fast_axis == 'x':
                self.V_piezo_interp = self.X[:,i]
            elif fast_axis == 'y':
                self.V_piezo_interp = self.Y[i,:]

            # Store this line's signals for Vdc, Vac x/y, and Cap
            self.V_squid_full = V[self.inp_dc]
            self.V_acx_full = V[self.inp_acx]
            self.V_acy_full = V[self.inp_acy]
            self.C_full = V[self.inp_cap]

            # interpolation functions
            interp_V = interp(self.V_piezo_full, self.V_squid_full)
            interp_V_acx = interp(self.V_piezo_full, self.V_acx_full)
            interp_V_acy = interp(self.V_piezo_full, self.V_acy_full)
            interp_C = interp(self.V_piezo_full, self.C_full)

            # interpolated signals
            self.V_squid_interp = interp_V(self.V_piezo_interp)
            self.V_acx_interp = interp_V_acx(self.V_piezo_interp)
            self.V_acy_interp = interp_V_acy(self.V_piezo_interp)
            self.C_interp = interp_C(self.V_piezo_interp)

            # store these in the 2D arrays
            if fast_axis == 'x':
                self.V[:,i] = self.V_squid_interp # changes from actual output data to give desired number of points
                self.V_acx[:,i] = self.V_acx_interp
                self.V_acy[:,i] = self.V_acy_interp
                self.C[:,i] = self.C_interp
            elif fast_axis == 'y':
                self.V[i,:] = self.V_squid_interp # changes from actual output data to give desired number of points
                self.V_acx[i,:] = self.V_acx_interp
                self.V_acy[i,:] = self.V_acy_interp
                self.C[i,:] = self.C_interp

            self.save_line(i, Vstart)

            self.plot()


        self.piezos.V = 0
        self.save()

        self.end_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        tend = time.time()
        print('Scan took %f minutes' %((tend-tstart)/60))
        return


    def plot(self):
        '''
        Update all plots.
        '''
        if not hasattr(self, 'fig_dc'): # see if this exists
            self.setup_plots()

        self.im_dc = pb.image(self.fig_dc, self.X, self.Y, self.V,
            z_title = 'DC %s (V)' %self.inp_dc, im_handle = self.im_dc
        )

        self.im_cap = pb.image(self.fig_cap, self.X, self.Y, self.C,
            z_title = 'Cap %s (V)' %self.inp_cap, im_handle = self.im_cap,
            cmap = 'afmhot'
        )

        self.im_acx = pb.image(self.fig_acx, self.X, self.Y, self.V_acx,
            z_title = 'AC X %s (V)' %self.inp_acx, im_handle = self.im_acx
        )

        self.im_acy = pb.image(self.fig_acy, self.X, self.Y, self.V_acy,
            z_title = 'AC Y %s (V)' %self.inp_acy, im_handle = self.im_acy
        )

        self.plot_line()



    def setup_plots(self):
        '''
        Set up all plots.
        '''
        ## Grid will be 2x2 with linecut at bottom
        ## top left
        self.fig_dc = pb.figure(
            title = self.filename
        )
        self.fig_dc.fig.plot_width=700 # correct room taken up by colorbar
        self.fig_dc.fig.min_border_top = 0
        self.fig_dc.fig.min_border_bottom = 0

        self.fig_cap = pb.figure(
            x_range = self.fig_dc.fig.x_range,
            y_range = self.fig_dc.fig.y_range
        )
        self.fig_cap.fig.plot_width=700
        self.fig_cap.fig.min_border_top = 0
        self.fig_cap.fig.min_border_bottom = 0

        self.fig_acx = pb.figure(
            x_range = self.fig_dc.fig.x_range,
            y_range = self.fig_dc.fig.y_range
        )
        self.fig_acx.fig.plot_width=700
        self.fig_acx.fig.min_border_top = 0
        self.fig_acx.fig.min_border_bottom = 0

        self.fig_acy = pb.figure(
            x_range = self.fig_dc.fig.x_range,
            y_range = self.fig_dc.fig.y_range
        )
        self.fig_acy.fig.plot_width=700
        self.fig_acy.fig.min_border_top = 0
        self.fig_acy.fig.min_border_bottom = 0

        self.fig_line = pb.figure(
            xlabel = 'Distance (Vpiezo)',
            ylabel = 'Signal (V)'
        )
        self.fig_line.fig.plot_width=1200
        self.fig_line.fig.min_border_top = 0
        self.fig_line.fig.min_border_bottom = 0

        self.plot() # plot all the images and lines

        self.grid = pb.plot_grid([[self.fig_dc.fig, self.fig_acx.fig],
                    [self.fig_cap.fig, self.fig_acy.fig],
                     [self.fig_line.fig]], width=1000, height=1000
                 )
        pb.show(self.grid)


    def plot_line(self):
        self.line_full = pb.line(self.fig_line, self.V_piezo_full,
            self.V_squid_full, line_handle = self.line_full,
        )
        self.line_interp = pb.line(self.fig_line, self.V_piezo_interp,
            self.V_squid_interp, line_handle = self.line_interp,
            color='red', linestyle='.'
        )

    def save(self, savefig=True):
        '''
        Saves the scanplane object to json in .../TeamData/Montana/Scans/
        Also saves the figure as a pdf, if wanted.
        '''

        self.tojson(DATA_FOLDER, self.filename)

        if savefig:
            self.fig.savefig(self.filename+'.pdf', bbox_inches='tight')


    def save_line(self, i, Vstart):
        '''
        Saves each line individually to JSON.
        '''
        line = Line()
        line.scan_filename = self.filename
        line.idx = i
        line.Vstart = Vstart
        line.V_squid_full = self.V_squid_full
        line.V_piezo_full = self.V_piezo_full
        line.make_timestamp_and_filename('scan_line')

        line.tojson(DATA_FOLDER, line.filename)

class Line(Measurement):
    def __getstate__(self):
        super().__getstate__() # from Measurement superclass,
                               # need this in every getstate to get save_dict
        self.save_dict.update({"idx": self.idx,
                          "Vstart": self.Vstart,
                          "V_squid_full": self.V_squid_full,
                          "V_piezo_full": self.V_piezo_full,
                          "scan_filename": self.scan_filename
                      })
        return self.save_dict

if __name__ == '__main__':
    'hey'
