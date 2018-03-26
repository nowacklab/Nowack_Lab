import time, os, matplotlib, matplotlib.pyplot as plt, numpy as np
from scipy.interpolate import interp1d

from ..Utilities import conversions
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict
from ..Utilities.plotting.plot_mpl import extents

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


    def plot_update(self):
        '''
        Update the data for all plots.
        '''
        # Update the line plot as well.
        self.plot_line()

        # Iterate over the color plots and update data with new line
        for chan in self._daq_inputs:
            # Convert None in data to NaN
            data = np.array(self.V[chan] * self._conversions[chan],
                                dtype=np.float)
            self.update_image(self.im[chan], data)


    def setup_plots(self):
        '''
        Set up all plots.
        '''

        # Use the aspect ratio of the image set subplot size.
        # The aspect ratio is Xspan/Yspan
        aspect = self.span[0] / self.span[1]
        numplots = len(self._daq_inputs)

        # If X is longer than Y, we want 2 columns of wide plots
        if aspect > 1:
            num_row = int(np.ceil(numplots / 2))
            num_col = 2
            width = 14
            height = width/aspect + 1  # +1 for title/axis labels
        # If Y is longer than X we want 2 rows of tall plots
        else:
            num_row = 2
            num_col = int(np.ceil(numplots / 2))
            height = 10
            width = height*aspect + 4  # pad for colorbars/axis labels

        # Make axis dicts, with daq input channels as keys.
        self.fig = plt.figure(figsize=(width,height))
        self.fig_cuts = plt.figure(figsize=(6,8))
        self.ax = AttrDict()
        self.ax_cuts = AttrDict()
        for i, chan in enumerate(self._daq_inputs):
            # Populate axes in the figure.
            self.ax[chan] = self.fig.add_subplot(num_row, num_col, i+1)
            self.ax_cuts[chan] = self.fig_cuts.add_subplot(
                                                len(self._daq_inputs), 1, i+1)

        # Determine colormaps and labels for each channel.
        cmaps = AttrDict(dc='RdBu', cap='afmhot', acx='magma', acy='magma')
        clabels = AttrDict(
            dc = 'DC Flux ($\Phi_0$)',
            cap = 'Capacitance (fF)',
            acx = 'AC X ($\Phi_0$)',
            acy = 'AC Y ($\Phi_0$)',
        )

        self.im = AttrDict()
        self.lines_full = AttrDict()
        self.lines_interp = AttrDict()

        for chan in self._daq_inputs:
            ax = self.ax[chan]

            # Plot the DC signal, capactitance and AC signal on 2D colorplots
            # Plot masked data on the appropriate axis with imshow
            # self.V[chan] as initialized is just a 2D array of nans.
            image = ax.imshow(self.V[chan], cmap=cmaps[chan], origin="lower",
                              extent = extents(self.X, self.Y))
            self.im[chan] = image
            self.add_colorbar(ax, label=clabels[chan])

            # Label the axes - including a timestamp
            ax.set_xlabel("X Position (V)")
            ax.set_ylabel("Y Position (V)")
            title = ax.set_title(self.timestamp, size=10, y=1.02)

            # Plot the last linecut for DC, AC and capacitance signals
            ax = self.ax_cuts[chan]

            # ax.plot returns a list containing the line
            # Take the line object - not the list containing the line
            self.lines_full[chan] = ax.plot(np.nan, np.nan, '-')[0]
            self.lines_interp[chan] = ax.plot(np.nan, np.nan, 'ok', ms=3)[0]
            ax.set_ylabel(clabels[chan])

            # Scientific notation for <10^-2, >10^2
            ax.yaxis.get_major_formatter().set_powerlimits((-2,2))

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

        # Label the X axis of only the bottom plot
        self.ax_cuts[self._daq_inputs[-1]].set_xlabel("Position (V)")
        # Title the top plot with the timestamp
        self.ax_cuts[self._daq_inputs[0]].set_title(self.timestamp, size=10)

        # Adjust subplot layout so all labels are visible
        # First call tight layout to prevent axis label overlap.
        self.fig.tight_layout()
        self.fig_cuts.tight_layout()

        # Update plots with actual data
        self.plot()


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

    def save(self, appendedpath='lines', **kwargs):
        super().save(appendedpath=appendedpath, **kwargs)
