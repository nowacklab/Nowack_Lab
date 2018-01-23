import time, os, matplotlib, matplotlib.pyplot as plt, numpy as np
from scipy.interpolate import interp1d
from mpl_toolkits.axes_grid1 import make_axes_locatable

from ..Utilities import conversions
from ..Utilities.save import Measurement, get_todays_data_dir, get_local_data_path
from ..Utilities.utilities import AttrDict
from ..Utilities.plotting.plot_mpl import extents, using_notebook_backend


class Scanplane(Measurement):
    '''
    Scan over a plane while monitoring signal on DAQ

    Attributes:
        _daq_inputs (list): list of channel names for DAQ to monitor
        _conversions (AttrDict): mapping from DAQ voltages to real units
        instrument_list (list): instrument names that Scanplane needs in
            order to be initialized.
    '''
    # DAQ channel labels required for this class.
    _daq_inputs = ['dc', 'cap', 'acx', 'acy']
    _conversions = AttrDict({
        # Assume high; changed in init when array loaded
        'dc': conversions.Vsquid_to_phi0['High'],
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
    fast_axis = 'x'


    def __init__(self, instruments={}, plane=None, span=[800, 800],
                 center=[0, 0], numpts=[20, 20],
                 scanheight=15, scan_rate=120, raster=False,
                 direction=['+','+'], ROI=None):
        '''
        direction: +/- to sweep each axis forwards or backwards.
        Flips scan image. TODO: don't flip
        ROI: List of [Vx1, Vx2, Vy1, Vy2] to specify a region of interest.
            Will draw a box from Vx1 < Vx < Vx2 and Vy1 < Vy < Vy2.
        '''


        super().__init__(instruments=instruments)

        # Load the correct SAA sensitivity based on the SAA feedback
        # resistor
        try:  # try block enables creating object without instruments
            Vsquid_to_phi0 = conversions.Vsquid_to_phi0[self.squidarray.sensitivity]
            self._conversions['acx'] = Vsquid_to_phi0
            self._conversions['acy'] = Vsquid_to_phi0
            # doesn't consider preamp gain. If preamp communication fails, then
            # this will be recorded
            self._conversions['dc'] = Vsquid_to_phi0
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
        self.scanheight = scanheight
        self.direction = direction
        self.ROI = ROI

        self.V = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo']
        })
        self.Vfull = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo']
        })
        self.Vinterp = AttrDict({
            chan: np.nan for chan in self._daq_inputs + ['piezo']
        })

        x = np.linspace(center[0] - span[0] / 2,
                        center[0] + span[0] / 2,
                        numpts[0])
        y = np.linspace(center[1] - span[1] / 2,
                        center[1] + span[1] / 2,
                        numpts[1])

        # Reverse scan direction
        if direction[0] == '-':
            x = x[::-1]
        if direction[1] == '-':
            y = y[::-1]

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


    def do(self, fast_axis='x', wait=None):
        '''
        Routine to perform a scan over a plane.

        Keyword arguments:
            fast_axis: If 'x' (default) take linecuts in the X direction
            If 'y', take linecuts in the Y direction.
            wait: Time in seconds to wait at the beginning of a scan.
            If wait == None, will wait 3 * time const of lockin.
        '''
        self.fast_axis = fast_axis

        # Check if points in the scan are within the voltage limits of
        # Piezos
        for i in range(self.X.shape[0]):
            self.piezos.x.check_lim(self.X[i, :])
            self.piezos.y.check_lim(self.Y[i, :])
            self.piezos.z.check_lim(self.Z[i, :])

        # Loop over Y values if fast_axis is x,
        # Loop over X values if fast_axis is y
        # Print a warning if the fast_axis has fewer points than the slow.
        def slow_axis_alert():
            print('Slow axis has more points than fast axis!')
            import winsound
            winsound.Beep(int(440*2**(1/2)),200) # play a tone
            winsound.Beep(440,200) # play a tone

        if fast_axis == 'x':
            num_lines = int(self.X.shape[0])  # loop over Y
            if num_lines > int(self.X.shape[1]):  # if more Y points than X
                slow_axis_alert()
        elif fast_axis == 'y':
            num_lines = int(self.X.shape[1])  # loop over X
            if num_lines > int(self.X.shape[0]):  # if more X points than Y
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

            if not self.montana.check_status(): # returns False if problem
                self.piezos.zero()
                self.squidarray.zero()
                self.atto.z.move(-1000)
                raise Exception('Montana error!')

            # If we detected a keyboard interrupt stop the scan here
            # The DAQ is not in use at this point so ending the scan
            # should be safe.
            if self.interrupt:
                break
            k = 0
            if self.raster:
                if i % 2 == 0:  # if even
                    # k keeps track of sweeping forward vs. backwards
                    k = 0
                else:  # if odd
                    k = -1
            # if not rastering, k=0, meaning always forward sweeps

            # Starting and ending piezo voltages for the line
            # for forward, starts at 0,i; backward: -1, i
            if fast_axis == 'x':
                Vstart = {'x': self.X[i, k],
                          'y': self.Y[i, k],
                          'z': self.Z[i, k]}
                # for forward, ends at -1,i; backward: 0, i
                Vend = {'x': self.X[i, -(k + 1)],
                        'y': self.Y[i, -(k + 1)],
                        'z': self.Z[i, -(k + 1)]}
            elif fast_axis == 'y':
                # for forward, starts at i,0; backward: i,-1
                Vstart = {'x': self.X[k, i],
                          'y': self.Y[k, i],
                          'z': self.Z[k, i]}
                # for forward, ends at i,-1; backward: i,0
                Vend = {'x': self.X[-(k + 1), i],
                        'y': self.Y[-(k + 1), i],
                        'z': self.Z[-(k + 1), i]}

            # Go to first point of scan
            self.piezos.sweep(self.piezos.V, Vstart)
            #self.squidarray.reset()
            if wait is None:
                wait = 3*self.lockin_squid.time_constant
            time.sleep(wait)

            # Begin the sweep
            output_data, received = self.piezos.sweep(Vstart, Vend,
                                          chan_in=self._daq_inputs,
                                          sweep_rate=self.scan_rate
                                          )
            # Flip the backwards sweeps
            if k == -1:  # flip only the backwards sweeps
                for d in output_data, received:
                    for key, value in d.items():
                        d[key] = value[::-1]  # flip the 1D array

            # Back off with the Z piezo before moving to the next line
            self.piezos.z.V = 0
            self.squidarray.reset()

            # Interpolate to the number of lines
            self.Vfull['piezo'] = output_data[fast_axis]
            if fast_axis == 'x':
                self.Vinterp['piezo'] = self.X[i, :]
            elif fast_axis == 'y':
                self.Vinterp['piezo'] = self.Y[:, i]

            # Store this line's signals for Vdc, Vac x/y, and Cap
            # Sometimes the daq doesn't return the right keys
            # Using try/except to try to diagnose for the future.
            for chan in self._daq_inputs:
                try:
                    self.Vfull[chan] = received[chan]
                except Exception as e:
                    print(received)
                    raise e

            # Convert from DAQ volts to lockin volts where applicable
            for chan in ['acx', 'acy']:
                self.Vfull[chan] = self.lockin_squid.convert_output(
                    self.Vfull[chan])
            self.Vfull['cap'] = self.lockin_cap.convert_output(
                self.Vfull['cap']) - Vcap_offset

            # Interpolate the data and store in the 2D arrays
            for chan in self._daq_inputs:
                if fast_axis == 'x':
                    self.Vinterp[chan] = interp1d(
                        self.Vfull['piezo'],
                        self.Vfull[chan])(self.Vinterp['piezo']
                                          )
                    self.V[chan][i, :] = self.Vinterp[chan]
                else:
                    self.Vinterp[chan] = interp1d(
                        self.Vfull['piezo'],
                        self.Vfull[chan])(self.Vinterp['piezo']
                                          )
                    self.V[chan][:, i] = self.Vinterp[chan]

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
            data_nan = np.array(self.V[chan] * self._conversions[chan],
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

        # Do not flush events for inline or notebook backends
        if using_notebook_backend():
            return

        self.fig.canvas.flush_events()

    def setup_plots(self):
        '''
        Set up all plots.
        '''
        # Use the aspect ratio of the image set subplot size.
        # The aspect ratio is Xspan/Yspan
        aspect = self.span[0] / self.span[1]
        numplots = 4
        # If X is longer than Y we want 2 columns of wide plots
        if aspect > 1:
            num_row = int(np.ceil(numplots / 2))
            num_col = 2
            width = 14
            # Add 1 to height for title/axis labels
            height = min(width, width / aspect) + 1
        # If Y is longer than X we want 2 rows of tall plots
        else:
            num_row = 2
            num_col = int(np.ceil(numplots / 2))
            height = 10
            # Pad the plots for the colorbars/axis labels
            width = min(height, height * aspect) + 4

        self.fig, self.axes = plt.subplots(num_row,
                                           num_col,
                                           figsize=(width, height))
        self.fig_cuts, self.axes_cuts = plt.subplots(4, 1, figsize=(6, 8),
                                                     sharex=True)
        # Convert the axis numpy arrays to list so they aren't saved as data.
        self.axes = list(self.axes.flatten())
        self.axes_cuts = list(self.axes_cuts.flatten())
        cmaps = ['RdBu',
                 'afmhot',
                 'magma',
                 'magma']
        clabels = ['DC Flux ($\Phi_0$)',
                   'Capacitance (fF)',
                   'AC X ($\Phi_0$)',
                   'AC Y ($\Phi_0$)']

        self.im = AttrDict()
        self.cbars = AttrDict()
        self.lines_full = AttrDict()
        self.lines_interp = AttrDict()

        # Plot the DC signal, capactitance and AC signal on 2D colorplots
        for ax, chan, cmap, clabel in zip(self.axes,
                                          self._daq_inputs,
                                          cmaps,
                                          clabels):
            # Convert None in data to NaN
            nan_data = np.array(self.V[chan] * self._conversions[chan])
            # Create masked array where data is NaN
            masked_data = np.ma.masked_where(np.isnan(nan_data), nan_data)

            # Plot masked data on the appropriate axis with imshow
            image = ax.imshow(masked_data, cmap=cmap, origin='lower',
                              extent = extents(self.X, self.Y))

            # Create a colorbar that matches the image height
            d = make_axes_locatable(ax)
            cax = d.append_axes('right', size=0.1, pad=0.1)
            cbar = plt.colorbar(image, cax=cax)
            cbar.set_label(clabel, rotation=270, labelpad=12)
            cbar.formatter.set_powerlimits((-2, 2))
            self.im[chan] = image
            self.cbars[chan] = cbar

            # Label the axes - including a timestamp
            ax.set_xlabel('X Position (V)')
            ax.set_ylabel('Y Position (V)')
            title = ax.set_title(self.timestamp, size='medium', y=1.02)
            # If the title intersects the exponent label from the colorbar
            # shift the title up and center it

            # ROI
            if self.ROI is not None:
                # make closed path of coordinates
                xy = [[self.ROI[0], self.ROI[2]],
                      [self.ROI[1], self.ROI[2]],
                      [self.ROI[1], self.ROI[3]],
                      [self.ROI[0], self.ROI[3]],
                      [self.ROI[0], self.ROI[2]],
                      ]
                p = matplotlib.patches.Polygon(xy)
                c = matplotlib.collections.PatchCollection([p], facecolors=['none'], edgecolors=['k'])
                ax.add_collection(c)

        # Plot the last linecut for DC, AC and capacitance signals
        for ax, chan, clabel in zip(self.axes_cuts,
                                    self._daq_inputs,
                                    clabels):
            # ax.plot returns a list containing the line
            # Take the line object - not the list containing the line
            self.lines_full[chan] = ax.plot(self.Vfull['piezo'],
                                            self.Vfull[chan],
                                            '-')[0]
            self.lines_interp[chan] = ax.plot(self.Vinterp['piezo'],
                                              self.Vinterp[chan], 'ok',
                                              markersize=3)[0]
            ax.set_ylabel(clabel)
            # Scientific notation for <10^-2, >10^2
            ax.yaxis.get_major_formatter().set_powerlimits((-2, 2))
        # Label the X axis of only the bottom plot
        self.axes_cuts[-1].set_xlabel('Position (V)')
        # Title the top plot with the timestamp
        self.axes_cuts[0].set_title(self.timestamp, size='medium')

        # Adjust subplot layout so all labels are visible
        # First call tight layout to prevent axis label overlap.
        self.fig.tight_layout()
        self.fig_cuts.tight_layout()

        # Show the (now empty) figures
        self.fig.canvas.draw()
        self.fig_cuts.canvas.draw()

    def plot_line(self):
        '''
        Update the data in the linecut plot.

        '''
        clabels = ['DC Flux ($\Phi_o$)',
                   'Capacitance (F)',
                   'AC X ($\Phi_o$)',
                   'AC Y ($\Phi_o$)']
        for ax, chan, clabel in zip(self.axes_cuts, self._daq_inputs, clabels):
            # Update X and Y data for the 'full data'
            self.lines_full[chan].set_xdata(self.Vfull['piezo'])
            self.lines_full[chan].set_ydata(self.Vfull[chan] *
                                            self._conversions[chan])
            # Update X and Y data for the interpolated data
            self.lines_interp[chan].set_xdata(self.Vfull['piezo'])
            self.lines_interp[chan].set_ydata(self.Vfull[chan] *
                                              self._conversions[chan])
            # Rescale axes for newly plotted data
            ax.relim()
            ax.autoscale_view()
        # Update the figure
        self.fig_cuts.canvas.draw()

        # Do not flush events for inline or notebook backends
        if using_notebook_backend():
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
        super().save(appendedpath='lines')
