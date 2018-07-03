# Some of these imports may not be used (same imports as squidIV2)
import numpy as np
import matplotlib.pyplot as plt
from importlib import reload
from scipy.interpolate import UnivariateSpline
from ..Utilities.plotting import plot_mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.signal import savgol_filter

# Nowack_Lab imports
import Nowack_Lab.Utilities.save
reload(Nowack_Lab.Utilities.save)
from Nowack_Lab.Utilities.save import Measurement
import Nowack_Lab.Utilities.dataset
from Nowack_Lab.Utilities.dataset import Dataset
from Nowack_Lab.Instruments import VNA8722ES
from Nowack_Lab.Instruments import Keithley2400

class WithoutDAQ_ThreeParam_Sweep):
    '''Sweep field coil current and measured frequency using VNA and keithley2400'''
    def __init__(self):
        pass

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()

    def plot(self):
        pass

    def _do(self, i, j):
        pass

    def _sweeptopt(self):
        pass

    def do(self):
        pass

    @staticmethod
    def plot_lines():
        pass

    @staticmethod
    def plot_color_diff(obj, ax):
        pass

    @staticmethod
    def plot_color():
        pass

    @staticmethod
    def plot_color_gradient():
        pass

    @staticmethod
    def plot_color_absgradient():
        pass

    @staticmethod
    def plot_fastmod():
        pass

    @staticmethod
    def plot_amplitude():
        pass

