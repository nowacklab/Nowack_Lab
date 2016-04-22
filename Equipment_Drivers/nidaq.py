from instrumental.drivers.daq import ni
from instrumental import u
import numpy

class NIDAQ():
    '''
    For remote operation of the NI DAQ-6363. Slightly simplified version of Guen's squidpy driver, does not import/inherit anything from squidpy. Uses package Instrumental from Mabuchi lab at Stanford
    '''
    
    def __init__(self, freq=100, dev_name='Dev1'):
        self._daq  = ni.NIDAQ(dev_name)
        self._freq = {}
    
        for chan in self._daq.get_AI_channels():
            setattr(NIDAQ,chan,property(fget=eval('lambda self: self.get_chan(\'%s\')' %chan))) # set up property for input channels NIDAQ.ai#(0-31)
            
        for chan in self._daq.get_AO_channels():
            setattr(self, '_%s' %chan, None)# privately store value
            setattr(NIDAQ,chan,property(fset=eval('lambda self, value: self.set_chan(\'%s\',value)' %chan), fget=eval('lambda self: getattr(self,\'_%s\')' %chan))) #property for output channels NIDAQ.ao# (0-3)
            self._freq[chan] = freq
    
    @property
    def freq(self):
        return self._freq
        
    @freq.setter
    def freq(self, value):
        self._freq = value
            
    def get_chan(self, chan):
        return getattr(self._daq,chan).read().magnitude

    def set_chan(self, chan, data):
        setattr(self, '_%s' %chan, data)
        if numpy.isscalar(data):
            getattr(self._daq,chan).write('%sV' %data)
    
    def monitor(self, chan_in, duration, freq=100): # similar to send_receive definition
        received = getattr(self._daq, chan_in).read(duration = '%fs' %duration, fsamp='%fHz' %freq)
        data_in = received[bytes(chan_in, 'utf-8')].magnitude
        t = received['t'].magnitude
        return list(data_in), list(t)
    
    def send_receive(self, chan_out, chan_in, data, freq=100):
        setattr(self, chan_out, data[0]) # initialize output
        
        # Weird thing to fix daq issue giving data points late by 1
        data = list(data)
        data = data + [data[len(data)-1]]
        
        task = ni.Task(getattr(self._daq, chan_out), getattr(self._daq, chan_in))
        task.set_timing(n_samples = len(data), fsamp='%fHz' %freq) #CALCULATE DURATION
        write_data = {chan_out: data * u.V}
        received = task.run(write_data)
        
        data_in = received[chan_in].magnitude #.magnitude from pint units package; 
        time = received['t'].magnitude
        return list(data_in[1:len(data_in)]), list(time[0:len(time)-1]) #list limits undo extra point added for daq weirdness
        
    def sweep(self, chan_out, chan_in, Vstart, Vend, Vstep = 0.01, freq=100, numsteps=None):   
        if Vstart == Vend:
            return
        
        if numsteps == None:
            numsteps = int(abs(Vstart-Vend)/Vstep)+1
        else:
            Vstep = (Vend-Vstart)/(numsteps-1)
        
        V = list(numpy.linspace(Vstart, Vend, numsteps))
        if abs(max(V)) > 10:
            raise Exception('NIDAQ out of range!')
            
        response, time = self.send_receive(chan_out, chan_in, V, freq=freq)
         
        return V, response, time
        
        
if __name__ == '__main__':
    nidaq = NIDAQ()
    
    out_data = []
    in_data = []
    num = 100
    vmax = 5
    for i in range(num):
        nidaq.ao3 = vmax*i/num
        out_data.append(nidaq.ao3)
        in_data.append(nidaq.ai3)
    for i in range(num):
        nidaq.ao3 = vmax-vmax*i/num
        out_data.append(nidaq.ao3)
        in_data.append(nidaq.ai3)
    import matplotlib.pyplot as plt
    plt.plot(in_data)
    plt.show()