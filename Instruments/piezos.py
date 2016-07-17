import numpy as np
import time
import atexit

class Piezos():
    '''
    Piezo benders on the scanner. Signal sent to NIDAQ goes through Nanonis HVA4 High Voltage Amplifier. Sweeps between voltages smoothly. One hiccup is that it jumps to zero upon creating the Piezo object.
    '''
    # amp = nanonis.HVA4('COM2')

    def __init__(self, daq, chan_out = {'x':0,'y':1,'z':2}, gain = {15 for i in ['x','y','z']}, Vmax={'x':200, 'y':200, 'z':200}, bipolar = {True for i in ['x','y','z']}, zero = True):
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
        self.chan_out = chan_out
        self.Vmax = Vmax
        self.bipolar = {}
        for key, value in bipolar.items():
            self.bipolar[key] = value + 1 # Bipolar multiplier; False = 1, True = 2

        self._V = {}
        if zero:
            self.V = {'x': 0, 'y': 0, 'z': 0}

    @property
    def V(self):
        '''
        Voltage property. Set and read any number of piezo voltages.
            pz.V
            pz.V = {'z':150, 'y':100}
            pz.V = 0 will zero all piezos
        '''
        for key in self.chan_out.keys():
            self._V[key] = getattr(self.daq, 'ai%s' %chan_out[key])*self.gain[key]*self.bipolar[key] # convert daq volts to piezo volts
        return self._V

    @V.setter
    def V(self, value):
        if np.isscalar(value):
            value = {k:value for k in ['x','y','z']}

        self.check_lim(value)

        ## Sweep to the desired voltage
        self.sweep(self.V, value)

        ## Store the desired voltage
        for key in value.keys():
            self._V[key] = value[key]


    def apply_gain(self, value):
        '''
        Converts DAQ volts to piezo volts by multiplying a voltage (dictionary) by the gain and bipolar factor for each axis.
        '''
        gains = {}
        for k in value.keys():
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
        for k in value.keys():
            if np.isscalar(value[k]):
                gains[k] =  value[k]/self.gain[k]/self.bipolar[k]
            else:
                gains[k] = list(np.array(value[k])/self.gain[k]/self.bipolar[k])
        return gains


    def check_lim(self, V):
        '''
        checks dictionary {'x': Vx, 'y': Vy, 'z': Vz} of voltage lists Vj = [...] to see if they are out of range for the piezos
        '''
        for k in V.keys():
            if np.isscalar(V[k]):
                V[k] = [V[k]]
            if type(V[k]) is not np.ndarray:
                V[k] = np.array(V[k])
            if V[k].max() > self.Vmax[k] or V[k].min() < -self.Vmax[k]:
                raise Exception('Voltage out of range for %s piezo! Max is %s' %(k, self.Vmax[k]))

#         for V in ('Vx', 'Vy', 'Vz'):

        #
#             if np.isscalar(eval(V)):
#                 exec('%s = [%s]' %(V, V)) # Makes Vj a list if it is not
#             if type(eval(V)) is not np.ndarray:
#                 exec('%s = np.array(%s)' %(V, V)) # makes it into a numpy array so min and max work correctly
#
#         if Vx is not None:
#             if Vx.max() > self.Vmax['x'] or Vx.min() < -self.Vmax['x']:
#                 raise Exception('Voltage out of range for x piezo! Max is %s' %self.Vmax['x'])
#         if Vy is not None:
#             if Vy.max() > self.Vmax['y'] or Vy.min() < -self.Vmax['y']:
#                 raise Exception('Voltage out of range for y piezo!')
#         if Vz is not None:
#             if Vz.max() > self.Vmax['z'] or Vz.min() < -self.Vmax['z']:
#                 raise Exception('Voltage out of range for z piezo!')


    def sweep(self, Vstart, Vend, Vstepmax = 0.01, freq = 1500):
        '''
        Sweeps piezos from a starting voltage (dictionary) to an ending voltage (dictionary), with maximum allowed step size and frequency. Maximum allowed step size will be the step size for the piezo that has to sweep over the largest voltage range.
        '''
        ## Check voltage limits
        self.check_lim(Vstart)
        self.check_lim(Vend)

        ## Sweep to Vstart first if we aren't already there. self.V calls this function, but recursion should only go one level deep.
        if Vstart != self.V:
            self.V = Vstart

        ## Calculate number of steps. This is max(|(Whole voltage range)/(step size)| + 1). All piezos use the same numsteps.
        numsteps = max([int(abs(Vstart[k]-Vend[k])/Vstepmax)+1 for k in Vstart.keys()])

        ## Convert keys to the channel names that the daq expects and remove gain
        Vstart = self.remove_gain(Vstart)
        Vend = self.remove_gain(Vend)

        for k in Vstart.keys():
            Vstart[self.chan_out[k]] = Vstart.pop(k) # changes key to daq output channel name
            Vend[self.chan_out[k]] = Vend.pop(k)

        V, response, time = self.daq.sweep([self.chan_out[k] for k in KEYS], Vstart, Vend, freq=freq, numsteps=numsteps)

        ## Go back to piezo keys
        for k in ['x','y','z']:
            try:
                V[k] = V.pop(self.chan_out[k])
            except: # in case one or more keys is not used
                pass

        ## reapply gain
        V = self.apply_gain(V)

        ## Keep track of current voltage
        for k in V.keys():
            self._V[k] = V[k][-1] # end of sweep, for keeping track of voltage

        return V, response, time

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
