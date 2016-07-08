import sys, os

sys.path.append(os.path.expanduser("~")+r'\Documents\GitHub\Instrumental')

from instrumental.drivers.daq import ni
from instrumental import u
import numpy
import PyDAQmx as mx
import time
from copy import copy

class NIDAQ():
    '''
    For remote operation of the NI DAQ-6363. Slightly simplified version of Guen's squidpy driver, does not import/inherit anything from squidpy. Uses package Instrumental from Mabuchi lab at Stanford
    '''
    
    def __init__(self, zero=False, freq=100, dev_name='Dev1', input_range=10, output_range=10):
        self._daq  = ni.NIDAQ(dev_name, input_range, output_range)
        self._freq = {}
            
        for chan in self._daq.get_AI_channels():
            setattr(NIDAQ,chan,property(fget=eval('lambda self: self.get_chan(\'%s\')' %chan))) # set up property for input channels NIDAQ.ai#(0-31)
        
        for chan in self._daq.get_AO_channels():
            setattr(self, '_%s' %chan, None)# privately store value
            # The following line works with instrumental modified to add read function to AnalogOut
            setattr(NIDAQ,chan,property(fset=eval('lambda self, value: self.set_chan(\'%s\',value)' %chan), fget=eval('lambda self: self.get_chan(\'%s\')' %chan)))
            # This works with instrumental after names of input channels added manually
            # setattr(NIDAQ,chan,property(fset=eval('lambda self, value: self.set_chan(\'%s\',value)' %chan), fget=eval('lambda self: self.get_chan(\'_%s_vs_aognd\')' %chan)))
            # This works with the current code, since I couldn't figure out internal channels with instrumental:
            # setattr(NIDAQ,chan,property(fset=eval('lambda self, value: self.set_chan(\'%s\',value)' %chan), fget=eval('lambda self: self.get_internal_chan(\'%s\')' %chan))) #property for output channels NIDAQ.ao# (0-3); monitor using internal channels
            self._freq[chan] = freq

            # DEBUG
        # for chan in ['ao0_vs_aognd', 'ao1_vs_aognd']:
            # setattr(self._daq, chan, ni.AnalogIn(self._daq, '%s'%chan))
            # setattr(NIDAQ,chan,property(fget=eval('lambda self: self.get_chan(\'%s\')' %chan)))
            # print(chan)
         
        self.inputs_to_monitor = ['ai23']# at least monitor one input
        
        if zero:
            self.zero()
            
    @property
    def freq(self):
        return self._freq
        
    @freq.setter
    def freq(self, value):
        self._freq = value      

    def accel_function(self, start,end, numpts):
        """ Does an x**2-like ramp. Code looks weird but test it if you want! ^_^ """
        if start == end:
            return [start]*numpts*2 # just return array of the same value 
        part1arg = numpy.linspace(start, (end-start)/2+start, numpts)
        part2arg = numpy.linspace((end-start)/2+start, end, numpts)
        part1 = start+ (part1arg-start)**2/((end-start)/2)**2*(end-start)/2
        part2 = end-(part2arg-end)**2/((end-start)/2)**2*(end-start)/2
        return list(part1)+list(part2[1:])
        
    def add_input(self, inp):
        if inp not in self.inputs_to_monitor:
            self.inputs_to_monitor.append(inp)
        
    def get(self):
        for chan in self._daq.get_AO_channels() + self._daq.get_AI_channels():
            print('%s: ' %chan, getattr(self, chan),'\n')
            
    def get_chan(self, chan):
        return getattr(self._daq,chan).read().magnitude

    def set_chan(self, chan, data):
        setattr(self, '_%s' %chan, data)
        if numpy.isscalar(data):
            getattr(self._daq,chan).write('%sV' %data)
    
    def monitor(self, chan_in, duration, freq=100): # similar to send_receive definition; haven't yet built in multiple channels
        if numpy.isscalar(chan_in):
            chan_in = [chan_in]

        for ch in chan_in:
            self.add_input(ch)
        
        numsteps = duration*freq
        V, response, time = self.sweep('ao0', self.ao0, self.ao0, freq=freq, numsteps=numsteps)
        
        return response, time
        
        # """ Monitor an input channel for a duration of time (s). 
            # e.g. V = daq.monitor('ai4', 10); V[0] is the voltage            """
        # if numpy.isscalar(chan_in):
            # chan_in = [chan_in]

        # for ch in chan_in:
            # self.add_input(ch)
            
        # received = getattr(self._daq, chan_in[0]).read(duration = '%fs' %duration, fsamp='%fHz' %freq)
        # print(received)
        # return [list(received[b''].magnitude),list(received['t'].magnitude),received] # this is a hack, b'' should really be an ai# channel, but I think Instrumental is handling the name wrong.
     
    
    def send_receive(self, chan_out, orig_data, freq=100):
        """
         chan_out is list of output channel names, data is list of datasets sent to each channel, in order
         """
        # gotta make these all lists, following code assumes they are list or dict
        data = copy(orig_data) # so we don't modify original data
        
        if numpy.isscalar(chan_out):
            data = {chan_out: data}
            chan_out = [chan_out]

        if len(chan_out) != len(data):
            raise Exception('Must have data for each output channel!')

        taskargs = tuple([getattr(self._daq, ch) for ch in chan_out + self.inputs_to_monitor])
        task = ni.Task(*taskargs) # * will take tuple as args
        write_data = {}
       
        
        for ch in chan_out: # handle outputs for each channel
            d = data[ch]
            setattr(self, ch, d[0]) # initialize output
       
            # Weird thing to fix daq issue giving data points late by 1.. appears to only happen with lowest numbered output listed :/
            d = list(d) 
            d = d + [d[len(d)-1]]
            # if ch == min_chan: # the lowest numbered channel
                # d = d + [d[len(d)-1]] # For the first one, the first data point is garbage, let's send the last data point twice to get that extra point again
            # else:
                # d = [d[0]] + d #Every other one is fine, so let's just duplicate the first point and get rid of it later
            data[ch] = d
            write_data[ch] = d * u.V # u.V is units, done to make Instrumental happy
   
        task.set_timing(n_samples = len(data[chan_out[0]]), fsamp='%fHz' %freq) 

        received = task.run(write_data)
        data_in = {}
        
        # Find lowest number channel, need to do this because the lowest number input channel will have garbage point. it's the lowest number because I modded instrumental to order them from low to high. It's really whichever channel is specified first.
        ch_nums = [int(''.join(x for x in y if x.isdigit())) for y in self.inputs_to_monitor] #finds the channel numbers    
        min_chan = 'ai%i' %min(ch_nums)
        
        for ch in self.inputs_to_monitor:
            d = received[ch].magnitude #.magnitude from pint units package; 
            if ch == min_chan:#self.inputs_to_monitor[0]:
                data_in[ch] = list(d[1:len(d)]) # get rid of the first data point because of the weird thing we died earlier
            else:
                data_in[ch] = list(d[0:len(d)-1]) # last data point should be a dupe
        time = received['t'].magnitude
        
        return data_in, list(time[0:len(time)-1]) #list limits undo extra point added for daq weirdness
        
    def sweep(self, chan_out, Vstart, Vend, freq=100, numsteps=1000, accel=False):  
        """ e.g. V, response, time = daq.sweep('ao1', -1, 1) """
        if numpy.isscalar(chan_out): #Make these dicts and lists
            Vstart = {chan_out: Vstart}
            Vend = {chan_out: Vend}
            chan_out = [chan_out]

        # for cha in chan_out:
            # if cha not in self.inputs_to_monitor:
                # self.inputs_to_monitor.append(cha)
        
        V = {}       
        for k in Vstart.keys():        
            V[k] = list(numpy.linspace(Vstart[k], Vend[k], numsteps))
            if max(abs(Vstart[k]), abs(Vend[k])) > 10:
                raise Exception('NIDAQ out of range!')
            if accel:
                numaccel = 250
                V[k][:0] = self.accel_function(0, V[k][0], numaccel) # accelerate from 0 to first value of sweep
                V[k] = V[k] + self.accel_function(V[k][-1], 0, numaccel) # accelerate from last value of sweep to 0
            
        response, time = self.send_receive(chan_out, V, freq=freq)
        
        # Trim off acceleration
        if accel:
            for k in V.keys():
                V[k] = V[k][2*numaccel-1:-2*numaccel+1] # slice off first 2*numaccel+1 and last 2*numaccel+1 points
            response = response[2*numaccel-1:-2*numaccel+1]
            time = time[2*numaccel-1:-2*numaccel+1]
         
        return V, response, time
        
    def zero(self):
        for chan in self._daq.get_AO_channels():
            self.sweep(chan, getattr(self, chan), 0, freq=100000)
        print('Zeroed outputs')
                        
    def get_internal_chan(self, chan):
        """
        Modifies example of PyDAQmx from https://pythonhosted.org/PyDAQmx/usage.html#task-object .
        """
        analog_input = mx.Task()
        read = mx.int32()
        data = numpy.zeros((1,), dtype=numpy.float64)

        # DAQmx Configure Code
        analog_input.CreateAIVoltageChan("Dev1/_%s_vs_aognd" %chan,"",mx.DAQmx_Val_Cfg_Default,-10.0,10.0,mx.DAQmx_Val_Volts,None)
        analog_input.CfgSampClkTiming("",10000.0,mx.DAQmx_Val_Rising,mx.DAQmx_Val_FiniteSamps,2)

        # DAQmx Start Code
        analog_input.StartTask()

        # DAQmx Read Code
        analog_input.ReadAnalogF64(1000,10.0,mx.DAQmx_Val_GroupByChannel,data,1000,mx.byref(read),None)
       
        x = data[0]
        return 0 if abs(x) < 1/150 else x # Stupid way to get around crashing at end of execution. If value returned is too small yet still nonzero, program will crash upon completion. Manually found threshold. It's exactly 1/150. No clue why.
        
    def get_internal_chan_old(self, chan):      
        """
        Modifies example of PyDAQmx from https://pythonhosted.org/PyDAQmx/usage.html#task-object . There was a simpler version that I didn't notice before, now that one is implemented above.
        """
        print('start get chan %s' %chan)
        # Declaration of variable passed by reference
        taskHandle = mx.TaskHandle()
        read = mx.int32()
        data = numpy.zeros((1,), dtype=numpy.float64)

        try:
            # DAQmx Configure Code
            mx.DAQmxCreateTask("",mx.byref(taskHandle))
            mx.DAQmxCreateAIVoltageChan(taskHandle,"Dev1/_%s_vs_aognd" %chan,"",mx.DAQmx_Val_Cfg_Default,-10.0,10.0,mx.DAQmx_Val_Volts,None)
            mx.DAQmxCfgSampClkTiming(taskHandle,"",10000.0,mx.DAQmx_Val_Rising,mx.DAQmx_Val_FiniteSamps,2)

            # DAQmx Start Code
            mx.DAQmxStartTask(taskHandle)

            # DAQmx Read Code
            mx.DAQmxReadAnalogF64(taskHandle,1000,10.0,mx.DAQmx_Val_GroupByChannel,data,1000,mx.byref(read),None)

        except mx.DAQError as err:
            print ("DAQmx Error: %s"%err)
        finally:
            if taskHandle:
                # DAQmx Stop Code
                mx.DAQmxStopTask(taskHandle)
                mx.DAQmxClearTask(taskHandle)
        print('end get chan %s' %chan)

        return float(data[0])
        
        
        
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