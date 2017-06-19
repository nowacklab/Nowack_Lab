"""
Zurich Instruments LabOne Python API Example

Demonstrate how to perform a simple frequency sweep using the ziDAQSweeper
class/Sweeper Module.
"""

# Copyright 2016 Zurich Instruments AG

from __future__ import print_function
import time
from .instrument import Instrument
import numpy as np
import zhinst.utils

class HF2LI(Instrument):
    ''' Testy test test test test'''

    _label = 'Zurich HF2LI'

    # Create Zurich HF2LI object, either using passed serial number or
    # autodetect.
    def __init__(self, server_address = 'localhost', server_port = 8005 , device_serial = ''):
        # Open a connection to the ziDAQServer (HF2LI must be powered on)
        self.daq = zhinst.ziPython.ziDAQServer(server_address, server_port)
        # Detect device
        deviceList = zhinst.utils.devices(self.daq)
        result = ''
        if device_serial in deviceList :
            self.device_id = device_serial
            result = 'Using Zurich HF2LI with serial %s' % self.device_id
        elif device_serial != '' :
            self.device_id = zhinst.utils.autoDetect(self.daq)
            result ='Requested device not found. Using %s' % self.device_id
        else:
            self.device_id = zhinst.utils.autoDetect(self.daq)
        print(result)

    def freq_sweep(self, freq_start, freq_stop, num_steps, time_constant = 1e-3,
                 amplitude = .1, outputchan = 1, inputchan = 1, couple = 'ac',
                 settleTCs = 10, avgTCs = 5, do_plot=False):
        """
        Sweeps frequency of chosen oscillator, while recording chosen input.

        Citation: Adapted from Zurich Instruments' "sweep" example.

        Arguments:

          freq_start (float): start frequency of sweep in hz

          freq_end (float): stop frequency of sweep in hz

          num_steps (int): number of frequency steps to perform

          time_constant (float): demod timeconstant

          amplitude (float, optional): The amplitude to set on the signal output.

          inputchan (int, optional): input channel (1 or 2)

          outputchan (int, optional): output channel (1 or 2)

          couple (string, optional): ac couple if str = 'ac', o.w. dc couple

          settleTCs (int, optional): number of time constants to allow demod to
            stabilize after sweep.

          avgTCs (int, optional): number of time constants to average demod
            output for data point.

          do_plot (bool, optional): Specify whether to plot the sweep.
           Default is no plot output.

        Returns:

          sample (list of dict): A list of demodulator sample dictionaries. Each
            entry in the list correspond to the result of a single sweep and is a
            dict containing a demodulator sample.

        Raises:

          RuntimeError: If the device is not "discoverable" from the API.

        See the "LabOne Programing Manual" for further help, available:
          - On Windows via the Start-Menu:
            Programs -> Zurich Instruments -> Documentation
          - On Linux in the LabOne .tar.gz archive in the "Documentation"
            sub-folder.

        """

        apilevel_example = 5  # The API level supported by this example.
        # Call a zhinst utility function that returns:
        # - an API session `daq` in order to communicate with devices via the data server.
        # - the device ID string that specifies the device branch in the server's node hierarchy.
        # - the device's discovery properties.
        err_msg = "This example only supports instruments with demodulators."

        # Create a base instrument configuration: disable all outputs, demods and scopes.
        general_setting = [['/%s/demods/*/enable' % self.device_id, 0],
                           ['/%s/demods/*/trigger' % self.device_id, 0],
                           ['/%s/sigouts/*/enables/*' % self.device_id, 0],
                           ['/%s/scopes/*/enable' % self.device_id, 0]]
        self.daq.set(general_setting)
        # Perform a global synchronisation between the device and the data server:
        # Ensure that the settings have taken effect on the device before setting
        # the next configuration.
        self.daq.sync()

        # Now configure the instrument for this experiment. The following channels
        # and indices work on all device configurations. The values below may be
        # changed if the instrument has multiple input/output channels and/or either
        # the Multifrequency or Multidemodulator options installed.
        out_channel = outputchan - 1
        in_channel = inputchan - 1
        demod_index = 0
        osc_index = outputchan-1
        demod_rate = 10e3
        out_mixer_channel = int(self.daq.listNodes('/%s/sigouts/%d/amplitudes/' % (self.device_id, out_channel),0)[1])
        if couple == 'ac':
            acUse = 1
        else:
            acUse = 0
        exp_setting = [['/%s/sigins/%d/ac'             % (self.device_id, in_channel), acUse],
                       ['/%s/sigins/%d/range'          % (self.device_id, in_channel), 2*amplitude],
                       ['/%s/demods/%d/enable'         % (self.device_id, demod_index), 1],
                       ['/%s/demods/%d/rate'           % (self.device_id, demod_index), demod_rate],
                       ['/%s/demods/%d/adcselect'      % (self.device_id, demod_index), in_channel],
                       ['/%s/demods/%d/order'          % (self.device_id, demod_index), 4],
                       ['/%s/demods/%d/timeconstant'   % (self.device_id, demod_index), time_constant],
                       ['/%s/demods/%d/oscselect'      % (self.device_id, demod_index), osc_index],
                       ['/%s/demods/%d/harmonic'       % (self.device_id, demod_index), 1],
                       ['/%s/sigouts/%d/on'            % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/enables/%d'    % (self.device_id, out_channel, out_mixer_channel), 1],
                       ['/%s/sigouts/%d/range'         % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/amplitudes/%d' % (self.device_id, out_channel, out_mixer_channel), amplitude],
                       ['/%s/sigins/%d/diff'           % (self.device_id, in_channel), 0],
                       ['/%s/sigouts/%d/add'           % (self.device_id, out_channel), 0],
                       ]
        # Some other device-type dependent configuration may be required. For
        # example, disable the signal inputs `diff` and the signal outputs `add` for
        # HF2 instruments.
        self.daq.set(exp_setting)

        # Create an instance of the Sweeper Module (ziDAQSweeper class).
        sweeper = self.daq.sweep()

        # Configure the Sweeper Module's parameters.
        # Set the device that will be used for the sweep - this parameter must be set.
        sweeper.set('sweep/device', self.device_id)
        # Specify the `gridnode`: The instrument node that we will sweep, the device
        # setting corresponding to this node path will be changed by the sweeper.
        sweeper.set('sweep/gridnode', 'oscs/%d/freq' % osc_index)
        # Set the `start` and `stop` values of the gridnode value interval we will use in the sweep.
        sweeper.set('sweep/start', freq_start)
        sweeper.set('sweep/stop', freq_stop)
        # Set the number of points to use for the sweep, the number of gridnode
        # setting values will use in the interval (`start`, `stop`)
        sweeper.set('sweep/samplecount', num_steps)
        # Specify logarithmic spacing for the values in the sweep interval.
        sweeper.set('sweep/xmapping', 1)
        # Automatically control the demodulator bandwidth/time constants used.
        # 0=manual, 1=fixed, 2=auto
        # Note: to use manual and fixed, sweep/bandwidth has to be set to a value > 0.
        sweeper.set('sweep/bandwidthcontrol', 0)
        # Sets the bandwidth overlap mode (default 0). If enabled, the bandwidth of
        # a sweep point may overlap with the frequency of neighboring sweep
        # points. The effective bandwidth is only limited by the maximal bandwidth
        # setting and omega suppression. As a result, the bandwidth is independent
        # of the number of sweep points. For frequency response analysis bandwidth
        # overlap should be enabled to achieve maximal sweep speed (default: 0). 0 =
        # Disable, 1 = Enable.
        sweeper.set('sweep/bandwidthoverlap', 0)

        # Sequential scanning mode (as opposed to binary or bidirectional).
        sweeper.set('sweep/scan', 0)
        # Specify the number of sweeps to perform back-to-back.
        loopcount = 1
        sweeper.set('sweep/loopcount', loopcount)
        # We don't require a fixed sweep/settling/time since there is no DUT
        # involved in this example's setup (only a simple feedback cable), so we set
        # this to zero. We need only wait for the filter response to settle,
        # specified via sweep/settling/inaccuracy.
        sweeper.set('sweep/settling/time', settleTCs*time_constant)
        # The sweep/settling/inaccuracy' parameter defines the settling time the
        # sweeper should wait before changing a sweep parameter and recording the next
        # sweep data point. The settling time is calculated from the specified
        # proportion of a step response function that should remain. The value
        # provided here, 0.001, is appropriate for fast and reasonably accurate
        # amplitude measurements. For precise noise measurements it should be set to
        # ~100n.
        # Note: The actual time the sweeper waits before recording data is the maximum
        # time specified by sweep/settling/time and defined by
        # sweep/settling/inaccuracy.
        sweeper.set('sweep/settling/inaccuracy', 0.001)
        # Set the minimum time to record and average data to 10 demodulator
        # filter time constants.
        sweeper.set('sweep/averaging/tc', avgTCs)
        # Minimal number of samples that we want to record and average is 100. Note,
        # the number of samples used for averaging will be the maximum number of
        # samples specified by either sweep/averaging/tc or sweep/averaging/sample.
        sweeper.set('sweep/averaging/sample', 10)

        # Now subscribe to the nodes from which data will be recorded. Note, this is
        # not the subscribe from ziDAQServer; it is a Module subscribe. The Sweeper
        # Module needs to subscribe to the nodes it will return data for.x
        path = '/%s/demods/%d/sample' % (self.device_id, demod_index)
        sweeper.subscribe(path)

        # Start the Sweeper's thread.
        sweeper.execute()

        start = time.time()
        timeout = 60  # [s]
        print("Will perform", loopcount, "sweeps...")
        while not sweeper.finished():  # Wait until the sweep is complete, with timeout.
            time.sleep(0.2)
            progress = sweeper.progress()
            print("Individual sweep progress: {:.2%}.".format(progress[0]), end="\r")
            # Here we could read intermediate data via:
            # data = sweeper.read(True)...
            # and process it while the sweep is completing.
            # if device in data:
            # ...
            if (time.time() - start) > timeout:
                # If for some reason the sweep is blocking, force the end of the
                # measurement.
                print("\nSweep still not finished, forcing finish...")
                sweeper.finish()
        print("")

        # Read the sweep data. This command can also be executed whilst sweeping
        # (before finished() is True), in this case sweep data up to that time point
        # is returned. It's still necessary still need to issue read() at the end to
        # fetch the rest.
        return_flat_dict = True
        data = sweeper.read(return_flat_dict)
        sweeper.unsubscribe(path)

        # Stop the sweeper thread and clear the memory.
        sweeper.clear()

        # Check the dictionary returned is non-empty.
        assert data, "read() returned an empty data dictionary, did you subscribe to any paths?"
        # Note: data could be empty if no data arrived, e.g., if the demods were
        # disabled or had rate 0.
        assert path in data, "No sweep data in data dictionary: it has no key '%s'" % path
        samples = data[path]
        print("Returned sweeper data contains", len(samples), "sweeps.")
        assert len(samples) == loopcount, \
            "The sweeper returned an unexpected number of sweeps: `%d`. Expected: `%d`." % (len(samples), loopcount)

        if do_plot:
            import matplotlib.pyplot as plt
            plt.clf()
            for i in range(0, len(samples)):
                frequency = samples[i][0]['frequency']
                R = np.abs(samples[i][0]['x'] + 1j*samples[i][0]['y'])
                phi = np.angle(samples[i][0]['x'] + 1j*samples[i][0]['y'])
                plt.subplot(2, 1, 1)
                plt.semilogx(frequency, R)
                plt.subplot(2, 1, 2)
                plt.semilogx(frequency, phi)
            plt.subplot(2, 1, 1)
            plt.title('Results of %d sweeps.' % len(samples))
            plt.grid(True)
            plt.ylabel(r'Demodulator R ($V_\mathrm{RMS}$)')
            plt.ylim(0.0, 0.1)
            plt.subplot(2, 1, 2)
            plt.grid(True)
            plt.xlabel('Frequency ($Hz$)')
            plt.ylabel(r'Demodulator Phi (radians)')
            plt.autoscale()
            plt.draw()
            plt.show()

        return samples

    def aux_sweep(self, aux_start, aux_stop, num_steps, time_constant = 1e-3,
                 amplitude = .01, freq = 200,  auxchan = 1, outputchan = 1, inputchan = 1,
                 couple = 'ac', settleTCs = 10, avgTCs = 5, do_plot=False):
        """
        Sweeps the output of an aux channel, while recording chosen input.
        If the goal is to do a DC biased lock in measurement (i.e. AC Rds vs
        Vds), auxchan should be connected to "add" of outputchan.

        Citation: Adapted from Zurich Instruments' "sweep" example.

        Arguments:

          aux_start (float): start voltage of the sweep in volts

          aux_stop (float): stop voltage of the sweep in volts

          num_steps (int): number of frequency steps to perform

          time_constant (float, optional): demod timeconstant

          amplitude (float, optional): The amplitude to set on the signal output.

          freq (float, optional): the frequency of the lock in measurement. If
              ac couple is enabled (default), it must be greater than 100 hz
              (corner of ac highpass).

          auxchan (int, optional): input channel (1 or 2)

          outputchan (int, optional): output channel (1 or 2)

          inputchan (int, optional): input channel (1 or 2)

          couple (string, optional): ac couple if str = 'ac', o.w. dc couple

          settleTCs (int, optional): number of time constants to allow demod to
            stabilize after sweep.

          avgTCs (int, optional): number of time constants to average demod
            output for data point.

          do_plot (bool, optional): Specify whether to plot the sweep.
           Default is no plot output.

        Returns:

          sample (list of dict): A list of demodulator sample dictionaries. Each
            entry in the list correspond to the result of a single sweep and is a
            dict containing a demodulator sample.

        Raises:

          RuntimeError: If the device is not "discoverable" from the API.

        See the "LabOne Programing Manual" for further help, available:
          - On Windows via the Start-Menu:
            Programs -> Zurich Instruments -> Documentation
          - On Linux in the LabOne .tar.gz archive in the "Documentation"
            sub-folder.

        """

        apilevel_example = 5  # The API level supported by this example.
        # Call a zhinst utility function that returns:
        # - an API session `daq` in order to communicate with devices via the data server.
        # - the device ID string that specifies the device branch in the server's node hierarchy.
        # - the device's discovery properties.
        err_msg = "This example only supports instruments with demodulators."

        # Create a base instrument configuration: disable all outputs, demods and scopes.
        general_setting = [['/%s/demods/*/enable' % self.device_id, 0],
                           ['/%s/demods/*/trigger' % self.device_id, 0],
                           ['/%s/sigouts/*/enables/*' % self.device_id, 0],
                           ['/%s/scopes/*/enable' % self.device_id, 0]]
        self.daq.set(general_setting)
        # Perform a global synchronisation between the device and the data server:
        # Ensure that the settings have taken effect on the device before setting
        # the next configuration.
        self.daq.sync()

        # Now configure the instrument for this experiment. The following channels
        # and indices work on all device configurations. The values below may be
        # changed if the instrument has multiple input/output channels and/or either
        # the Multifrequency or Multidemodulator options installed.
        out_channel = outputchan - 1
        in_channel = inputchan - 1
        aux_channel = auxchan - 1
        demod_index = 0
        osc_index = outputchan-1
        out_mixer_channel = int(self.daq.listNodes('/%s/sigouts/%d/amplitudes/' % (self.device_id, out_channel),0)[1])
        demod_rate = 10e3
        if couple == 'ac':
            acUse = 1
        else:
            acUse = 0
        exp_setting = [['/%s/sigins/%d/ac'             % (self.device_id, in_channel), acUse],
                       ['/%s/sigins/%d/range'          % (self.device_id, in_channel), 2*amplitude],
                       ['/%s/sigins/%d/diff'           % (self.device_id, in_channel), 0],
                       ['/%s/demods/%d/enable'         % (self.device_id, demod_index), 1],
                       ['/%s/demods/%d/rate'           % (self.device_id, demod_index), demod_rate],
                       ['/%s/demods/%d/adcselect'      % (self.device_id, demod_index), in_channel],
                       ['/%s/demods/%d/order'          % (self.device_id, demod_index), 4],
                       ['/%s/demods/%d/timeconstant'   % (self.device_id, demod_index), time_constant],
                       ['/%s/demods/%d/oscselect'      % (self.device_id, demod_index), osc_index],
                       ['/%s/demods/%d/harmonic'       % (self.device_id, demod_index), 1],
                       ['/%s/sigouts/%d/on'            % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/enables/%d'    % (self.device_id, out_channel, out_mixer_channel), 1],
                       ['/%s/sigouts/%d/range'         % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/add'           % (self.device_id, out_channel), 1],
                       ['/%s/sigouts/%d/amplitudes/%d' % (self.device_id, out_channel, out_mixer_channel), amplitude],
                       ['/%s/auxouts/%d/outputselect'  % (self.device_id, aux_channel),-1]
                      ]
        self.daq.set(exp_setting)

        # Create an instance of the Sweeper Module (ziDAQSweeper class).
        sweeper = self.daq.sweep()

        # Configure the Sweeper Module's parameters.
        # Set the device that will be used for the sweep - this parameter must be set.
        sweeper.set('sweep/device', self.device_id)
        # Specify the `gridnode`: The instrument node that we will sweep, the device
        # setting corresponding to this node path will be changed by the sweeper.
        sweeper.set('sweep/gridnode', '/%s/auxouts/%d/offset' % (self.device_id,aux_channel))
        # Set the `start` and `stop` values of the gridnode value interval we will use in the sweep.
        sweeper.set('sweep/start', aux_start)
        sweeper.set('sweep/stop', aux_stop)
        # Set the number of points to use for the sweep, the number of gridnode
        # setting values will use in the interval (`start`, `stop`)
        sweeper.set('sweep/samplecount', num_steps)
        # Specify logarithmic spacing for the values in the sweep interval.
        sweeper.set('sweep/xmapping', 1)
        # Automatically control the demodulator bandwidth/time constants used.
        # 0=manual, 1=fixed, 2=auto
        # Note: to use manual and fixed, sweep/bandwidth has to be set to a value > 0.
        sweeper.set('sweep/bandwidthcontrol', 0)
        # Sets the bandwidth overlap mode (default 0). If enabled, the bandwidth of
        # a sweep point may overlap with the frequency of neighboring sweep
        # points. The effective bandwidth is only limited by the maximal bandwidth
        # setting and omega suppression. As a result, the bandwidth is independent
        # of the number of sweep points. For frequency response analysis bandwidth
        # overlap should be enabled to achieve maximal sweep speed (default: 0). 0 =
        # Disable, 1 = Enable.
        sweeper.set('sweep/bandwidthoverlap', 0)

        # Sequential scanning mode (as opposed to binary or bidirectional).
        sweeper.set('sweep/scan', 0)
        # Specify the number of sweeps to perform back-to-back.
        loopcount = 1
        sweeper.set('sweep/loopcount', loopcount)
        # We don't require a fixed sweep/settling/time since there is no DUT
        # involved in this example's setup (only a simple feedback cable), so we set
        # this to zero. We need only wait for the filter response to settle,
        # specified via sweep/settling/inaccuracy.
        sweeper.set('sweep/settling/time', settleTCs*time_constant)
        # The sweep/settling/inaccuracy' parameter defines the settling time the
        # sweeper should wait before changing a sweep parameter and recording the next
        # sweep data point. The settling time is calculated from the specified
        # proportion of a step response function that should remain. The value
        # provided here, 0.001, is appropriate for fast and reasonably accurate
        # amplitude measurements. For precise noise measurements it should be set to
        # ~100n.
        # Note: The actual time the sweeper waits before recording data is the maximum
        # time specified by sweep/settling/time and defined by
        # sweep/settling/inaccuracy.
        sweeper.set('sweep/settling/inaccuracy', 0.001)
        # Set the minimum time to record and average data to 10 demodulator
        # filter time constants.
        sweeper.set('sweep/averaging/tc', avgTCs)
        # Minimal number of samples that we want to record and average is 100. Note,
        # the number of samples used for averaging will be the maximum number of
        # samples specified by either sweep/averaging/tc or sweep/averaging/sample.
        sweeper.set('sweep/averaging/sample', 10)

        # Now subscribe to the nodes from which data will be recorded. Note, this is
        # not the subscribe from ziDAQServer; it is a Module subscribe. The Sweeper
        # Module needs to subscribe to the nodes it will return data for.x
        path = '/%s/demods/%d/sample' % (self.device_id, demod_index)
        sweeper.subscribe(path)

        # Start the Sweeper's thread.
        sweeper.execute()

        start = time.time()
        timeout = 60  # [s]
        print("Will perform", loopcount, "sweeps...")
        while not sweeper.finished():  # Wait until the sweep is complete, with timeout.
            time.sleep(0.2)
            progress = sweeper.progress()
            print("Individual sweep progress: {:.2%}.".format(progress[0]), end="\r")
            # Here we could read intermediate data via:
            # data = sweeper.read(True)...
            # and process it while the sweep is completing.
            # if device in data:
            # ...
            if (time.time() - start) > timeout:
                # If for some reason the sweep is blocking, force the end of the
                # measurement.
                print("\nSweep still not finished, forcing finish...")
                sweeper.finish()
        print("")

        # Read the sweep data. This command can also be executed whilst sweeping
        # (before finished() is True), in this case sweep data up to that time point
        # is returned. It's still necessary still need to issue read() at the end to
        # fetch the rest.
        return_flat_dict = True
        data = sweeper.read(return_flat_dict)
        sweeper.unsubscribe(path)

        # Stop the sweeper thread and clear the memory.
        sweeper.clear()

        # Check the dictionary returned is non-empty.
        assert data, "read() returned an empty data dictionary, did you subscribe to any paths?"
        # Note: data could be empty if no data arrived, e.g., if the demods were
        # disabled or had rate 0.
        assert path in data, "No sweep data in data dictionary: it has no key '%s'" % path
        samples = data[path]
        print("Returned sweeper data contains", len(samples), "sweeps.")
        assert len(samples) == loopcount, \
            "The sweeper returned an unexpected number of sweeps: `%d`. Expected: `%d`." % (len(samples), loopcount)

        if do_plot:
            import matplotlib.pyplot as plt
            plt.clf()
            for i in range(0, len(samples)):
                frequency = samples[i][0]['frequency']
                R = np.abs(samples[i][0]['x'] + 1j*samples[i][0]['y'])
                phi = np.angle(samples[i][0]['x'] + 1j*samples[i][0]['y'])
                plt.subplot(2, 1, 1)
                plt.semilogx(frequency, R)
                plt.subplot(2, 1, 2)
                plt.semilogx(frequency, phi)
            plt.subplot(2, 1, 1)
            plt.title('Results of %d sweeps.' % len(samples))
            plt.grid(True)
            plt.ylabel(r'Demodulator R ($V_\mathrm{RMS}$)')
            plt.ylim(0.0, 0.1)
            plt.subplot(2, 1, 2)
            plt.grid(True)
            plt.xlabel('Frequency ($Hz$)')
            plt.ylabel(r'Demodulator Phi (radians)')
            plt.autoscale()
            plt.draw()
            plt.show()

        return samples