class RF_sweep_current(WithoutDAQ_ThreeParam_Sweep):
    ''' At different current steps, measure frequency response
    Using class SQUID_Mod_FastIV(ThreeParam_Sweep) as example'''
    instrument_list = ['VNA', 'keithley']  # probably not necessary

    # _XLABEL = r'$I_{squid}$ ($\mu A$)'
    # _YLABEL = r'$Frequency_{squid}$ ($\mu Hz$)'

    def __init__(self, instruments = [],
                k_Istart, k_Istop, k_Isteps,
                v_freqmin, v_freqmax, v_power, v_avg_factor, v_numpoints, mode,
                v_smoothing_state=0, v_smoothing_factor=1):
        # mode 0: only dB. mode 1: only phase. mode 2: dB and phase.
        super().__init__(instruments=instruments)  # no daq stuff

        assert self.k_Istart < k_Istop, "stop voltage should be greater than start voltage"
        assert self.v_power <= -65, "Don't send too much power to SQUID"
        valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert self.v_numpoints in self.valid_numpoints, "number of points must be in " + str(valid_numpoints)

        self.k3 = Keithley2400(24)  # initialize current source (Instrument object)
        self.v1 = VNA8722ES(16)  # initialize VNA (Instrument object)

        self.arr_1 = None  # store an array to plot
        self.arr_2 = None  # store an array to plot

    def do(self, hysteresis=False, plot=False):
        '''
        Run measurement
        Arguments:
            hysteresis (boolean): sweep current up and down?
            plot (boolean): should I plot?
        '''
        # TODO: implement hysteresis (back) sweep
        # TODO: is this plotting stuff very different from just calling pyplot functions?
        assert not hysteresis, "Hysteretic measurement not implemented yet"

        # Set up current source settings
        if(self.k3.output == 'off'):
            self.k3.output = 'on'
        self.k3.source = 'I'
        time.sleep(3)  # FIXME this is clumsy way of making sure keithley has enough time to turn on
        self.k3.Iout_range = 20e-3  # 20 mA range # TODO: figure out what exactly range is
        self.k3.Iout = 0
        self.k3.V_compliance = 21  # 21 volt compliance

        # Set up VNA settings
        self.v1.networkparam = 'S21'  # Set to measure forward transmission
        self.v1.power = v_power
        self.v1.powerstate = 1  # turn vna source power on
        self.v1.averaging_state = 1  # Turn averaging on
        self.v1.averaging_factor = v_averaging_factor # Set averaging factor
        self.v1.minfreq = v_freqmin  # set sweep range
        self.v1.maxfreq = v_freqmax
        self.v1.numpoints = v_numpoints  # set number of points in frequency sweep
        self.v1.smoothing_state = v_smoothing_state  # turn smoothing on
        self.v1.smoothing_factor = v_smoothing_factor  # set smoothing factor

        if hysteresis:
            sleep_length = float(self.v1.ask('SWET?'))*(self.v1.averaging_factor+3)
            estimated_runtime = sleep_length*k_Isteps*2
            print('Minimum estimated runtime: '+ str(int(estimated_runtime/60)) + ' minutes')

            I_stepsize = (float(k_Istop-k_Istart))/k_Isteps
            print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')

            arr_up = np.zeros((int(self.v1.numpoints), 2, 1))  # array for values. depth d is d'th current step

            # Stepping up the current from k_Istar to k_Istop
            for step in range(0, k_Isteps):
                if step % 10 == 0:
                    print("Current source step " + str(step+1) + " out of " + str(2*k_Isteps))
                if step == 1:
                    arr_up = np.delete(arr_up, (0), axis=2)
                self.k3.Iout = self.k3.Iout + I_stepsize  # increment current
                self.v1.averaging_restart()  # restart VNA averaging
                if mode == 0:
                    temp = self.v1.savelog()  # just save dB data
                if mode == 1:
                    temp = self.v1.savephase()  # just save phase data
                if mode == 2:
                    # save both dB and phase data
                    temp = self.v1.savelog() + np.flip(self.v1.savephase(), axis=1)
                arr_up = np.dstack((arr_up, temp))  # waiting occurs in save() function

            # Now, stepping down the current from k_Istop down to k_Istart
            arr_down = np.zeros((int(self.v1.numpoints), 2, 1))  # array for values. depth d is d'th current step
            for step in range(0, k_Isteps):
                if step % 10 == 0:
                    print("current source step " + str(step+1+k_Isteps) + " out of " + str(2*k_Isteps))
                k3.Iout = k3.Iout - I_stepsize  # step down current one step
                self.v1.averaging_restart()
                if mode == 0:
                    temp = self.v1.savelog()
                if mode == 1:
                    temp = self.v1.savephase()
                if mode == 2:
                    # wave both dB and phase data
                    temp = self.v1.savelog() + np.flip(self.v1.savephase(), axis=1)
                arr_down = np.dstack((arr_down, temp))

            self.k3.Iout = 0
            self.k3.output = 'off'  # turn off keithley output
            self.v1.powerstate = 0  # turn off VNA source power
            # TODO: real-time plotting?
            if mode == 2:
                print('not prepared to show this yet: just need to do subplot thing')

                fig, (mag_ax, phase_ax) = plt.subplots(2, sharey=True)
                mag_ax.imshow(arr[:, 0, :], aspect='auto')
                mag_ax.colorbar()
                phase_ax.imshow(arr[:, 1, :], aspect='auto')
                phase_ax.colorbar()
                savestring = " magnitude_and_phase" + str(k_Istart)
                plt.savefig
                plt.show()

                plt.subplot(211)
                plt.imshow(arr[:, 0, :], aspect='auto')
                plt.colorbar()
                plt.subplot(212)
                plt.imshow(arr[:, 1, :], aspect='auto')
                plt.colorbar()
                plt.show()
            elif mode == 0:  # attenuation mode
                # first, plot the stepping up current run
                plt.subplot(211)
                plt.imshow(arr_up[:, 0, :], aspect='auto', extent=[k_Istart, k_Istop, v_freqmin, v_freqmax])
                cbar = plt.colorbar()
                cbar.ax.set_title('Attenuation (dB)')  # redundant?
                savestring = "Iup" + str(k_Istart) + "_" + str(k_Istop) + "_" + str(k_Isteps) + "_" + str(v_power) + "_" + str(int(time.time())) + ".png"
                plt.title(savestring)
                plt.savefig(savestring, bbox_inches="tight")
                np.save(savestring, arr_down) #save data???
                plt.show()  # TODO: figure out how to make it stay showing on notebook? if not, not a problem because can just save
                plt.close()

                # second, plot the stepping down current run
                plt.subplot(212)
                plt.imshow(arr_down[:,0,:-1], aspect=;'auto', extent=[k_Istart, k_Istop, v_freqmin, v_freqmax])
                cbar = plt.colorbar()
                cbar.ax.set_title('Attenuation (dB)')  # redundant?
                savestring = "Idown" + str(k_Istart) + "_" + str(k_Istop) + "_" + str(k_Isteps) + "_" + str(v_power) + "_" + str(int(time.time())) + ".png"
                plt.title(savestring)
                plt.savefig(savestring, bbox_inches="tight")
                np.save(savestring, arr_down) #save data??????
                plt.show()
                plt.close()

                print("Finished, saved pngs as [Iup/Idown]" + savestring)

                self.arr_1 = arr_up
                self.arr_2 = arr_down
                return np.dstack((arr_up, arr_down))

            elif mode == 1:
                plt.subplot(111)
                plt.imshow(arr[:, 0, :], aspect='auto', extent=[k_Istart, k_Istop, v_freqmin, v_freqmax])
                cbar = plt.colorbar()
                cbar.ax.set_title('phase shift (degrees)')
                savestring = str(k_Istart) + "_" + str(k_Istop) + "_" + str(k_Isteps) + "_" + str(v_power) + "_" + str(int(time.time())) + ".png"
                # start, stop, power
                plt.savefig(savestring, bbox_inches="tight")
                plt.show()  # TODO: figure out how to make it stay showing on notebook? if not, not a problem because can just save
                plt.close()
                print("Finished, saved png as " + savestring)
                return arr

        else: # i.e. not hysteresis mode
            sleep_length = float(self.v1.ask('SWET?'))*(self.v1.averaging_factor+3)
            estimated_runtime = sleep_length*k_Isteps
            print('Minimum estimated runtime: '+ str(int(estimated_runtime/60)) + ' minutes')

            I_stepsize = (float(k_Istop-k_Istart))/k_Isteps
            print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')
            arr = np.zeros((int(self.v1.numpoints), 2, 1))  # array for values. depth d is d'th current step

            for step in range(0, k_Isteps):
                if step % 10 == 0:
                    print("Current source step #" + str(step+1) + " out of " + str(k_Isteps))
                if step == 1:
                    arr = np.delete(arr, (0), axis=2)
                self.k3.Iout = self.k3.Iout + I_stepsize  # increment voltage
                self.v1.averaging_restart()  # restart averaging
                if mode == 0:
                    temp = self.v1.savelog()  # just save dB data
                if mode == 1:
                    temp = self.v1.savephase()  # just save phase data
                if mode == 2:
                    # save both dB and phase data
                    temp = self.v1.savelog() + np.flip(self.v1.savephase(), axis=1)
                arr = np.dstack((arr, temp))  # waiting occurs in save() function

            self.k3.Iout = 0
            self.k3.output = 'off'  # turn off keithley output
            self.v1.powerstate = 0  # turn off VNA source power

            # TODO: real-time update plotting?

            # Old plotting function, trying to change to better one
            if mode == 2:
                print('not prepared to show this yet: just need to do subplot thing')

                fig, (mag_ax, phase_ax) = plt.subplots(2, sharey=True)
                mag_ax.imshow(arr[:, 0, :], aspect='auto')
                mag_ax.colorbar()
                phase_ax.imshow(arr[:, 1, :], aspect='auto')
                phase_ax.colorbar()
                savestring = " magnitude_and_phase" + str(k_Istart)
                plt.savefig
                plt.show()

                plt.subplot(211)
                plt.imshow(arr[:, 0, :], aspect='auto')
                plt.colorbar()
                plt.subplot(212)
                plt.imshow(arr[:, 1, :], aspect='auto')
                plt.colorbar()
                plt.show()
            elif mode == 0:  # attenuation mode

                plt.subplot(111)
                plt.imshow(arr[:, 0, :], aspect='auto', extent=[k_Istart, k_Istop, v_freqmin, v_freqmax])
                cbar = plt.colorbar()
                cbar.ax.set_title('Attenuation (dB)')
                savestring = str(k_Istart) + "_" + str(k_Istop) + "_" + str(k_Isteps) + "_" + str(v_power) + "_" + str(int(time.time())) + ".png"
                plt.title(savestring)
                # start, stop, power
                plt.savefig(savestring, bbox_inches="tight")
                plt.show()  # TODO: figure out how to make it stay showing on notebook? if not, not a problem because can just save
                plt.close()
                np.save(savestring, arr) #save data??????
                print("Finished, saved png as " + savestring)
                return arr
            elif mode == 1:
                plt.subplot(111)
                plt.imshow(arr[:, 0, :], aspect='auto', extent=[k_Istart, k_Istop, v_freqmin, v_freqmax])
                cbar = plt.colorbar()
                cbar.ax.set_title('phase shift (degrees)')
                savestring = str(k_Istart) + "_" + str(k_Istop) + "_" + str(k_Isteps) + "_" + str(v_power) + "_" + str(int(time.time())) + ".png"
                # start, stop, power
                plt.savefig(savestring, bbox_inches="tight")
                plt.show()  # TODO: figure out how to make it stay showing on notebook? if not, not a problem because can just save
                plt.close()
                print("Finished, saved png as " + savestring)
                return arr


    def setup_plots(self):
        self.fig, self.ax = plt.subplots(1,2, figsize=(16,6))
        self.ax = list(self.ax)

    def plot(self):
        raise NotImplementedError('"plot" function in other programs uses daq; VNA does not have analog output--> not using daq. Use plot2() instead')
        assert self.arr_1 not None and self.arr_2 not None, "both arr_1 and arr_2 should have arrays"
        self.ax[0], cbar = RF_sweep_current.plot_color(
                                            self.ax[0],
                                            [],
                                            [],
                                            self.arr_up[:,0,:]


                                            cmap='viridis'
                                            )
        pass

        def plot2(self):
        # TODO: change to make 2 subplots if hysteresis is true, 1 subplot if false (up and down)
        # Change name
        # Plot 2 subplots: magnitude and phase
        self.fig, self.ax = plt.subplots(1, 2, figsize=(16, 6))
        self.ax = list(self.ax)

        z_ar_log = v1.savelog()  # TODO: change when starting to use Re, Im from smith chart
        z_ar_phase = v1.savephase()
        self.ax[0], cbar = self.plot_color(self.ax[0], [k_Istart, k_Istop], [v_freqmin, v_freqmax]0, z_ar_log[:, 0, :])
        self.ax[0].set_xlabel('field coil current (amps)')
        self.ax[0].set_ylabel('frequency (Hz)')
        cbar.set_label('')
        # TODO: Unfinished here, looking at squidIV2.py as guide

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        plt.pause(.01)

    def save_data(self):
        data = dataset(self)


    @staticmethod
    def plot_color(ax, xaxis, yaxis, z, cmap='viridis'):
        im = ax.imshow(z, cmap, origin='lower',
                        extent=(xaxis[0], xaxis[-1], yaxis[0], yaxis[-1]),
                        aspect='auto')
        d = make_axes_locatable(ax)
        cax = d.append_axes('right', size=.1, pad=.1)
        cbar = plt.colorbar(im, cax=cax)

        return [ax, cbar]
