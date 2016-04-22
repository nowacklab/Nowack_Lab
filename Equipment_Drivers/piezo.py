import nidaq
import nanonis
import numpy
import time
import atexit

class Piezo():
    '''
    Piezo benders on the scanner. Signal sent to NIDAQ goes through Nanonis HVA4 High Voltage Amplifier. Sweeps between voltages smoothly. One hiccup is that it jumps to zero upon creating the Piezo object.
    '''    
    daq = nidaq.NIDAQ()
    # amp = nanonis.HVA4('COM2')
    
    def __init__(self, axis, gain, bipolar, out_channel, in_channel = None, Vmax=120):
        self.axis = axis
        self.Vmax = Vmax
        self.gain = gain
        self.bipolar_multiplier = 1
        if bipolar:
            self.bipolar_multiplier = 2
        self.out_channel = out_channel
        self.in_channel = in_channel
        self._V = 0
        self.V = 0
        atexit.register(self.exit)
        
    @property
    def V(self):
        return self._V
    
    @V.setter
    def V(self, value):
        if abs(value) > self.Vmax:
            raise Exception('Voltage too high, max is %f' %self.Vmax)
        self.sweep(self._V, value)
        # setattr(self.daq, self.out_channel, value)
        self._V = value
    
    def apply_gain(self, value):
        if numpy.isscalar(value):
            return value*self.gain*self.bipolar_multiplier
        return list(numpy.array(value)*self.gain*self.bipolar_multiplier)
        
    def remove_gain(self, value):
        if numpy.isscalar(value):
            return value/self.gain/self.bipolar_multiplier
        return list(numpy.array(value)/self.gain/self.bipolar_multiplier)
        
    def sweep(self, Vstart, Vend, Vstep = .1, freq = 150): #max rate in volts/second, including gain
        if Vstart == Vend:
            return 1, 1, 1
        if Vstart != self._V:
            self.sweep(self._V, Vstart, .1)
        
        V, response, time = self.daq.sweep(self.out_channel, self.in_channel, self.remove_gain(Vstart), self.remove_gain(Vend), Vstep=self.remove_gain(Vstep), freq=freq)
 
        V = self.apply_gain(V)
        self._V = V[len(V)-1] # end of sweep, for keeping track of voltage 
        
        return V, response, time
        
    def split_sweep(self, Vstart, Vend, Vstep, freq, iter, num_iter):
        Vrange = Vend-Vstart
        if Vstart < Vend: # sweep up
            V, response, time = self.sweep(Vstart + iter/num_iter*Vrange, Vstart + (iter+1)/num_iter*Vrange, Vstep, freq)
        elif Vstart > Vend: # sweep up
            V, response, time = self.sweep(Vend - iter/num_iter*Vrange, Vstart - (iter+1)/num_iter*Vrange, Vstep, freq)
        return V, response, time 
    
    def full_sweep(self, Vstep, freq):
        Vup, responseup, timeup = (self.sweep(0, self.Vmax, Vstep=Vstep, freq=freq)) # up sweep

        Vdown, responsedown, timedown = (self.sweep(self.Vmax, 0, Vstep=Vstep, freq=freq)) #down sweep
        
        return Vup + Vdown, responseup + responsedown #, timeup + [t + timeup[len(timeup)-1] for t in timedown]
        
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
        
    def exit(self):
        self.sweep(self._V, 0)
    
if __name__ == '__main__':
    """ Testing the code.  """
    import matplotlib.pyplot as plt
    
    piezo = Piezo('z', 15, False, 'ao2', 'ai22')
    sweep_data = piezo.full_sweep(1000)
    plt.plot(sweep_data[0],sweep_data[1])
    plt.show()
    
    
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
   