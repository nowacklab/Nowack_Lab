import numpy as np
import time
import atexit

class Piezos():
    '''
    Piezo benders on the scanner. Signal sent to NIDAQ goes through Nanonis HVA4 High Voltage Amplifier. Sweeps between voltages smoothly. One hiccup is that it jumps to zero upon creating the Piezo object.
    '''
    # amp = nanonis.HVA4('COM2')

    def __init__(self, daq, chan_out = {'x':0,'y':1,'z':2}, gain = {i:15 for i in ['x','y','z']}, Vmax={'x':200, 'y':200, 'z':200}, bipolar = {i: True for i in ['x','y','z']}, zero = True):
        '''
        e.g. pz = piezos.Piezos(daq=daq,
                                chan_out = {'x':0,'y':1,'z':2},
                                gain={'x': 15,'y':15, 'z':15},
                                Vmax = {'x':200, 'y':200, 'z':200},
                                bipolar = {'x':True, 'y':True, 'z':True},
                                zero = True
                                )
            daq: the nidaq.NIDAQ() object
            chan_out: output channel of daq (just the number, ao#)
            gain: gain setting on HVA4
            Vmax: maximum delta voltage across piezo (includes bipolar multiplier)
            bipolar: whether the piezo is driven with +/- V (True) or +V/gnd (False)
            zero: whether to zero the daq or not
        '''
        self.daq = daq
        self.gain = gain
        self.chan_out = {key: 'ao%s'%chan_out[key] for key in chan_out}
        self.Vmax = Vmax
        self.bipolar = {}
        for key, value in bipolar.items():
            self.bipolar[key] = value + 1 # Bipolar multiplier; False = 1, True = 2

        self._V = {}
        if zero:
            self.zero()

    @property
    def V(self):
        '''
        Voltage property. Set and read any number of piezo voltages.
            pz.V
            pz.V = {'z':150, 'y':100}
            pz.V = 0 will zero all piezos
        '''
        for key in self.chan_out:
            self._V[key] = getattr(self.daq, self.chan_out[key])*self.gain[key]*self.bipolar[key] # convert daq volts to piezo volts
        return self._V

    @V.setter
    def V(self, value):
        if np.isscalar(value):
            value = {k:value for k in ['x','y','z']}

        self.check_lim(value)

        ## Sweep to the desired voltage
        self.sweep(self.V, value)

        ## Store the desired voltage
        for key in value:
            self._V[key] = value[key]


    def apply_gain(self, value):
        '''
        Converts DAQ volts to piezo volts by multiplying a voltage (dictionary) by the gain and bipolar factor for each axis.
        '''
        gains = {}
        for k in value:
            if np.isscalar(value[k]):
                gains[k] =  value[k]*self.gain[k]*self.bipolar[k]
            else:
                gains[k] = list(np.array(value[k])*self.gain[k]*self.bipolar[k])
        return gains


    def remove_gain(self, value):
        '''
        Converts piezo volts to DAQ volts by dividing a voltage (dictionary) by the gain and bipolar factor for each axis.
        '''
        gains = {}
        for k in value:
            if np.isscalar(value[k]):
                gains[k] =  value[k]/self.gain[k]/self.bipolar[k]
            else:
                gains[k] = list(np.array(value[k])/self.gain[k]/self.bipolar[k])
        return gains


    def check_lim(self, V):
        '''
        checks dictionary {'x': Vx, 'y': Vy, 'z': Vz} of voltage lists Vj = [...] to see if they are out of range for the piezos
        '''
        Vtemp = V.copy() # need to do this or else V is modified
        for k in Vtemp:
            if np.isscalar(Vtemp[k]):
                Vtemp[k] = [Vtemp[k]]
            if type(Vtemp[k]) is not np.ndarray:
                Vtemp[k] = np.array(Vtemp[k])
            if Vtemp[k].max()-1 > self.Vmax[k] or Vtemp[k].min()+1 < -self.Vmax[k]:# +/- 1 is tolerance, daq noise was throwing it off
                raise Exception('Voltage out of range for %s piezo! Max is %s' %(k, self.Vmax[k]))


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
        self.check_lim(Vstart)
        self.check_lim(Vend)

        ## Calculate number of steps. This is max(|(Whole voltage range)/(step size)| + 1). All piezos use the same numsteps.
        numsteps = max([int(abs(Vstart[k]-Vend[k])/Vstepmax)+1 for k in Vstart])

        ## Remove gain
        Vstart = self.remove_gain(Vstart)
        Vend = self.remove_gain(Vend)

        ## Convert keys to the channel names that the daq expects
        for k in list(Vstart.keys()): # need this a list so that new keys aren't iterated over
            Vstart[self.chan_out[k]] = Vstart.pop(k) # changes key to daq output channel name
            Vend[self.chan_out[k]] = Vend.pop(k)
        all_keys = list(set(Vstart) & set(Vend))

        V, response, time = self.daq.sweep(all_keys, Vstart, Vend, freq=freq, numsteps=numsteps)

        ## Go back to piezo keys
        for k in ['x','y','z']:
            try:
                V[k] = V.pop(self.chan_out[k])
            except: # in case one or more keys is not used
                pass

        ## reapply gain
        V = self.apply_gain(V)

        ## Keep track of current voltage
        for k in V:
            self._V[k] = V[k][-1] # end of sweep, for keeping track of voltage

        return V, response, time

    def zero(self):
        print('Zeroing piezos...')
        self.V = {'x': 0, 'y': 0, 'z': 0}
        print('...done.')

