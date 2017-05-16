import numpy as np
import time, os
from scipy.interpolate import interp1d
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from ..Utilities.plotting import plot_mpl
from ..Instruments import piezos, montana, squidarray
from ..Utilities.save import Measurement, get_todays_data_dir, get_local_data_path
from ..Utilities import conversions
from ..Utilities.utilities import AttrDict

class Scanplane(Measurement):
    """Scan over a plane while monitoring signal on DAQ

    Attributes:
        _daq_inputs (list): list of channel names for DAQ to monitor
        _conversions (AttrDict): mapping from DAQ voltages to real units
        instrument_list (list): instrument names that Scanplane needs in
            order to be initialized.
    """
    # DAQ channel labels required for this class.
    _daq_inputs = ['dc','cap','acx','acy']
    _conversions = AttrDict({
        'dc': conversions.Vsquid_to_phi0['High'], # Assume high; changed in init when array loaded
        'cap': conversions.V_to_C,
        'acx': conversions.Vsquid_to_phi0['High'],
        'acy': conversions.Vsquid_to_phi0['High'],
        'x': conversions.Vx_to_um,
        'y': conversions.Vy_to_um
    })
    _units = AttrDict({
        'dc': 'phi0',
        'cap': 'C',
        'acx': 'phi0',
        'acy': 'phi0',
        'x': '~um',
        'y': '~um',
    })
    instrument_list = ['piezos',
                       'montana',
                       'squidarray',
                       'preamp',
                       'lockin_squid',
                       'lockin_cap',
                       'atto',
                       'daq']

    def __init__(self, instruments={}, plane=None, span=[800,800],
                        center=[0,0], numpts=[20,20],
                        scanheight=15, scan_rate=120, raster=False):

        super().__init__(instruments=instruments)

        # Load the correct SAA sensitivity based on the SAA feedback
        # resistor
        try: # try block enables creating object without instruments
            Vsquid_to_phi0 = conversions.Vsquid_to_phi0[self.squidarray.sensitivity]
            self._conversions['acx'] = Vsquid_to_phi0
            self._conversions['acy'] = Vsquid_to_phi0
            self._conversions['dc'] = Vsquid_to_phi0 # doesn't consider preamp gain. If preamp communication fails, then this will be recorded
            # Divide out the preamp gain for the DC channel
            self._conversions['dc'] /= self.preamp.gain
        except:
            pass

        # Define variables specified in init
        self.scan_rate = scan_rate
        self.raster = raster
        self.span = span
        self.center = center
        self.numpts = numpts
        self.plane = plane

        self.V = AttrDict({
           chan: np.nan for chan in self._daq_inputs + ['piezo']
        })
        self.Vfull = AttrDict({
           chan: np.nan for chan in self._daq_inputs + ['piezo']
        })
        self.Vinterp = AttrDict({
           chan: np.nan for chan in self._daq_inputs + ['piezo']
        })

        self.scanheight = scanheight

        x = np.linspace(center[0]-span[0]/2,
                        center[0]+span[0]/2,
                        numpts[0])
        y = np.linspace(center[1]-span[1]/2,
                        center[1]+span[1]/2,
                        numpts[1])

        self.X, self.Y = np.meshgrid(x, y)
        try:
            self.Z = self.plane.plane(self.X, self.Y) - self.scanheight
        except:
            print('plane not loaded')

        for chan in self._daq_inputs:
            # Initialize one array per DAQ channel
            self.V[chan] = np.full(self.X.shape, np.nan)
            # If no conversion factor is given then directly record the
            # voltage by setting conversion = 1
            if chan not in self._conversions.keys():
                self._conversions[chan] = 1
            if chan not in self._units.keys():
                self._units[chan] = 'V'

        # Scan in X direction by default
        self.fast_axis = 'x'

    def do(self, fast_axis = 'x', surface=False):
        '''
        Routine to perform a scan over a plane.

        Keyword arguments:
            fast_axis: If 'x' (default) take linecuts in the X direction
            If 'y', take linecuts in the Y direction.

            surface: If False sweep out lines over the sufrace. If True,
            piezos.sweep_surface is used during the scan
        '''
        self.fast_axis = fast_axis

        # Check if points in the scan are within the voltage limits of
        # Piezos
        for i in range(self.X.shape[0]):
            self.piezos.x.check_lim(self.X[i,:])
            self.piezos.y.check_lim(self.Y[i,:])
            self.piezos.z.check_lim(self.Z[i,:])

        # Loop over Y values if fast_axis is x,
        # Loop over X values if fast_axis is y
        ## Print a warning if the fast_axis has fewer points than the slow.
        def slow_axis_alert():
            print('Slow axis has more points than fast axis!')
            import winsound
            winsound.Beep(int(440*2**(1/2)),200) # play a tone
            winsound.Beep(440,200) # play a tone
        if fast_axis == 'x':
            num_lines = int(self.X.shape[0]) # loop over Y
            if num_lines > int(self.X.shape[1]): # if more Y points than X
                slow_axis_alert()
        elif fast_axis == 'y':
            num_lines = int(self.X.shape[1]) # loop over X
            if num_lines > int(self.X.shape[0]): # if more X points than Y
                slow_axis_alert()
        else:
            raise Exception('Specify x or y as fast axis!')

        # Measure capacitance offset
        Vcap_offset = []
        for i in range(5):
            time.sleep(0.5)
            Vcap_offset.append(
                self.lockin_cap.convert_output(self.daq.inputs['cap'].V)
            )
        Vcap_offset = np.mean(Vcap_offset)

        # Loop over each line in the scan
        for i in range(num_lines):
            # If we detected a keyboard interrupt stop the scan here
            # The DAQ is not in use at this point so ending the scan
            # should be safe.
            if self.interrupt:
                break
            k = 0
            if self.raster:
                if i%2 == 0: # if even
                    # k keeps track of sweeping forward vs. backwards
                    k = 0
                else: # if odd
                    k = -1
            # if not rastering, k=0, meaning always forward sweeps

            # Starting and ending piezo voltages for the line
            # for forward, starts at 0,i; backward: -1, i
            if fast_axis == 'x':
                Vstart = {'x': self.X[i,k],
                          'y': self.Y[i,k],
                          'z': self.Z[i,k]}
                # for forward, ends at -1,i; backward: 0, i
                Vend = {'x': self.X[i,-(k+1)],
                        'y': self.Y[i,-(k+1)],
                        'z': self.Z[i,-(k+1)]}
            elif fast_axis == 'y':
                # for forward, starts at i,0; backward: i,-1
                Vstart = {'x': self.X[k,i],
                          'y': self.Y[k,i],
                          'z': self.Z[k,i]}
                # for forward, ends at i,-1; backward: i,0
                Vend = {'x': self.X[-(k+1),i],
                        'y': self.Y[-(k+1),i],
                        'z': self.Z[-(k+1),i]}

            # Go to first point of scan
            self.piezos.sweep(self.piezos.V, Vstart)
            self.squidarray.reset()
            time.sleep(3)
            # Begin the sweep
            if not surface:
                # Sweep over X
                output_data, received = self.piezos.sweep(Vstart, Vend,
                                            chan_in = self._daq_inputs,
                                            sweep_rate=self.scan_rate
                                        )
            else:
                # 50 points should be good for giving this to
                # piezos.sweep_surface
                x = np.linspace(Vstart['x'], Vend['x'])
                y = np.linspace(Vstart['y'], Vend['y'])
                if fast_axis == 'x':
                    Z = self.plane.surface(x,y)[:,i]
                else:
                    Z = self.plane.surface(x,y)[i,:]
                output_data = {'x': x, 'y':y, 'z': Z}
                output_data, received = self.piezos.sweep_surface(
                    output_data,
                    chan_in = self._daq_inputs,
                    sweep_rate = self.scan_rate
                )
            # Flip the backwards sweeps
            if k == -1: # flip only the backwards sweeps
                for d in output_data, received:
                    for key, value in d.items():
                        d[key] = value[::-1] # flip the 1D array

            # Return to zero for a couple of seconds:
            self.piezos.V = 0
            time.sleep(2)

            # Interpolate to the number of lines
            self.Vfull['piezo'] = output_data[fast_axis]
            if fast_axis == 'x':
                self.Vinterp['piezo'] = self.X[i,:]
            elif fast_axis == 'y':
                self.Vinterp['piezo'] = self.Y[:,i]


            # Store this line's signals for Vdc, Vac x/y, and Cap
            for chan in self._daq_inputs:
                self.Vfull[chan] = received[chan]

            # Convert from DAQ volts to lockin volts where applicable
            for chan in ['acx', 'acy']:
                self.Vfull[chan] = self.lockin_squid.convert_output(
                    self.Vfull[chan])
            self.Vfull['cap'] = self.lockin_cap.convert_output(
                self.Vfull['cap']) - Vcap_offset

            # Interpolate the data and store in the 2D arrays
            for chan in self._daq_inputs:
                f = interp1d(self.Vfull['piezo'], self.Vfull[chan])
                self.Vinterp[chan] = f(self.Vinterp['piezo'])
                if fast_axis == 'x':
                    self.V[chan][i,:] = self.Vinterp[chan]
                else:
                    self.V[chan][:,i] = self.Vinterp[chan]

            self.save_line(i, Vstart)
            self.plot()

        self.piezos.V = 0

    def plot(self):
        '''
        Update all plots.
        '''
        super().plot()

        # Update the line plot
        self.plot_line()

        # Iterate over the color plots and update data with new line
        for chan in self._daq_inputs:
            data_nan = np.array(self.V[chan]*self._conversions[chan],
                                dtype=np.float)
            data_masked = np.ma.masked_where(np.isnan(data_nan), data_nan)

            # Set a new image for the plot
            self.im[chan].set_data(data_masked)
            # Adjust colorbar limits for new data
            self.cbars[chan].set_clim([data_masked.min(),
                                       data_masked.max()])
            # Update the colorbars
            self.cbars[chan].draw_all()

        self.fig.canvas.draw()

        ## Do not flush events for inline or notebook backends
        if matplotlib.get_backend() in ('nbAgg','module://ipykernel.pylab.backend_inline'):
            return

        self.fig.canvas.flush_events()

    def setup_plots(self):
        '''
        Set up all plots.
        '''
        # Use the aspect ratio of the image set subplot size.
        # The aspect ratio is Xspan/Yspan
        aspect = self.span[0]/self.span[1]
        numplots = len(self._daq_inputs)

        if aspect > 1: # If X is longer than Y, we want 2 columns of wide plots
            num_row = int(np.ceil(numplots/2))
            num_col = 2
            width = 14
            height = width/aspect + 1 # +1 for title/axis labels
        else:
            num_row = 2
            num_col = int(np.ceil(numplots/2))
            height = 10
            width = height*aspect + 4 # pad for colorbars/axis labels

        ## Make axis dicts, with daq input channels as keys.
        self.fig = plt.figure(figsize=(width,height))
        self.fig_cuts = plt.figure(figsize=(6,8))
        self.ax = AttrDict()
        self.ax_cuts = AttrDict()
        for i, chan in enumerate(self._daq_inputs):
            ## Populate axes in the figure.
            self.ax[chan] = self.fig.add_subplot(num_row, num_col, i+1)
            self.ax_cuts[chan] = self.fig_cuts.add_subplot(
                                                len(self._daq_inputs), 1, i+1)

        ## Determine colormaps and labels for each channel.
        cmaps = AttrDict(dc='RdBu', cap='afmhot', acx='magma', acy='magma')
        clabels = AttrDict(
            dc = 'DC Flux ($\Phi_0$)',
            cap = 'Capacitance (fF)',
            acx = 'AC X ($\Phi_0$)',
            acy = 'AC Y ($\Phi_0$)',
        )

        self.im = AttrDict()
        self.cbars = AttrDict()
        self.lines_full = AttrDict()
        self.lines_interp = AttrDict()

        for chan in self._daq_inputs:
            ax = self.ax[chan]
            cmap = cmaps[chan]
            clabel = clabels[chan]

            ## Plot the DC signal, capactitance and AC signal on 2D colorplots

            # Convert None in data to NaN
            nan_data = np.array(self.V[chan]*self._conversions[chan])
            # Create masked array where data is NaN
            masked_data = np.ma.masked_where(np.isnan(nan_data), nan_data)

            # Plot masked data on the appropriate axis with imshow
            image = ax.imshow(masked_data, cmap=cmap, origin="lower",
                              extent = [self.X.min(), self.X.max(),
                                        self.Y.min(), self.Y.max()])

            # Create a colorbar that matches the image height
            d = make_axes_locatable(ax)
            cax = d.append_axes("right", size=0.1, pad=0.1)
            cbar = plt.colorbar(image, cax=cax)
            cbar.set_label(clabel, rotation=270, labelpad=12)
            cbar.formatter.set_powerlimits((-2,2))
            self.im[chan] = image
            self.cbars[chan] = cbar

            # Label the axes - including a timestamp
            ax.set_xlabel("X Position (V)")
            ax.set_ylabel("Y Position (V)")
            title = ax.set_title(self.timestamp, size="medium", y=1.02)
            # If the title intersects the exponent label from the colorbar
            # shift the title up and center it
            # TODO

            ## Plot the last linecut for DC, AC and capacitance signals

            ax = self.ax_cuts[chan]

            # ax.plot returns a list containing the line
            # Take the line object - not the list containing the line
            self.lines_full[chan] = ax.plot(self.Vfull['piezo'],
                                            self.Vfull[chan],
                                            '-')[0]
            self.lines_interp[chan] = ax.plot(self.Vinterp['piezo'],
                                              self.Vinterp[chan], 'ok',
                                              markersize=3)[0]
            ax.set_ylabel(clabel)
            ## Scientific notation for <10^-2, >10^2
            ax.yaxis.get_major_formatter().set_powerlimits((-2,2))

        # Label the X axis of only the bottom plot
        self.ax_cuts[self._daq_inputs[-1]].set_xlabel("Position (V)")
        # Title the top plot with the timestamp
        self.ax_cuts[self._daq_inputs[0]].set_title(self.timestamp, size="medium")

        # Adjust subplot layout so all labels are visible
        # First call tight layout to prevent axis label overlap.
        self.fig.tight_layout()
        self.fig_cuts.tight_layout()

        ## Show the (now empty) figures
        self.fig.canvas.draw()
        self.fig_cuts.canvas.draw()


    def plot_line(self):
        '''
        Update the data in the linecut plot.
        '''
        for chan in self._daq_inputs:
            ax = self.ax_cuts[chan]
            l_full = self.lines_full[chan]
            l_interp = self.lines_interp[chan]

            # Update X and Y data for the "full data"
            l_full.set_xdata(self.Vfull['piezo'] *
                                            self._conversions[self.fast_axis])
            l_full.set_ydata(self.Vfull[chan] *
                                            self._conversions[chan])
            # Update X and Y data for the interpolated data
            l_interp.set_xdata(self.Vinterp['piezo'] *
                                            self._conversions[self.fast_axis])
            l_interp.set_ydata(self.Vinterp[chan] *
                                            self._conversions[chan])
            # Rescale axes for newly plotted data
            ax.relim()
            ax.autoscale_view()
        # Update the figure
        self.fig_cuts.canvas.draw()

        ## Do not flush events for inline or notebook backends
        if matplotlib.get_backend() in ('nbAgg','module://ipykernel.pylab.backend_inline'):
            return

        self.fig_cuts.canvas.flush_events()


    def save_line(self, i, Vstart):
        '''
        Saves each line individually to JSON.
        '''
        line = Line()
        line.scan_filename = self.filename
        line.idx = i
        line.Vstart = Vstart
        line.Vfull = AttrDict()
        line.Vfull['dc'] = self.Vfull['dc']
        line.Vfull['piezo'] = self.Vfull['piezo']
        line.save()


class Line(Measurement):
    def __init__(self):
        super().__init__()

    def save(self):
        filename_in_extras = os.path.join(get_local_data_path(), get_todays_data_dir(), 'extras', self.filename)
        self._save(filename_in_extras)
