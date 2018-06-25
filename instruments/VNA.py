import visa
import numpy as np
import time
import math
from .instrument import Instrument
from .keithley import Keithley2400
import matplotlib.pyplot as plt

class VNA8722ES(Instrument):
    _label = 'VNA_ES'
    '''Instrument driver for HP 8722ES Vector Network Analyzer'''
# TODO: more safety precautions re: VNA source power and amplifier/squid limitations
    _power_state = None
    _power = None

    _networkparam = None  # which network parameter: 'S11' 'S21' 'S12' 'S22'
    _savemode = None  # e.g. FORM4
    _sweepmode = None
    _freqmin = None
    _freqmax = None
    _numpoints = None

    _averaging_state = None
    _averaging_factor = None

    _smoothing_state = None
    _smoothing_factor = None

    # TODO: fix all @property things: should query then set and return etc.
    # TODO: need to change preset: dangerous to have it jump to -10dB with source power with preset command
    def __init__(self, gpib_address=16):
        # FIXME: is gpib_address always going to be 16?
        # FIXME: need to initialize other attributes too
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address, read_termination='a')
        self._visa_handle.read_termination = '\n'

        self.write('SOUP OFF;')  # immediately turn power off and set to -75
        self._power_state = 0
        self.write('PWRRPMAN')  # power range manual
        self.write('POWR11')  # manually change to power range 11
        self.write('POWE -75')
        self._power = -75

        self.write('S21')  # set to measure transmission forward
        self._networkparam = 'S21'
        self._sweepmode = 'LINFREQ'
        self._freqmin = .05e9
        self._freqmax = 40.05e9
        self._numpoints = 201
        self._averaging_state = 0
        self._averaging_factor = 16

        self._smoothing_state = 1 # smoothing on
        self._smoothing_factor = 3  # 3% smoothing '

        self.write('FORM4')
        self._savemode = 'FORM4'

        print ("init: power off and at -75dB. Measuring S21. Most other settings factory preset.")

    def factory_preset(self):
        '''Set vna to factory preset. Dangerous because default is -10dBm with power on.'''
        self.write('OPC?;PRES;')
        print('Set to factory preset')

    def __getstate__(self):
        self._save_dict = {
        'power state': self._power_state,
        'power': self._power,
        'sweep mode': self._sweepmode,
        'min of frequency sweep': self._freqmin,
        'max of frequency sweep': self._freqmax,
        'number of frequency points': self._numpoints,
        'averaging state': self._averaging_state,
        'averaging factor': self._averaging_factor
        }
        return self._save_dict

        # TODO: should something else be implemented?
    def __setstate__(self, state):
        pass

    @property
    def powerstate(self):
        '''Get whether power is on/off 1/0'''
        return self._power_state

    @powerstate.setter
    def powerstate(self, value):
        '''Set power to on/off 1/0'''
        val = int(value)
        assert val in [1,0], "powerstate must be 1 or 0"
        if val == 1:
            self.write('SOUP1')
            print('Turning on VNA source power')
        else:
            self.write('SOUP0')
            print('Powering down VNA')
        self._power_state = val

    @property
    def power(self):
        '''Get the power (dBm)'''
        return float(self.ask('POWE?'))

    @power.setter
    def power(self, value):
        '''Set the power (dBm)'''
        assert type(value) is float or int
        if value > -10 or value < -80:
            raise Exception('Power should be between -10 and -80 dBm')
        rangenum = min(math.floor((-value + 5)/5), 11)
        self.write('POWR%d' %rangenum)  # first change power range
        self.write('POWE %f' % value)  # then can change power
        self._power = value

    @property
    def sweepmode(self):
        '''
        Get the sweep mode
        '''
        options = {
        "": "LIN",
        "": "LOG",
        "": "LIST",
        "": "POWER",
        "": "CW"
        }
        if self.ask('LINFREQ?') == str(1):
            return "LIN"
        elif self.ask('LOGFREQ?') == str(1):
            return "LOG"
        elif self.ask('LISFREQ?') == str(1):
            return "LIST"
        else:
            raise Exception('Driver can only handle linear, log, list sweeps')

    @sweepmode.setter
    def sweepmode(self, value):
        '''
        Set the sweep mode
        '''
        if value == 'LIN':
            value = 'LINFREQ'
        elif value == 'LOG':
            value = 'LOGFREQ'
        elif value == 'LIST':
            value = 'LISTFREQ'
        else:
            raise Exception('Driver currently only handles linear, log, list')
        self.write(value)
        self._sweepmode = value
        # Check stuff here

    @property
    def minfreq(self):
        '''
        Get the min frequency
        '''
        return float(self.ask('STAR?'))

    @minfreq.setter
    def minfreq(self, value):
        '''
        Set min frequency
        '''
        assert type(value) is float or int, "frequency must be float or int"
        if value > self.maxfreq:
            raise Exception('Min frequency cannot be greater than stop frequency')
        self.write('STAR %f' % value)
        self._minfreq = value

    @property
    def maxfreq(self):
        '''Get the stop frequency'''
        return float(self.ask('STOP?'))

    @maxfreq.setter
    def maxfreq(self, value):
        '''Set max frequency'''
        assert type(value) is float or int, "frequency must be float or int"
        if value < self.minfreq:
            raise Exception('Max frequency cannot be smaller than min frequency')
        self._maxfreq = value
        self.write('STOP %f' % value)

    @property
    def numpoints(self):
        '''Get the number of points in sweep'''
        return float(self.ask('POIN?'))

    @numpoints.setter
    def numpoints(self, value):
        '''Set the number of points in sweep (and wait for clean sweep)'''
        vals = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert value in vals, "must be in " + str(vals)
        self.write('OPC?;POIN %f;' %value)
        self._numpoints = value

    @property
    def averaging_state(self):
        '''Get averaging state (on/off 1/0)'''
        return int(self.ask('AVERO?'))

    @averaging_state.setter
    def averaging_state(self, value):
        '''Set averaging to on/off 1/0'''
        val = int(value)
        if val == 1:
            self.write('AVEROON')
        elif val == 0:
            self.write('AVEROOFF')
        else:
            print('Must set to on/off 1/0')
        self._averaging_state = value

    @property
    def averaging_factor(self):
        '''Get averaging factor'''
        return int(float(self.ask('AVERFACT?')))

    @averaging_factor.setter
    def averaging_factor(self, value):
        '''Set averaging factor, in [0, 999]'''
        assert isinstance(value, int) and value >= 0 and value <= 999, "Averaging factor should be int in [0, 999]"
        self.write('AVERFACT%s' % value)

    def averaging_restart(self):
        '''Restart the measurement averaging'''
        self.write('AVERREST')

    @property
    def smoothing_state(self):
        '''Get smoothing state'''
        return self._smoothing_state

    @smoothing_state.setter
    def smoothing_state(self, value):
        '''Set smoothing to on/off 1/0'''
        val = int(value)
        assert val in [1, 0], "smoothing state should be 1 or 0 on/off"
        self.write('SMOOO%d' %val)
        self._smoothing_state = val

    @property
    def smoothing_factor(self):
        '''Get smoothing factor'''
        self._smoothing_factor = float(self.ask('SMOOAPER?'))
        return self._smoothing_factor

    @smoothing_factor.setter
    def smoothing_factor(self, value):
        '''Set smoothing factor'''
        assert value >=.05 and value <20, "value must be between .05 and 20 (%)"
        self.write('SMOOAPER %f' %value)
        self._smoothing_factor = value

    @property
    def networkparam(self):
        '''Get which network parameter is being measured'''
        if self.ask('S11') == '1':
            return 'S11'
        elif self.ask('S21') == '1':
            return 'S21'
        elif self.ask('S12') == '1':
            return 'S12'
        elif self.ask('S22') == '1':
            return 'S22'

    @networkparam.setter
    def networkparam(self, value):
        nplist = ['S11', 'S21', 'S12', 'S22']
        assert value in nplist, "Network parameter should be one of " + str(nplist)
        if value == 'S12' or value == 'S22':
            raise Exception('Don\'t send current thru amplifer the backwards (just for cold amplifer testing, remove this in code if needed)')
        self.write(value)

    def save(self):
        '''Save data as array'''
        self.write('FORM4')  # Prepare to output correct data format
        self.write('SMIC')  # Use this format so can get both real and imaginary
        sleep_length = float(self.ask('SWET?'))*(self.averaging_factor+3)
        time.sleep(sleep_length)  # wait for averaging

        rm = visa.ResourceManager()
        secondary = rm.get_instrument('GPIB0::16')
        secondary.write('OUTPFORM')
        s = secondary.read(termination='~')
        s = s.split('\n')
        n_ar = np.empty((self._numpoints, 2))
        for i in range(len(s)):
            splot = s[i].split(',')
            Re = float(splot[0])
            Im = float(splot[1])
            dB = 20*math.log10(math.sqrt(Re**2+Im**2))
            try:
                phase = math.atan(Im/Re)
            except ZeroDivisionError:
                phase = math.pi/2
            n_ar[i][0] = dB
            n_ar[i][1] = phase
        self.write('LOGM')  # switch back to log magnitude format
        return n_ar

    def savelog(self):
        '''Save dB data in array'''
        self.write('FORM4')  # Prepare to output correct data format
        self.write('LOGM')
        sleep_length = float(self.ask('SWET?'))*(self.averaging_factor+3)
        time.sleep(sleep_length)  # wait for averaging

        rm = visa.ResourceManager()
        '''Important: not actually initializing another instance of this class because that
        would temporarily set power too high when goes to factory reset.'''
        secondary = rm.get_instrument('GPIB0::16')
        secondary.write('OUTPFORM')
        s = secondary.read(termination='~')
        s = s.split('\n')
        n_ar = np.empty((self._numpoints, 2))
        for i in range(len(s)):
            splot = s[i].split(',')
            dB = float(splot[0])
            # _ = float(splot[1])  # don't actually know what this is, manual says units N/s^2 ?
            n_ar[i][0] = dB
            n_ar[i][1] = 0  # just empty for now. May change later
        return n_ar

    def savephase(self):
        '''Save phase data in array'''
        self.write('FORM4')
        self.write('PHASE')
        sleep_length = float(self.ask('SWET?'))*(self.averaging_factor+3)
        time.sleep(sleep_length)

        rm = visa.ResourceManager()
        secondary = rm.get_instrument('GPIB0::16')
        secondary.write('OUTPFORM')
        s = secondary.read(termination='~')
        s = s.split('\n')
        n_ar = np.empty((self._numpoints, 2))
        for i in range(len(s)):
            splot = s[i].split(',')
            phase = float(splot[0])
            n_ar[i][0] = phase
            n_ar[i][1] = 0  # just empty for now. May change later
        self.write('LOGM')  # switch back to log mag format for viewing
        return n_ar


    def rfsquid_sweep_I(self, k_Istart, k_Istop, k_Isteps, v_freqmin, v_freqmax, v_power, v_averaging_factor, v_numpoints, mode, v_smoothing_state=1,
        v_smoothing_factor=1.5):
        '''Frequency and current sweep (i.e. keithley sources current, as opposed to sourcing voltage)'''
        # mode 0: only dB. mode 1: only phase. mode 2: dB and phase.

        assert k_Istart < k_Istop, "stop voltage should be greater than start voltage"
        assert v_power <= -65, "Don't send to much power to SQUID"
        valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert v_numpoints in valid_numpoints, "number of points must be in " + str(valid_numpoints)

        # Set up current source
        k3 = Keithley2400(24)
        k3.output = 'on'
        k3.source = 'I'
        time.sleep(1)  # FIXME this is clumsy way of making sure keithley has enough time to turn on
        k3.Iout_range = 20e-3  # 20 mA range # TODO: figure out what exactly range is
        k3.Iout = 0
        k3.V_compliance = 21  # 21 volt compliance

        # Set up VNA
        self.networkparam = 'S21'  # Set to measure forward transmission
        self.power = v_power
        self.powerstate = 1  # turn vna source power on
        self.averaging_state = 1  # Turn averaging on
        self.averaging_factor = v_averaging_factor # Set averaging factor
        self.minfreq = v_freqmin  # set sweep range
        self.maxfreq = v_freqmax
        self.numpoints = v_numpoints  # set number of points in frequency sweep
        self.smoothing_state = 1  # turn smoothing on
        self.smoothing_factor = 1.5  # set smoothing factor. # TODO: have this as parameter, not hardcoded

        sleep_length = float(self.ask('SWET?'))*(self.averaging_factor+3)
        estimated_runtime = sleep_length*k_Isteps
        print('Minimum estimated runtime: '+ str(int(estimated_runtime)/60) + ' minutes')

        I_stepsize = (float(k_Istop-k_Istart))/k_Isteps
        print('Incrementing current in step sizes of ', str(I_stepsize*1000) + ' milliamps')
        arr = np.zeros((int(self.numpoints), 2, 1))  # array for values. depth d is d'th current step

        for step in range(0, k_Isteps):
            if step % 10 == 0:
                print("Current source step #" + str(step+1) + " out of " + str(k_Isteps))
            if step == 1:
                arr = np.delete(arr, (0), axis=2)
            k3.Iout = k3.Iout + I_stepsize  # increment voltage
            self.averaging_restart()  # restart averaging
            if mode == 0:
                temp = self.savelog()  # just save dB data
            if mode == 1:
                temp = self.savephase()  # just save phase data
            if mode == 2:
                # save both dB and phase data
                temp = self.savelog() + np.flip(self.savephase(), axis=1)
            arr = np.dstack((arr, temp))  # waiting occurs in save() function


        k3.Iout = 0
        k3.output = 'off'  # turn off keithley output
        self.powerstate = 0  # turn off VNA source power
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
            # start, stop, power
            plt.savefig(savestring, bbox_inches="tight")
            plt.show()  # TODO: figure out how to make it stay showing on notebook? if not, not a problem because can just save
            plt.close()
            print("Finished, saved png as " + savestring)
        # fig.savefig('filename here')
        # colorbar stuff add later
        # cbar.ax.set_ylabel(cbarlabel='some cbarlabel', rotation=-90, va="bottom")
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

    def rfsquid_sweep_V(self, k_Vstart, k_Vstop, k_Vsteps, v_freqmin, v_freqmax, v_power, v_averaging_factor, v_numpoints, mode):
        # mode 0: only dB. mode 1: only phase. mode 2: dB and phase.


        assert k_Vstart < k_Vstop, "stop voltage should be greater than start voltage"
        assert v_power <= -65, "Don't send to much power to SQUID"
        valid_numpoints = [3, 11, 21, 26, 51, 101, 201, 401, 801, 1601]
        assert v_numpoints in valid_numpoints, "number of points must be in " + str(valid_numpoints)
        # Set up current source

        # set up voltage source
        k3 = Keithley2400(24)
        k3.output = 'on'
        k3.source = 'V'
        k3.Vout_range = 20
        k3.Vout = k_Vstart
        k3.I_compliance = 20e-3  # current compliance

        # Set up VNA
        self.networkparam = 'S21'  # Set to measure forward transmission
        self.power = v_power
        self.powerstate = 1  # turn vna source power on
        self.averaging_state = 1  # Turn averaging on
        self.averaging_factor = v_averaging_factor # Set averaging factor
        self.minfreq = v_freqmin# set sweep range
        self.maxfreq = v_freqmax
        self.numpoints = v_numpoints
        self.smoothing_state = 1
        self.smoothing_factor = 1.5

        sleep_length = float(self.ask('SWET?'))*(self.averaging_factor+3)
        estimated_runtime = sleep_length*k_Vsteps
        print('Minimum estimated runtime: '+ str(int(estimated_runtime))/60 + ' minutes')

        V_stepsize = (float(k_Vstop-k_Vstart))/k_Vsteps
        print('Incrementing voltage in step sizes of ', str(V_stepsize) + ' volts')
        arr = np.zeros((int(self.numpoints), 2, 1))  # array for values. depth d is d'th current step

        for step in range(0, k_Vsteps):
            print("starting voltage source step #" + str(step+1) + " out of " + str(k_Vsteps) + ".")
            print('source voltage:' + str(k3.Vout))
            print('measured current:' + str(k3.I) + ' amps')
            if step == 1:
                arr = np.delete(arr, (0), axis=2)

            self.averaging_restart()  # restart averaging
            if mode == 0:
                temp = self.savelog()  # just save dB data
            if mode == 1:
                temp = self.savephase()  # just save phase data
            if mode == 2:
                # save both dB and phase data
                temp = self.savelog() + np.flip(self.savephase(), axis=1)
            arr = np.dstack((arr, temp))  # waiting occurs in save() function
            k3.Vout = k3.Vout + V_stepsize  # increment voltage

        k3.Vout = 0
        k3.output = 'off'  # turn off keithley output
        self.powerstate = 0  # turn off VNA source power
        # TODO: real-time plotting?
        if mode == 2:
            print('not prepared to show this yet: just need to do subplot thing')
            plt.subplot(211)
            plt.imshow(arr[:, 0, :], aspect='auto')
            plt.colorbar()
            plt.subplot(212)
            plt.imshow(arr[:, 1, :], aspect='auto')
            plt.colorbar()
            plt.show()
        else:

            plt.subplot(111)
            plt.imshow(arr[:, 0, :], aspect='auto')
            plt.colorbar()
            plt.show()
        # fig.savefig('filename here')
        # colorbar stuff add later
        # cbar.ax.set_ylabel(cbarlabel='some cbarlabel', rotation=-90, va="bottom")

        return arr

    def ask(self, msg, tryagain=True):
        try:
            return self._visa_handle.query(msg)  # changed from .ask to .query
        except Exception as e:
            print('Communication error with VNA: ')
            print(e)
            self.close()
            self.__init__(self.gpib_address)
            if tryagain:
                self.ask(msg, False)

    def write(self, msg):
        self._visa_handle.write(msg)

    def close(self):
        self._visa_handle.close()
        del(self._visa_handle)