if __name__ == '__main__':
    """ Testing the code.  """
    # import matplotlib.pyplot as plt

    # piezo = Piezo('z', 15, False, 'ao2', 'ai22')
    # sweep_data = piezo.full_sweep(1000)
    # plt.plot(sweep_data[0],sweep_data[1])
    # plt.show()


    ##### OLD DUMB CODE
        # def sweep(self, Vstart, Vend, Vstep=0.01, numsteps=None):
        # # self._V = Vstart

        # if numsteps == None:
            # numsteps = int((Vstart-Vend)/Vstep)+1
        # else:
            # Vstep = (Vend-Vstart)/(numsteps-1)

        # # t_wait_min = 0.035 # set by code execution time
        # # if t_wait < t_wait_min:
            # # t_wait = t_wait_min
            # # print('time limited to 0.035 by current code execution time')

        # max_rate = 40 #V/s

        # V = list(np.linspace(Vstart, Vend, numsteps))
        # if self.remove_gain(abs(max(V))) > 10:
            # raise Exception('NIDAQ out of range!')

        # response = daq.send_receive(self.out_channel, self.in_channel, self.remove_gain(V), freq=max_rate/Vstep)

        # # Upward sweep
        # # for step in range(numsteps):
            # # start_time = time.time()
            # # V_step = self.remove_gain(V[step])

            # # setattr(self.daq, self.out_channel, V_step) # takes 0.009 seconds
            # # if self.in_channel != None:
                # # response.append(getattr(self.daq,self.in_channel)) # takes 0.025 seconds

            # # elapsed_time = time.time() - start_time
            # # if elapsed_time < t_wait:
                # # time.sleep(t_wait - elapsed_time)

        # self._V = V[len(V)-1] # end of sweep

        # return V, response

    # def full_sweep(self, t_wait, numsteps):
        # Vup, responseup = (self.sweep(0, self.Vmax, t_wait,numsteps)) # up sweep
        # Vdown, responsedown = (self.sweep(self.Vmax-self.Vmax/numsteps, 0, t_wait,numsteps-1)) # down sweep # extra term avoids duplicate data point at top of sweep; minus 1 makes it symmetric
        # return Vup + Vdown, responseup + responsedown
