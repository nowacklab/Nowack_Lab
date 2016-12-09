import numpy as np
from ..Utilities.logging import log
from .instrument import Instrument

class Piezos(Instrument):
    '''
    Piezo benders on the scanner.
    Signal sent to NIDAQ goes through Nanonis HVA4 High Voltage Amplifier.
    Sweeps between voltages smoothly.
    '''
    _label = 'piezos'
    _chan_labels = ['x','y','z'] # DAQ channel labels expected by this class
    _piezos = ['x','y','z']
    _gain = [40, 40, 40]
    _Vmax = [400, 400, 400] # maximum allowed total voltage across piezo
    _bipolar = [2, 2, 2] # multiplier for whether piezos are biased +V/-V or not.
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
        for ch in self._chan_labels:
            if ch not in daq.outputs and ch not in daq.inputs:
                raise Exception('Need to set daq channel labels! Need a %s' %ch)

        for (i,p) in enumerate(self._piezos):
            setattr(self, p, Piezo(self._daq, label=p,
                                    gain = self._gain[i], Vmax=self._Vmax[i],
                                    bipolar = self._bipolar[i],
                                max_sweep_rate = self._max_sweep_rate,
                                max_step_size=self._max_step_size))
                                # makes benders x, y, and z

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
        ## Sweep to the desired voltage
        self.sweep(self.V, value)
        ## Store the desired voltage
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


    def sweep(self, Vstart, Vend, chan_in=None, sweep_rate=180, meas_rate=900):
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
        ## Make copies of start and end dictionaries so we can mess them up
        Vstart = Vstart.copy()
        Vend = Vend.copy()

        ## Sweep to Vstart first if we aren't already there. self.V calls this function, but recursion should only go one level deep.
        if Vstart != self._V:
            self.V = Vstart

        ## Make sure to only have the piezos we want to sweep over
        all_keys = list(set(Vstart) & set(Vend)) # keys in common
        for v in Vstart, Vend:
            keys = list(v.keys()) # keys in each one
            for key in keys:
                if key not in all_keys:
                    v.pop(key) # get rid of unwanted items
        all_keys.sort()

        ## Figuring out how fast to sweep
        if sweep_rate > self._max_sweep_rate:
            raise Exception('Sweeping piezos too fast! Max is 180 V/s!')

        # Figure out the step size demanded by sweep_rate and meas_rate
        step_size = sweep_rate/meas_rate # default: 0.2 V
        if step_size > self._max_step_size:
            raise Exception('Sweeping piezos too choppily! Decrease sweep_rate or increase meas_rate to increase the step size!')

        msg = 'Sweeping piezos! '
        for key in all_keys:
            msg = msg + '\n%s: %.1f to %.1f ' %(key, Vstart[key], Vend[key])
        log(msg)

        ## Calculate number of steps. This is max(|(Whole voltage range)/(step size)|).
        ## Add 1 so there is at least 1 step
        ## All piezos use the same numsteps. This is based on which piezo needs to move the furthest.
        numsteps = max([int(abs(Vstart[k]-Vend[k])/step_size)+1 for k in Vstart])

        ## Check voltage limits and remove gain
        for k in Vstart.keys():
            getattr(self,k).check_lim(Vstart[k])
            Vstart[k] = getattr(self,k).remove_gain(Vstart[k])
        for k in Vend.keys():
            getattr(self,k).check_lim(Vend[k])
            Vend[k] = getattr(self,k).remove_gain(Vend[k])

        # ## Convert keys to the channel names that the daq expects
        # for k in list(Vstart.keys()): # need this a list so that new keys aren't iterated over
        #     Vstart[getattr(self,k).label] = Vstart.pop(k) # changes key to daq output channel name
        #     Vend[getattr(self,k).label] = Vend.pop(k)

        ## If for some reason you give extra keys, get rid of them.
        all_keys = list(set(Vstart) & set(Vend))
        for key in Vstart.keys():
            if key not in all_keys:
                Vstart.pop(key)
        for key in Vend.keys():
            if key not in all_keys:
                Vend.pop(key)

        output_data, received = self._daq.sweep(Vstart, Vend, chan_in = chan_in,
                                sample_rate=meas_rate, numsteps=numsteps
                            )

        # ## Go back to piezo keys
        # for k in self._piezos:
        #     try:
        #         output_data[k] = output_data.pop(getattr(self,k).label)
        #     except:
        #         pass
        #     try:
        #         Vend[k] = Vend.pop(getattr(self,k).label) # need to convert Vend back for later
        #     except: # in case one or more keys is not used
        #         pass
        #     try:
        #         self._V.pop(getattr(self,k).label) # was keeping daq keys for some reason
        #     except:
        #         pass

        ## reapply gain
        for k in output_data.keys():
            output_data[k] = getattr(self,k).apply_gain(output_data[k])

        ## Keep track of current voltage
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
        from scipy.interpolate import interp1d
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


class Piezo(Instrument):
    _V = None
    def __init__(self, daq, label=None, gain=15, Vmax=200, bipolar=2, max_sweep_rate=180, max_step_size=.2):
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
            self._V = self._daq.outputs[self.label].V*self.gain*self.bipolar # convert daq volts to piezo volts
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
        Converts DAQ volts to piezo volts by multiplying a voltage by the gain and bipolar factor
        '''
        if np.isscalar(value):
            return value*self.gain*self.bipolar
        else:
            return np.array(value)*self.gain*self.bipolar


    def remove_gain(self, value):
        '''
        Converts piezo volts to DAQ volts by dividing a voltage by the gain and bipolar factor
        '''
        if np.isscalar(value):
            return value/self.gain/self.bipolar
        else:
            return np.array(value)/self.gain/self.bipolar


    def check_lim(self, V):
        '''
        checks voltage list V = [...] to see if it is out of range for the piezo
        '''
        if np.isscalar(V):
            Vtemp = [V]
        else:
            Vtemp = V
        if type(Vtemp) is not np.ndarray:
            Vtemp = np.array(Vtemp)
        if Vtemp.max()-1 > self.Vmax or Vtemp.min()+1 < -self.Vmax:# +/- 1 is tolerance, daq noise was throwing it off
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
        ## Sweep to Vstart first if we aren't already there.
        ## Self.V calls this function, but recursion should only go one level deep.
        if Vstart != self._V: #Need self._V or else it will do a measurement and loop forever!
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

        ## Calculate number of steps. This is |(Whole voltage range)/(step size)|.
        ## Add 1 so there is at least 1 step
        numsteps = int(abs(Vstart-Vend)/step_size)+1

        ## Remove gain
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
