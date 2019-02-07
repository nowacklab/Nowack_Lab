import numpy as np
from scipy.interpolate import interp1d
from ..Utilities.logging import log
from .instrument import Instrument
import time
try:
    import PyDAQmx as mx
except:
    print('PyDAQmx not imported in piezos.py!')

class Piezos(Instrument):
    '''
    Piezo benders on the scanner.
    Signal sent to NIDAQ goes through Nanonis HVA4 High Voltage Amplifier.
    Sweeps between voltages smoothly.
    '''
    _label = 'piezos'
    # DAQ channel labels expected by this class
    _daq_outputs = ['x','y','z']
    _piezos = ['x','y','z']
    _gain = [40, 40, 40]
    # maximum allowed total voltage across piezo
    _Vmax = [400, 400, 400]
    # multiplier for whether piezos are biased +V/-V or not.
    _bipolar = [2, 2, 2]
    _V = {}
    _daq = None
    _max_sweep_rate = 180 # Vpiezo/s
    _max_step_size = 0.2 #Vpiezo = 0.0025 Vdaq * 2 * 40, assuming these are typical values for bipolar and gain.
                        # 0.0025 V is approximately the resolution of the daq, so it doesn't make sense to go much slower than that.
                        # 0.2 is a nice number

    def __init__(self, daq=None, zero = False):
        '''
        e.g. pz = piezos.Piezos(daq=daq, zero = True)
            daq: the nidaq.NIDAQ() object
            zero: whether to zero the daq or not
        '''
        self._daq = daq
        if daq is None:
            print('Daq not loaded... piezos will not work until you give them a daq!')
        for ch in self._daq_outputs:
            if ch not in daq.outputs:
                raise Exception('Need to set daq channel outputs! Need a %s' %ch)

        for (i,p) in enumerate(self._piezos):
            setattr(self, p, Piezo(self._daq, label=p,
                                    gain = self._gain[i], Vmax=self._Vmax[i],
                                    bipolar = self._bipolar[i],
                                max_sweep_rate = self._max_sweep_rate,
                                max_step_size=self._max_step_size))
                                # makes benders x, y, and z

        #self.checkHVAStatus()

        if zero:
            self.zero()

    def __getstate__(self):
        self._save_dict = {"x": self.x,
                            "y": self.y,
                            "z": self.z,
                            "daq": self._daq,
                            "max sweep rate": self._max_sweep_rate,
                            "max step size": self._max_step_size
                            }
        return self._save_dict


    def __setstate__(self, state):
        state.pop('daq') # don't want to load the daq automatically
        state['_max_sweep_rate'] = state.pop('max sweep rate')
        state['_max_step_size'] = state.pop('max step size')
        self.__dict__.update(state)
        # print('Daq not loaded in piezos! Load with load_daq(daq)!')


    @property
    def V(self):
        '''
        Voltage property. Set and read any number of piezo voltages.
            pz.V
            pz.V = {'z':150, 'y':100}
            pz.V = 0 will zero all piezos
        '''
        for p in self._piezos:
            self._V[p] = getattr(self,p).V
        return self._V

    @V.setter
    def V(self, value):
        if np.isscalar(value):
            value = {k: value for k in self._piezos}

        for k in value.keys():
            getattr(self,k).check_lim(value[k])
        # Sweep to the desired voltage
        self.sweep(self.V, value)
        # Store the desired voltage
        for key in self._piezos:
            try:
                self._V[key] = value[key]
            except:
                pass


    def load_daq(self, daq):
        '''
        If piezos object loaded without a daq, give it a daq.
        '''
        self._daq = daq
        for p in self._piezos:
            getattr(self,p)._daq = daq


    def sweep(self, Vstart, Vend, chan_in=None, sweep_rate=180, meas_rate=900
               trigger = 'False'):
        '''
        Sweeps piezos from a starting voltage (dictionary) to an ending voltage
         (dictionary).
         specify the channels you want to monitor as a list
         Maximum allowed step size will be the step size for the piezo that has
         to sweep over the largest voltage range.
         Maximum step size set at 0.2 Vpiezo by default for class.
         Piezo sweep rate limited to 180 V/s when not scanning, 120 V/s when scanning.
         This sets a typical minimum output rate of 180/.2 = 900 Hz.
         Sampling faster will decrease the step size.
         Lowering the sweep rate open ups smaller measure rates
        '''
        # Make copies of start and end dictionaries so we can mess them up
        Vstart = Vstart.copy()
        Vend = Vend.copy()

        # Sweep to Vstart.
        # self.V calls this function.
        # Recursion should only go one level deep.
        if Vstart != self._V:
            self.V = Vstart

        # Make sure to only have the piezos we want to sweep over
        all_keys = list(set(Vstart) & set(Vend)) # keys in common
        for v in Vstart, Vend:
            keys = list(v.keys()) # keys in each one
            for key in keys:
                if key not in all_keys:
                    v.pop(key) # get rid of unwanted items
        all_keys.sort()

        # Determine sweep rate
        if sweep_rate > self._max_sweep_rate:
            raise Exception('Sweeping piezos too fast! Max is 180 V/s!')

        # Figure out the step size demanded by sweep_rate and meas_rate
        step_size = sweep_rate/meas_rate # default: 0.2 V
        if step_size > self._max_step_size:
            raise Exception('Sweeping piezos too choppily! Decrease sweep_rate or increase meas_rate to increase the step size!')

        msg = 'Sweeping piezos! '
        for key in all_keys:
            msg = msg + '\n%s: %.1f to %.1f ' %(key, Vstart[key], Vend[key])

        # Calculate number of steps using.
        # max(|(Whole voltage range)/(step size)|).
        # Add 1 so there is at least 1 step
        # All piezos use the same numsteps, Based on which piezo needs to
        # move the furthest.
        numsteps = max(
            [int(abs(Vstart[k]-Vend[k])/step_size)+1 for k in Vstart])

        # Check voltage limits and remove gain
        for k in Vstart.keys():
            getattr(self,k).check_lim(Vstart[k])
            Vstart[k] = getattr(self,k).remove_gain(Vstart[k])
        for k in Vend.keys():
            getattr(self,k).check_lim(Vend[k])
            Vend[k] = getattr(self,k).remove_gain(Vend[k])

        # Convert keys to the channel names that the daq expects
        # Remove extra keys
        all_keys = list(set(Vstart) & set(Vend))
        for key in Vstart.keys():
            if key not in all_keys:
                Vstart.pop(key)
        for key in Vend.keys():
            if key not in all_keys:
                Vend.pop(key)

        output_data, received = self._daq.sweep(Vstart, Vend,
                                                chan_in = chan_in,
                                                sample_rate=meas_rate,
                                                numsteps=numsteps,
                                                trigger = trigger
                            )
        # Reapply gain
        for k in output_data.keys():
            output_data[k] = getattr(self,k).apply_gain(output_data[k])

        # Keep track of current voltage
        for k in output_data:
            self._V[k] = Vend[k] # end of sweep, for keeping track of voltage

        return output_data, received

    def sweep_surface(self, voltages, chan_in=None, sweep_rate=180, meas_rate=900):
        '''
        Sweeps piezos using arrays given in a voltage dictionary.
        This function will take that dictionary and interpolate to a different
         number of steps. This number is determined by figuring out the total
         distance (in volts) traveled by each piezo, and then dividing by the
         average step size determined by sweep_rate and meas_rate. Note that
         this does not ensure that the step size is kept constant between all
          data points; it only ensures that the average is not too high.
         Specify the channels you want to monitor as a list.
         Maximum step size set at 0.2 Vpiezo by default for class.
         Piezo sweep rate limited to 180 V/s when not scanning, 120 V/s when scanning.
         This sets a typical minimum output rate of 180/.2 = 900 Hz.
         Sampling faster will decrease the step size.
         Lowering the sweep rate open ups smaller measure rates
        '''
        voltages = voltages.copy() # so we don't modify voltages

        Vstart = {}
        Vend = {}
        for key, value in voltages.items():
            Vstart[key] = value[0]
            Vend[key] = value[-1]

        ## Sweep to Vstart first if we aren't already there. self.V calls this function, but recursion should only go one level deep.
        if Vstart != self._V:
            self.V = Vstart

        ## Figuring out how fast to sweep
        if sweep_rate > self._max_sweep_rate:
            raise Exception('Sweeping piezos too fast! Max is 180 V/s!')

        # Figure out the step size demanded by sweep_rate and meas_rate
        step_size = sweep_rate/meas_rate # default: 0.2 V
        if step_size > self._max_step_size:
            raise Exception('Sweeping piezos too choppily! Decrease sweep_rate or increase meas_rate to increase the step size!')

        ## Figure out the number of steps we need to take to get this average step size
        numsteps = []
        for k in voltages.keys():
            diffs = abs(np.diff(voltages[k])) # step sizes
            total_voltage_distance = sum(diffs)
            numsteps.append(total_voltage_distance/step_size)

        numsteps = max(numsteps) # we will follow whichever piezo needs the most steps

        ## Now interpolate to this number of steps:
        for k in voltages.keys():
            f = interp1d(np.linspace(0,1,len(voltages[k])), voltages[k])
            voltages[k] = f(np.linspace(0,1,numsteps))

            # check if step size is way too large
            diffs = abs(np.diff(voltages[k]))
            if len(diffs[diffs>self._max_step_size*3]):
                raise Exception('Piezo step size too large! Max is %s' %self._max_step_size)

        ## Check voltage limits and remove gain
        for k in voltages.keys():
            getattr(self,k).check_lim(voltages[k])
            voltages[k] = getattr(self,k).remove_gain(voltages[k])

        ## Convert keys to the channel names that the daq expects
        for k in list(voltages.keys()): # need this a list so that new keys aren't iterated over
            voltages[getattr(self,k).label] = voltages.pop(k) # changes key to daq output channel name

        received = self._daq.send_receive(voltages, chan_in = chan_in,
                                sample_rate=meas_rate)

        ## Go back to piezo keys
        for k in self._piezos:
            try:
                voltages[k] = voltages.pop(getattr(self,k).label)
            except:
                pass
            try:
                self._V.pop(getattr(self,k).label) # was keeping daq keys for some reason
            except:
                pass

        for k in voltages.keys():
            voltages[k] = getattr(self,k).apply_gain(voltages[k])

        ## Keep track of current voltage
        self.V # does a measurement of daq output channels

        return voltages, received


    def zero(self):
        self.V = 0

    def HVALookup(self,readArray,chan_1,chan_2):
        '''
        Calculates gain from AO and A1 channels on HVA bitstream. Channel
        numbers start with zero

        readArray: array returned by digital read from HVA
        chan_1: AO in HVA manual, offset by -1 from HVA manual numbering
        convention
        chan_2: A1 in HVA manual, offset by -1 from HVA manual numbering
        convention

        returns the gain calculated
        '''
        if readArray[chan_1] == 1:
            if readArray[chan_2] == 1:
                output = 40
            else:
                output = 4
        else:
            if readArray[chan_2] == 1:
                output = 15
            else:
                output = 1
        return output


    def checkHVAStatus(self):
        '''
        Checks high voltage amplifier for overheat and high temp as well as
        checking if all parameters equal those in code

        Raises exceptions for mismatches in code and hardware, or if there is
        fault condition in the HVA.
        '''
        arraySize = 16; # Length of serial word
        sampsPerChanToAcquire = arraySize + 1
        readArray = np.ones(arraySize, dtype=np.uint8)
        loadArray = np.ones(sampsPerChanToAcquire, dtype=np.uint8)
        loadArray[1] = 0; # Create trigger
        LP_c_double = mx.POINTER(mx.c_long);
        actRead = LP_c_double()
        numBytes = LP_c_double()
        rate = 100000 # Communication rate, should be set as high as possible
        numRead = LP_c_double()
        sampsPerChanWritten = LP_c_double()

        # Create tasks
        taskIn = mx.Task()
        taskOut = mx.Task()
        taskClock = mx.Task()

        # Creates input and output
        taskIn.CreateDIChan("/Dev1/port0/line4","dIn",
                            mx.DAQmx_Val_ChanPerLine)
        taskOut.CreateDOChan("/Dev1/port0/line5","Load",
                             mx.DAQmx_Val_ChanPerLine)

        # Creates a counter to use as a clock
        taskClock.CreateCOPulseChanFreq("/Dev1/ctr0", "clock",
                                        mx.DAQmx_Val_Hz,mx.DAQmx_Val_Low,0,rate,.5)
        taskClock.CfgImplicitTiming(mx.DAQmx_Val_ContSamps,17)

        #Set both input and output to use the counter we created as clock
        taskIn.CfgSampClkTiming ("/Dev1/Ctr0InternalOutput",
                                 rate,mx.DAQmx_Val_Rising,mx.DAQmx_Val_FiniteSamps,
                                 sampsPerChanToAcquire);
        taskOut.CfgSampClkTiming ("/Dev1/Ctr0InternalOutput",rate,
                                  mx.DAQmx_Val_Rising,mx.DAQmx_Val_ContSamps,
                                  sampsPerChanToAcquire);

        # Syncs input to external connection from counter
        taskIn.CfgDigEdgeStartTrig("/Dev1/PFI1",mx.DAQmx_Val_Rising)

        # Loads data to be written
        taskOut.WriteDigitalLines(sampsPerChanToAcquire,False,.9,
                                  mx.DAQmx_Val_GroupByChannel,loadArray,
                                  sampsPerChanWritten,None)

        #Start tasks
        taskClock.StartTask()
        taskOut.StartTask()
        time.sleep(.01)
        taskIn.StartTask()
        taskIn.ReadDigitalLines(-1,.9,mx.DAQmx_Val_GroupByChannel,readArray,80,
                                numRead,numBytes,None)
        time.sleep(.01)
        taskIn.StopTask()
        taskClock.StopTask()
        taskOut.StopTask()

        #throw exceptions for errors
        if readArray[0] == 0:
             raise Exception("The aux output is not enabled!")
        if readArray[1] == 0:
             raise Exception("The Z output is not enabled!")
        if readArray[2] == 0:
             raise Exception("The X&Y outputs are not enabled!")
        if readArray[3] == 0:
             print("The output connector is not plugged in!")
        if readArray[5] == 1:
             raise Exception("HVA High Temperature!")
        if readArray[6] == 0:
             raise Exception("HV Supply error")
        if readArray[7] == 1:
             raise Exception("Overheated!")
        if readArray[8] == 1:
             raise Exception("the polarity of aux is positive")
        if readArray[11] == 0:
             raise Exception("the polarity of Z is negative")
        if self.HVALookup(readArray, 10,9) != self.z.gain:
            raise Exception("the gain of aux should be " + str(self.z.gain) # aux channel is our z-
                            + " but it is set to "
                            + str(self.HVALookup(readArray, 10,9)))
        if self.HVALookup(readArray, 14,15) != self.z.gain:
            raise Exception("the gain of z should be " + str(self.z.gain)
                            + " but it is set to "
                            + str(self.HVALookup(readArray, 14,15)))
        if self.HVALookup(readArray, 12,13) != self.x.gain:
            raise Exception("the gain of x should be " + str(self.x.gain)
                            + " but it is set to "
                            + str(self.HVALookup(readArray, 12,13)))



