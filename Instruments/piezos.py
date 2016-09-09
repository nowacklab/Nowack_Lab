import numpy as np
import time
import atexit

class Piezos():
    '''
    Piezo benders on the scanner.
    Signal sent to NIDAQ goes through Nanonis HVA4 High Voltage Amplifier.
    Sweeps between voltages smoothly.
    '''
    _piezos = ['x','y','z']
    _gain = [40, 40, 40]
    _Vmax = [400, 400, 400] # maximum allowed total voltage across piezo
    _bipolar = [2, 2, 2] # multiplier for whether piezos are biased +V/-V or not.
    _V = {}

    def __init__(self, daq=None, chan_out = [0,1,2], zero = False):
        '''
        e.g. pz = piezos.Piezos(daq=daq, chan_out = [0,1,2], zero = True)
            daq: the nidaq.NIDAQ() object
            chan_out: output channels of daq for each positioner (just the number, ao#) [x,y,z]
            zero: whether to zero the daq or not
        '''
        self._daq = daq
        if daq is None:
            print('Daq not loaded... piezos will not work until you give them a daq!')

        for (i,p) in enumerate(self._piezos):
            setattr(self, p, Piezo(self._daq, chan_out[i], label=p,
                                    gain = self._gain[i], Vmax=self._Vmax[i],
                                    bipolar = self._bipolar[i]
                                )) # makes benders x, y, and z

        if zero:
            self.zero()

    def __getstate__(self):
        self.save_dict = {"x": self.x,
                            "y": self.y,
                            "z": self.z,
                            "daq": self._daq}
        return self.save_dict


    def __setstate__(self, state):
        state.pop('daq') # don't want to load the daq automatically
        self.__dict__.update(state)
        print('Daq not loaded! Load with load_daq(daq)!')


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
            value = {k: value for k in ['x','y','z']}

        self.check_lim(value)

        ## Sweep to the desired voltage
        self.sweep(self.V, value)

        ## Store the desired voltage
        for key in value:
            self._V[key] = value[key]


    def load_daq(self, daq):
        '''
        If piezos object loaded without a daq, give it a daq.
        '''
        self._daq = daq
        for p in self._piezos:
            getattr(self,p)._daq = daq


    def sweep(self, Vstart, Vend, Vstepmax = 0.01, freq = 1500):
        '''
        Sweeps piezos from a starting voltage (dictionary) to an ending voltage (dictionary), with maximum allowed step size and frequency. Maximum allowed step size will be the step size for the piezo that has to sweep over the largest voltage range.
        '''
        ## Sweep to Vstart first if we aren't already there. self.V calls this function, but recursion should only go one level deep.
        if Vstart != self.V:
            self.V = Vstart

        ## Make sure to only have the piezos requested to sweep over
        all_keys = list(set(Vstart) & set(Vend)) # keys in common
        for v in Vstart, Vend:
            keys = list(v.keys()) # keys in each one
            for key in keys:
                if key not in all_keys:
                    v.pop(key) # get rid of unwanted items

        ## Check voltage limits
        for p in self._piezos:
            getattr(self,p).check_lim(Vstart)
            getattr(self,p).check_lim(Vend)

        ## Calculate number of steps. This is max(|(Whole voltage range)/(step size)| + 1). All piezos use the same numsteps.
        numsteps = max([int(abs(Vstart[k]-Vend[k])/Vstepmax)+1 for k in Vstart])

        ## Remove gain
        Vstart = self.remove_gain(Vstart)
        Vend = self.remove_gain(Vend)

        ## Convert keys to the channel names that the daq expects
        for k in list(Vstart.keys()): # need this a list so that new keys aren't iterated over
            Vstart[getattr(self,k).chan_out] = Vstart.pop(k) # changes key to daq output channel name
            Vend[getattr(self,k).chan_out] = Vend.pop(k)
        all_keys = list(set(Vstart) & set(Vend))

        V, response, time = self._daq.sweep(all_keys, Vstart, Vend, freq=freq, numsteps=numsteps)

        ## Go back to piezo keys
        for k in self._piezos:
            try:
                V[k] = V.pop(getattr(self,k).chan_out)
            except: # in case one or more keys is not used
                pass

        ## reapply gain
        V = self.apply_gain(V)

        ## Keep track of current voltage
        for k in V:
            self._V[k] = V[k][-1] # end of sweep, for keeping track of voltage

        return V, response, time


    def zero(self):
        for p in self._piezos:
            getattr(self,p).zero()


class Piezo():
    def __init__(self, daq, chan_out, label=None, gain=15, Vmax=200, bipolar=2):
        self._daq = daq
        self.chan_out = chan_out
        self.label = label
        self.gain = gain
        self.Vmax = Vmax
        self.bipolar = bipolar
        self.V # get voltage from daq
        

        def __getstate__(self):
            self.save_dict = {"chan_out": self.chan_out,
                                "label": self.label,
                                "gain": self.gain,
                                "Vmax": self.Vmax,
                                "bipolar multiplier": self.bipolar,
                                "V": self.V}
            return self.save_dict


        def __setstate__(self, state):
            state['bipolar'] = state.pop('bipolar multiplier')
            state['_V'] = state.pop('V')
            self.__dict__.update(state)


        @property
        def V(self):
            '''
            Voltage property. Set or read piezo voltage
            '''
            self._V = getattr(self._daq, self.chan_out)*self.gain*self.bipolar # convert daq volts to piezo volts
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
                return list(np.array(value)*self.gain*self.bipolar)


        def remove_gain(self, value):
            '''
            Converts piezo volts to DAQ volts by dividing a voltage by the gain and bipolar factor
            '''
            if np.isscalar(value):
                return value/self.gain/self.bipolar
            else:
                return list(np.array(value)/self.gain/self.bipolar)


        def check_lim(self, V):
            '''
            checks voltage list V = [...] to see if it is out of range for the piezo
            '''
            Vtemp = V.copy() # need to do this or else V is modified
            if np.isscalar(Vtemp):
                Vtemp = [Vtemp]
            if type(Vtemp) is not np.ndarray:
                Vtemp = np.array(Vtemp)
            if Vtemp.max()-1 > self.Vmax or Vtemp.min()+1 < -self.Vmax:# +/- 1 is tolerance, daq noise was throwing it off
                raise Exception('Voltage out of range for %s piezo! Max is %s' %(self.label, self.Vmax))


        def sweep(self, Vstart, Vend, Vstepmax = 0.01, freq = 1500):
            '''
            Sweeps piezo from a starting voltage to an ending voltage,
            with maximum allowed step size and frequency.
            '''
            ## Sweep to Vstart first if we aren't already there.
            ## Self.V calls this function, but recursion should only go one level deep.
            if Vstart != self.V:
                self.V = Vstart

            ## Check voltage limits
            self.check_lim(Vstart)
            self.check_lim(Vend)

            ## Calculate number of steps. |(Whole voltage range)/(step size)| + 1.
            numsteps =int(abs(Vstart-Vend)/Vstepmax)+1

            ## Remove gain
            Vstart = self.remove_gain(Vstart)
            Vend = self.remove_gain(Vend)

            V, response, time = self._daq.sweep(self.chan_out, Vstart, Vend, freq=freq, numsteps=numsteps)

            ## reapply gain
            V = self.apply_gain(V)

            self.V # check the current voltage

            return V, response, time

        def zero(self):
            print('Zeroing %s piezo...' %self.label)
            self.V = 0
            print('...done.')
