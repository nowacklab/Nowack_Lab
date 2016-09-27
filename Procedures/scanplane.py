import numpy as np
from numpy.linalg import lstsq
from . import navigation, planefit
import time, os
from datetime import datetime
from scipy.interpolate import interp1d as interp
import matplotlib.pyplot as plt
from IPython import display
from numpy import ma
from ..Utilities.plotting import plot_mpl
from ..Instruments import piezos, montana, squidarray
from ..Utilities.save import Measurement, get_todays_data_path
from ..Utilities import conversions

class Scanplane(Measurement):
    instrument_list = ['piezos','montana','squidarray','preamp','lockin_squid','lockin_cap','atto','daq']

    def __init__(self, instruments={}, span=[100,100],
                        center=[0,0], numpts=[50,50], plane=None,
                        scanheight=5, inp_dc=0, inp_cap=1,
                        inp_acx=None, inp_acy=None,
                        scan_rate=120, raster=False):

        super().__init__('scan')

        self.inp_dc = 'ai%s' %inp_dc
        self.inp_acx = 'ai%s' %inp_acx
        self.inp_acy = 'ai%s' %inp_acy
        self.inp_cap = 'ai%s' %inp_cap

        self.load_instruments(instruments)

        self.scan_rate = scan_rate
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
        self.Vac_x = np.full(self.X.shape, np.nan)
        self.Vac_y = np.full(self.X.shape, np.nan)
        self.C = np.full(self.X.shape, np.nan)

        self.V_piezo_full = np.array([])
        self.V_squid_full = np.array([])
        self.V_piezo_interp = np.array([])
        self.V_squid_interp = np.array([])
        self.linecuts = {}

        self.end_time = ''

    def __getstate__(self):
        self.save_dict.update({"timestamp": self.timestamp,
                          "end_time": self.end_time,
                          "piezos": self.piezos,
                          "scan_rate": self.scan_rate,
                          "montana": self.montana,
                          "squidarray": self.squidarray,
                          "linecuts": self.linecuts,
                          "V": self.V,
                          "Vac_x": self.Vac_x,
                          "Vac_y": self.Vac_y,
                          "C": self.C,
                          "plane": self.plane,
                          "span": self.span,
                          "center": self.center,
                          "numpts": self.numpts,
                          "preamp": self.preamp,
                          "lockin_squid": self.lockin_squid,
                          "lockin_cap": self.lockin_cap,
                          "atto": self.atto,
                          "X": self.X,
                          "Y": self.Y
                      })
        return self.save_dict


    def do(self, fast_axis = 'x', linear=True): # linear True = sweep in lines, False sweep over plane surface
        ## Start time and temperature
        tstart = time.time()
        #temporarily commented out so we can scan witout internet on montana
        #computer
        #self.temp_start = self.montana.temperature['platform']

        self.setup_plots()

        ## make sure all points are not out of range of piezos before starting anything
        for i in range(self.X.shape[0]):
            self.piezos.x.check_lim(self.X[i,:])
            self.piezos.y.check_lim(self.Y[i,:])
            self.piezos.z.check_lim(self.Z[i,:])

        ## Loop over Y values if fast_axis is x, X values if fast_axis is y
        if fast_axis == 'x':
            num_lines = int(self.X.shape[1]) # loop over Y
        elif fast_axis == 'y':
            num_lines = int(self.X.shape[0]) # loop over X
        else:
            raise Exception('Specify x or y as fast axis!')

        ## Measure capacitance offset
        C0s = []
        for i in range(5):
            time.sleep(0.5)
            C0s.append(self.lockin_cap.convert_output(getattr(self.daq, self.inp_cap))*conversions.V_to_C)
        C0 = np.mean(C0s)

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
            self.piezos.sweep(self.piezos.V, Vstart)
            self.squidarray.reset()
            time.sleep(3)

            ## Do the sweep
            in_chans = [self.inp_dc, self.inp_acx, self.inp_acy, self.inp_cap]

            if linear:
                output_data, received = self.piezos.sweep(Vstart, Vend, chan_in = in_chans,
                                        sweep_rate=self.scan_rate
                                    ) # sweep over X
            else:
                x = np.linspace(Vstart['x'], Vend['x']) # 50 points should be good for giving this to piezos.sweep_surface
                y = np.linspace(Vstart['y'], Vend['y'])
                if fast_axis == 'x':
                    Z = self.plane.surface(x,y)[:,i]
                else:
                    Z = self.plane.surface(x,y)[i,:]
                output_data = {'x': x, 'y':y, 'z': Z}
                output_data, received = self.piezos.sweep_surface(output_data,
                                                        chan_in = in_chans,
                                                        sweep_rate = self.scan_rate
                                                    )

            ## Flip the backwards sweeps
            if k == -1: # flip only the backwards sweeps
                for d in output_data, received:
                    for key, value in d.items():
                        d[key] = value[::-1] # flip the 1D array

            ## Return to zero for a couple of seconds:
            self.piezos.V = 0
            time.sleep(2)

            ## Interpolate to the number of lines
            self.V_piezo_full = output_data[fast_axis] # actual voltages swept in x or y direction
            if fast_axis == 'x':
                self.V_piezo_interp = self.X[:,i]
            elif fast_axis == 'y':
                self.V_piezo_interp = self.Y[i,:]


            # Store this line's signals for Vdc, Vac x/y, and Cap
            # Convert from DAQ volts to lockin volts
            Vdc = received[self.inp_dc]
            self.V_squid_full = self.lockin_squid.convert_output(Vdc)

            Vac_x_full = received[self.inp_acx]
            self.Vac_x_full = self.lockin_squid.convert_output(Vac_x_full)

            Vac_y_full = received[self.inp_acy]
            self.Vac_y_full = self.lockin_squid.convert_output(Vac_y_full)

            Vcap = received[self.inp_cap]
            Vcap = self.lockin_cap.convert_output(Vcap) # convert to a lockin voltage
            self.C_full = Vcap*conversions.V_to_C - C0 # convert to capacitance (fF)

            ## Save linecuts
            self.linecuts[str(i)] = {"Vstart": Vstart,
                                "Vend": Vend,
                                "Vsquid": {"Vdc": self.V_squid_full,
                                           "Vac_x": self.Vac_x_full,
                                           "Vac_y": self.Vac_y_full
                                       }
                                   }

            # interpolation functions
            interp_V = interp(self.V_piezo_full, self.V_squid_full)
            interp_Vac_x = interp(self.V_piezo_full, self.Vac_x_full)
            interp_Vac_y = interp(self.V_piezo_full, self.Vac_y_full)
            interp_C = interp(self.V_piezo_full, self.C_full)

            # interpolated signals
            self.V_squid_interp = interp_V(self.V_piezo_interp)
            self.Vac_x_interp = interp_Vac_x(self.V_piezo_interp)
            self.Vac_y_interp = interp_Vac_y(self.V_piezo_interp)
            self.C_interp = interp_C(self.V_piezo_interp)

            # store these in the 2D arrays
            if fast_axis == 'x':
                self.V[:,i] = self.V_squid_interp # changes from actual output data to give desired number of points
                self.Vac_x[:,i] = self.Vac_x_interp
                self.Vac_y[:,i] = self.Vac_y_interp
                self.C[:,i] = self.C_interp
            elif fast_axis == 'y':
                self.V[i,:] = self.V_squid_interp # changes from actual output data to give desired number of points
                self.Vac_x[i,:] = self.Vac_x_interp
                self.Vac_y[i,:] = self.Vac_y_interp
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
        try:
            self.im_dc # see if this exists
        except:
            self.setup_plots()
        plot_mpl.update2D(self.im_dc, self.V)
        plot_mpl.update2D(self.im_cap, self.C)
        plot_mpl.update2D(self.im_ac_x, self.Vac_x)
        plot_mpl.update2D(self.im_ac_y, self.Vac_y)
        self.plot_line()

        self.fig.canvas.draw()


    def setup_plots(self):
        '''
        Set up all plots.
        '''
        self.fig = plt.figure(figsize=(11,11))

        ## DC magnetometry
        self.ax_dc = self.fig.add_subplot(321)
        self.im_dc = plot_mpl.plot2D(self.ax_dc,
                                        self.X,
                                        self.Y,
                                        self.V,
                                        title = self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'DC V %s' %self.inp_dc
                                    )

        ## AC x
        self.ax_ac_x = self.fig.add_subplot(323)
        self.im_ac_x = plot_mpl.plot2D(self.ax_ac_x,
                                        self.X,
                                        self.Y,
                                        self.Vac_x,
                                        cmap='cubehelix',
                                        title = self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'AC X V %s' %self.inp_acx
                                    )

        ## AC y
        self.ax_ac_y = self.fig.add_subplot(325)
        self.im_ac_y = plot_mpl.plot2D(self.ax_ac_y,
                                        self.X,
                                        self.Y,
                                        self.Vac_y,
                                        cmap='cubehelix',
                                        title = self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'AC Y V %s' %self.inp_acx
                                    )

        ## Capacitance
        self.ax_cap = self.fig.add_subplot(324)
        self.im_cap = plot_mpl.plot2D(self.ax_cap,
                                    self.X,
                                    self.Y,
                                    self.C,
                                    cmap='afmhot',
                                    title = self.filename,
                                    xlabel = r'$X (V_{piezo})$',
                                    ylabel = r'$Y (V_{piezo})$',
                                    clabel = 'Cap fF %s' %self.inp_cap
                                )

        ## "Last full scan" plot
        self.ax_line = self.fig.add_subplot(326)
        self.ax_line.set_title(self.filename, fontsize=8)
        self.line_full = self.ax_line.plot(self.V_piezo_full, self.V_squid_full, '-.k') # commas only take first element of array? ANyway, it works.
        self.line_interp = self.ax_line.plot(self.V_piezo_interp, self.V_squid_interp, '.r', markersize=12)
        self.ax_line.set_xlabel('Vpiezo (V)', fontsize=8)
        self.ax_line.set_ylabel('Last DC V line (V)', fontsize=8)

        self.line_full = self.line_full[0] # it is given as an array
        self.line_interp = self.line_interp[0]

        ## Draw everything in the notebook
        self.fig.canvas.draw()


    def plot_line(self):
        self.line_full.set_xdata(self.V_piezo_full)
        self.line_full.set_ydata(self.V_squid_full)
        self.line_interp.set_xdata(self.V_piezo_interp)
        self.line_interp.set_ydata(self.V_squid_interp)

        self.ax_line.relim()
        self.ax_line.autoscale_view()

        plot_mpl.aspect(self.ax_line, .3)

    def save(self, savefig=True):
        '''
        Saves the scanplane object to json in .../TeamData/Montana/Scans/
        Also saves the figure as a pdf, if wanted.
        '''

        self.tojson(get_todays_data_path(), self.filename)

        if savefig:
            self.fig.savefig(os.path.join(get_todays_data_path(), self.filename+'.pdf'), bbox_inches='tight')


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

        line.tojson(get_todays_data_path(), line.filename)

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
