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
from Nowack_Lab.Instruments import VNA8722ES
from Nowack_Lab.Instruments import Keithley2400

class RF_sweep_current(Measurement):
    ''' At different current steps, measure frequency response '''
    instrument_list = ['VNA', 'keithley']

    _XLABEL = r'$I_{squid}$ ($\mu A$)'
    _YLABEL = r'$Frequency_{squid}$ ($\mu Hz$)'

    def __init__(self, instruments = {},
                k_Istart, k_Istop, k_Isteps,
                v_freqmin, v_freqmax, v_power, v_avg_factor, v_numpoints, mode,
                v_smoothing_state=0, v_smoothing_factor=1):
        # mode 0: only dB. mode 1: only phase. mode 2: dB and phase.
        super().__init__(instruments=instruments)

        assert k_Istart < k_Istop, "stop voltage should be greater than start voltage"
        assert v_power <= -65, "Don't send to much power to SQUID"
        valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert v_numpoints in valid_numpoints, "number of points must be in " + str(valid_numpoints)

        k3 = Keithley2400(24)  # initialize current source (Instrument object)
        v1 = VNA8722ES(16)  # initialize VNA (Instrument object)


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
        k3.output = 'on'
        k3.source = 'I'
        time.sleep(1)  # FIXME this is clumsy way of making sure keithley has enough time to turn on
        k3.Iout_range = 20e-3  # 20 mA range # TODO: figure out what exactly range is
        k3.Iout = 0
        k3.V_compliance = 21  # 21 volt compliance

        # Set up VNA settings
        v3.networkparam = 'S21'  # Set to measure forward transmission
        v3.power = v_power
        v3.powerstate = 1  # turn vna source power on
        v3.averaging_state = 1  # Turn averaging on
        v3.averaging_factor = v_averaging_factor # Set averaging factor
        v3.minfreq = v_freqmin  # set sweep range
        v3.maxfreq = v_freqmax
        v3.numpoints = v_numpoints  # set number of points in frequency sweep
        v3.smoothing_state = v_smoothing_state  # turn smoothing on
        v3.smoothing_factor = v_smoothing_factor  # set smoothing factor

        if hysteresis:
            sleep_length = float(v3.ask('SWET?'))*(v3.averaging_factor+3)
            estimated_runtime = sleep_length*k_Isteps*2
            print('Minimum estimated runtime: '+ str(int(estimated_runtime/60)) + ' minutes')

            I_stepsize = (float(k_Istop-k_Istart))/k_Isteps
            print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')

            arr = np.zeros((int(v3.numpoints), 2, 1))  # array for values. depth d is d'th current step

            # step up
            for step in range(0, k_Isteps):
                if step % 10 == 0:
                    print("Current source step " + str(step+1) + " out of " + str(2*k_Isteps))
                if step == 1:
                    arr = np.delete(arr, (0), axis=2)
                k3.Iout = k3.Iout + I_stepsize  # increment current
                v3.averaging_restart()  # restart VNA averaging
                if mode == 0:
                    temp = v3.savelog()  # just save dB data
                if mode == 1:
                    temp = v3.savephase()  # just save phase data
                if mode == 2:
                    # save both dB and phase data
                    temp = v3.savelog() + np.flip(v3.savephase(), axis=1)
                arr = np.dstack((arr, temp))  # waiting occurs in save() function
            for step in range(0, k_Isteps):
                if step % 10 == 0:
                    print("current source step " + str(step+1+k_Isteps) + " out of " + str(2*k_Isteps))
                k3.Iout = k3.Iout - I_stepsize  # step down current
                v3.averaging_restart()  # restart VNA averaging
                if mode == 0:
                    temp = v3.savelog()
                if mode == 1:
                    temp = v3.svaephase()
                if mode == 2:
                    # wave both dB and phase data
                    temp = v3.savelog() + np.flip(v3.savephase(), axis=1)
                arr = np.dstack((arr, temp))  # waiting occurs in save() function
                
            k3.Iout = 0
            k3.output = 'off'  # turn off keithley output
            v3.powerstate = 0  # turn off VNA source power
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

        else: # i.e. not hysteresis mode
            sleep_length = float(v3.ask('SWET?'))*(v3.averaging_factor+3)
            estimated_runtime = sleep_length*k_Isteps
            print('Minimum estimated runtime: '+ str(int(estimated_runtime/60)) + ' minutes')

            I_stepsize = (float(k_Istop-k_Istart))/k_Isteps
            print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')
            arr = np.zeros((int(v3.numpoints), 2, 1))  # array for values. depth d is d'th current step

            for step in range(0, k_Isteps):
                if step % 10 == 0:
                    print("Current source step #" + str(step+1) + " out of " + str(k_Isteps))
                if step == 1:
                    arr = np.delete(arr, (0), axis=2)
                k3.Iout = k3.Iout + I_stepsize  # increment voltage
                v3.averaging_restart()  # restart averaging
                if mode == 0:
                    temp = v3.savelog()  # just save dB data
                if mode == 1:
                    temp = v3.savephase()  # just save phase data
                if mode == 2:
                    # save both dB and phase data
                    temp = v3.savelog() + np.flip(v3.savephase(), axis=1)
                arr = np.dstack((arr, temp))  # waiting occurs in save() function

            k3.Iout = 0
            k3.output = 'off'  # turn off keithley output
            v3.powerstate = 0  # turn off VNA source power
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

    def plot(self, hysteresis=True):
        super().plot()
        self.ax.plot()
