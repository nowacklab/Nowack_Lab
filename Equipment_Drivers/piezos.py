import nanonis
import numpy
import time
import atexit

KEYS = ['x','y','z']

class Piezos():
    '''
    Piezo benders on the scanner. Signal sent to NIDAQ goes through Nanonis HVA4 High Voltage Amplifier. Sweeps between voltages smoothly. One hiccup is that it jumps to zero upon creating the Piezo object.
    '''    
    # amp = nanonis.HVA4('COM2')
    
    def __init__(self, daq, gain, chan_out, Vmax=[120]*3, bipolar = [True]*3):
        """ Pass args ars array [xvalue, yvalue, zvalue] """
        self.daq = daq
        self.gain = {}
        self.chan_out = {} 
        self.Vmax = {}
        self.bipolar = {}
        self._V = {}

        for i in range(len(KEYS)):
            self.gain[KEYS[i]] = gain[i]
            self.chan_out[KEYS[i]] = chan_out[i]
            self.Vmax[KEYS[i]] = Vmax[i]
            self.bipolar[KEYS[i]] = int(bipolar[i])+1 # = 1 if bipolar is False, =2 if bipolar is true
        self._V = self.apply_gain({KEYS[i]: getattr(self.daq, chan_out[i]) for i in range(len(KEYS))})
        self.V = {'x': 0, 'y': 0, 'z': 0}
        
    @property
    def V(self):
        return self._V
    
    @V.setter
    def V(self, value):
        """ Have to set whole dictionary """
        for k in KEYS:
            if k not in value.keys(): # make sure all voltages written
                value[k] = self._V[k]
            if value[k] > self.Vmax[k]*self.bipolar[k]:
                raise Exception('Voltage too high, max is %f' %self.Vmax[k])
        self.sweep(self._V, value)
        self._V = value
    
    def apply_gain(self, value):
        gains = {}
        for k in value.keys():
            if numpy.isscalar(value[k]):
                gains[k] =  value[k]*self.gain[k]*self.bipolar[k]
            else:
                gains[k] = list(numpy.array(value[k])*self.gain[k]*self.bipolar[k])
        return gains
        
    def remove_gain(self, value):
        gains = {}
        for k in value.keys():
            if numpy.isscalar(value[k]):
                gains[k] =  value[k]/self.gain[k]/self.bipolar[k]
            else:
                gains[k] = list(numpy.array(value[k])/self.gain[k]/self.bipolar[k])
        return gains

    def check_lim(self, A):
        for k in A.keys():
            if A[k].max() > self.Vmax[k] or A[k].min() < -self.Vmax[k]:
                raise Exception('Voltage out of range for piezo %s!' %k)
           
    def sweep(self, Vstart, Vend, Vstep = {k: .01 for k in KEYS}, freq = 1500):
        Vs = {}
        
        for k in KEYS:
            if k not in Vstart.keys(): # makes sure that all keys are listed, but will do a pointless nowhere-sweep
                Vstart[k] = self._V[k]
            if k not in Vend.keys(): # makes sure that all keys are listed, but will do a pointless nowhere-sweep
                Vend[k] = self._V[k]
            if k not in Vstep.keys(): # makes sure that all keys are listed, but will do a pointless nowhere-sweep
                Vstep[k] = 0.01
            if Vstart[k] != self._V[k]:
                self.V = Vstart
                # self.sweep(self._V, Vstart)
        numsteps = max([int(abs(Vstart[k]-Vend[k])/Vstep[k])+1 if Vstep[k]!= 0 else 0 for k in KEYS])
        
        #Convert keys to the channel names that the daq expects and remove gain
        Vstart = self.remove_gain(Vstart)
        Vend = self.remove_gain(Vend)
        for k in KEYS:   
            Vstart[self.chan_out[k]] = Vstart.pop(k)
            Vend[self.chan_out[k]] = Vend.pop(k)

        V, response, time = self.daq.sweep([self.chan_out[k] for k in KEYS], Vstart, Vend, freq=freq, numsteps=numsteps)
 
        # Go back to piezo keys
        for k in KEYS:   
            V[k] = V.pop(self.chan_out[k])
            
        V = self.apply_gain(V)
        for k in KEYS:
            self._V[k] = V[k][len(V[k])-1] # end of sweep, for keeping track of voltage 
        
        return V, response, time

""" Commented out code below not yet tested """
        
    # def split_sweep(self, Vstart, Vend, Vstep, freq, iter, num_iter):
        # Vrange = Vend-Vstart
        # if Vstart < Vend: # sweep up
            # V, response, time = self.sweep(Vstart + iter/num_iter*Vrange, Vstart + (iter+1)/num_iter*Vrange, Vstep, freq)
        # elif Vstart > Vend: # sweep up
            # V, response, time = self.sweep(Vend - iter/num_iter*Vrange, Vstart - (iter+1)/num_iter*Vrange, Vstep, freq)
        # return V, response, time 
    
    # def full_sweep(self, Vstep, freq):
        # Vup, responseup, timeup = (self.sweep(0, self.Vmax, Vstep=Vstep, freq=freq)) # up sweep

        # Vdown, responsedown, timedown = (self.sweep(self.Vmax, 0, Vstep=Vstep, freq=freq)) #down sweep
        
        # return Vup + Vdown, responseup + responsedown #, timeup + [t + timeup[len(timeup)-1] for t in timedown]
        
        # Vtot = []
        # responsetot = []
        
        # for i in range(5):
            # Vup, responseup, timeup = (self.sweep(i/5*self.Vmax, (i+1)/5*self.Vmax, Vstep=Vstep, max_rate=max_rate)) # up sweep
            # time.sleep(2)
            # Vtot = Vtot + Vup
            # responsetot = responsetot + responseup
        # for i in range(5):
            # Vdown, responsedown, timedown = (self.sweep((5-i)/5*self.Vmax, (5-i-1)/5*self.Vmax, Vstep=Vstep, max_rate=max_rate))
            # time.sleep(2)
            # Vtot = Vtot + Vdown
            # responsetot = responsetot + responsedown
            
        # return Vtot, responsetot
    
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
        
        # V = list(numpy.linspace(Vstart, Vend, numsteps))
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
   