class Piezo(Instrument):
    _V = None
    def __init__(self, daq, label=None, gain=15, Vmax=200, bipolar=2,
                 max_sweep_rate=180, max_step_size=.2):
        self._daq = daq
        self.label = label
        self.gain = gain
        self.Vmax = Vmax
        self.bipolar = bipolar
        self.V # get voltage from daq
        self.max_sweep_rate = max_sweep_rate
        self.max_step_size = max_step_size

    def __getstate__(self):
        self._save_dict = { "label": self.label,
                            "gain": self.gain,
                            "Vmax": self.Vmax,
                            "bipolar multiplier": self.bipolar,
                            "V": self.V,
                            "max sweep rate": self.max_sweep_rate,
                            "sweep step size": self.max_step_size
                        }
        return self._save_dict


    def __setstate__(self, state):
        state['bipolar'] = state.pop('bipolar multiplier')
        state['_V'] = state.pop('V')
        state['max_sweep_rate'] = state.pop('max sweep rate')
        state['max_step_size'] = state.pop('sweep step size')
        self.__dict__.update(state)


    @property
    def V(self):
        '''
        Voltage property. Set or read piezo voltage
        '''
        try:
            # Convert daq volts to piezo volts
            self._V = self._daq.outputs[self.label].V*self.gain*self.bipolar
        except:
            print('Couldn\'t communicate with daq! Current %s piezo voltage unknown!' %self.label)
        return self._V

    @V.setter
    def V(self, value):
        self.check_lim(value)
        self.sweep(self.V, value)
        self._V = value


    def apply_gain(self, value):
        '''
        Converts DAQ volts to piezo volts by multiplying a voltage by the
        gain and bipolar factor
        '''
        if np.isscalar(value):
            return value*self.gain*self.bipolar
        else:
            return np.array(value)*self.gain*self.bipolar


    def remove_gain(self, value):
        '''
        Converts piezo volts to DAQ volts by dividing a voltage by the
        gain and bipolar factor
        '''
        if np.isscalar(value):
            return value/self.gain/self.bipolar
        else:
            return np.array(value)/self.gain/self.bipolar


    def check_lim(self, V):
        '''
        checks voltage list V = [...] to see if it is out of range for the
        piezo
        '''
        if np.isscalar(V):
            Vtemp = [V]
        else:
            Vtemp = V
        if type(Vtemp) is not np.ndarray:
            Vtemp = np.array(Vtemp)
        # +/- 1 is tolerance, daq noise was throwing it off
        if Vtemp.max()-1 > self.Vmax or Vtemp.min()+1 < -self.Vmax:
            raise Exception('Voltage out of range for %s piezo! Max is %s' %(self.label, self.Vmax))


    def sweep(self, Vstart, Vend, chan_in=None, sweep_rate=180, meas_rate=900):
        '''
        Sweeps piezos linearly from a starting voltage to an ending voltage.
        Specify a list of input channels you want to monitor.
         Maximum allowed step size will be the step size for the piezo that has
         to sweep over the largest voltage range.
         Maximum step size set at 0.2 Vpiezo by default for class.
         Piezo sweep rate limited to 180 V/s when not scanning, 120 V/s when scanning.
         This sets a typical minimum output rate of 180/.2 = 900 Hz.
         Sampling faster will decrease the step size.
         Lowering the sweep rate open ups smaller measure rates
        '''
        # Sweep to Vstart first if we aren't already there.
        # Self.V calls this function, but recursion should only go one
        # level deep.
        # Need self._V or else it will do a measurement and loop forever!
        if Vstart != self._V:
            self.V = Vstart

        ## Check voltage limits
        self.check_lim(Vstart)
        self.check_lim(Vend)

        ## Figuring out how fast to sweep
        if sweep_rate > self.max_sweep_rate:
            raise Exception('Sweeping piezos too fast! Max is 180 V/s!')

        # Figure out the step size demanded by sweep_rate and meas_rate
        step_size = sweep_rate/meas_rate # default: 0.2 V
        if step_size > self.max_step_size:
            raise Exception('Sweeping piezos too choppily! Decrease sweep_rate or increase meas_rate to increase the step size!')

        # Calculate number of steps. This is |(Whole voltage range)/(step size)|.
        # Add 1 so there is at least 1 step
        numsteps = int(abs(Vstart-Vend)/step_size)+1

        # Remove gain
        Vstart = self.remove_gain(Vstart)
        Vend = self.remove_gain(Vend)

        output_data, received = self._daq.sweep({self.label: Vstart},
                                            {self.label: Vend},
                                            chan_in = chan_in,
                                            sample_rate=meas_rate,
                                            numsteps=numsteps
                                        )

        output_data = output_data[self.label]
        ## reapply gain
        output_data = self.apply_gain(output_data)

        self._V = Vend # check the current voltage

        return output_data, received


    def zero(self):
        print('Zeroing %s piezo...' %self.label)
        self.V = 0
        print('...done.')
        log('Zeroed all piezos safely.')
