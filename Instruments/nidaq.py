import sys, os

home = os.path.expanduser("~")
sys.path.append(os.path.join(home,'Documents','GitHub','Instrumental'))

from instrumental.drivers.daq import ni
from instrumental import u
import numpy as np
try:
    import PyDAQmx as mx
except:
    print('PyDAQmx not imported!')
import time
from copy import copy
from ..Utilities import logging

class NIDAQ():
    '''
    For remote operation of the NI DAQ-6363.
    Slightly simplified version of Guen's squidpy driver;
    does not import/inherit anything from squidpy.
    Uses package Instrumental from Mabuchi lab at Stanford
    '''

    def __init__(self, zero=False, dev_name='Dev1', input_range=10, output_range=10):
        self._daq  = ni.NIDAQ(dev_name, input_range, output_range)
        self._dev_name = dev_name
        self._input_range = input_range
        self._output_range = output_range

        self._ins = self._daq.get_AI_channels()
        self._outs = self._daq.get_AO_channels()

        for chan in self._ins:
            setattr(self, chan, InputChannel(self._daq, name=chan))

        for chan in self._outs:
            setattr(self, chan, OutputChannel(self._daq, name=chan))

        if zero:
            self.zero()


    def __getstate__(self):
        self._save_dict = {}
        for chan in self._ins + self._outs:
            self._save_dict[chan] = getattr(self, chan).V
        self._save_dict.update({
            'device name': self._dev_name,
            'input range': self._input_range,
            'output range': self._output_range
        })

        return self._save_dict


    def __setstate__(self, state):
        self._daq = ni.NIDAQ(state['device name'], state['input range'], state['output range'])


    def accel_function(self, start,end, numpts):
        """ Does an x**2-like ramp. Code looks weird but test it if you want! ^_^ """
        '''
        NO THIS IS ACTUALLY CRAP DON'T USE THIS
        '''
        if start == end:
            return [start]*numpts*2 # just return array of the same value
        part1arg = np.linspace(start, (end-start)/2+start, numpts)
        part2arg = np.linspace((end-start)/2+start, end, numpts)
        part1 = start+ (part1arg-start)**2/((end-start)/2)**2*(end-start)/2
        part2 = end-(part2arg-end)**2/((end-start)/2)**2*(end-start)/2
        return list(part1)+list(part2[1:])


    def all(self):
        '''
        Returns a dictionary of all channel voltages.
        '''
        voltages = {}
        for chan in self._ins + self._outs:
            voltages[chan] =  getattr(self, chan).V
        return voltages


    @property
    def inputs(self):
        '''
        Makes a dictionary with keys = input channel labels, values = input channel objects
        To get the voltage of a channel by using the label, you would do something like:
            daq.inputs['squid'].V
        This is written as a property in case you decide to manually change the label of a channel.
        '''
        self._inputs = {}
        for label, name in self.input_names.items():
            self._inputs[label] = getattr(self, name)
        return self._inputs


    @inputs.setter
    def inputs(self, d):
        '''
        Set a bunch of input channel labels at once. d is a dictionary with keys = input channel labels, values = input channel real names
        e.g. {'squid': 'ai0'}
        '''
        for label, name in d.items():
            getattr(self, name).label = label


    @property
    def input_names(self):
        '''
        Returns a dictionary mapping input channel labels (keys) to the real channel names (values).
        '''
        self._input_names = {}
        for chan in self._ins:
            self._input_names[getattr(self, chan).label] = chan
        return self._input_names


    @property
    def outputs(self):
        '''
        Makes a dictionary with keys = output channel labels, values = output channel objects
        To set the voltage of a channel by using the label, you would do something like:
            daq.outputs['x'].V = 1
        '''
        self._outputs = {}
        for label, name in self.output_names.items():
            self._outputs[label] = getattr(self, name)
        return self._outputs


    @outputs.setter
    def outputs(self, d):
        '''
        Set a bunch of output channel labels at once. d is a dictionary with keys = output channel labels, values = output channel real names
        e.g. {'piezo x': 'ao0'}
        '''
        for label, name in d.items():
            getattr(self, name).label = label


    @property
    def output_names(self):
        '''
        Returns a dictionary mapping output channel labels (keys) to the real channel names (values).
        '''
        self._output_names = {}
        for chan in self._outs:
            self._output_names[getattr(self, chan).label] = chan
        return self._output_names


    def monitor(self, chan_in, duration, sample_rate=100):
        '''
        Monitor any number of channels for a given duration, sampling at sample_rate.
        Default 100 Hz sample rate.
        '''
        if np.isscalar(chan_in):
            chan_in = [chan_in]

        ## Prepare "data" for the Task. We'll just send the current value of ao0
        ## and tell the DAQ to output that value of ao0 for every data point.
        numsteps = int(duration*sample_rate)
        current_ao0 = self.ao0.V
        data = {'ao0': np.array([current_ao0]*numsteps)}

        received = self.send_receive(data, chan_in=chan_in, sample_rate=sample_rate)

        return received


    def send_receive(self, data, chan_in=None, sample_rate=100):
        '''
        Send data to daq outputs and receive data on input channels.
        Data should be a dictionary with keys that are output channel labels or names
        and values can be float, list, or np.ndarray.
        Arrays should be equally sized for all output channels.
        chan_in is a list of all input channel labels or names you wish to monitor.
        '''
        ## Make everything a numpy array
        data = data.copy() # so we don't modify original data
        for key, value in data.items():
            value = value.copy() # so we don't modify original data
            if np.isscalar(value):
                value = np.array([value])
            elif type(value) is list:
                value = np.array(value)

            ## Make sure daq does not go out of range
            absmax = abs(value).max()
            if absmax > self._output_range:
                raise Exception('%s is out of range for DAQ with output range %s!' %(absmax,self._output_range))

            ## Repeat the last data point.
            ## The DAQ for some reason gives data points late by 1. (see later)
            value = np.append(value, value[-1])

            ## Add units for Instrumental
            value = value * u.V

            data[key] = value


        ## Make sure there's at least one input channel (or DAQmx complains)
        if chan_in is None:
            chan_in = ['ai23'] # just a random channel
        elif np.isscalar(chan_in):
            chan_in = [chan_in]

        ## Convert to real channel names
        output_labels = list(data.keys())
        for label in output_labels:
            if label in self.output_names: # this means we've labeled it something other than the channel name
                data[self.output_names[label]] = data.pop(label) # replaces custom label with real channel name

        input_labels = chan_in.copy()
        for label in input_labels:
            if label in self.input_names: # this means we've used a custom label
                chan_in.remove(label)
                chan_in.append(self.input_names[label])

        ## prepare a NIDAQ Task
        taskargs = tuple([getattr(self._daq, ch) for ch in list(data.keys()) + chan_in])
        task = ni.Task(*taskargs)
        some_data = next(iter(data.values())) # All data must be equal length, so just choose one.
        task.set_timing(n_samples = len(some_data), fsamp='%fHz' %sample_rate)

        ## run the task and remove units
        received = task.run(data)
        for key, value in received.items():
            received[key] = value.magnitude

        ## Undo added data point
        ## The daq gives data late by one.
        ## This only happens on the lowest numbered input channel.
        ## the nowacklab branch of Instrumental is modified so that channels
        ## are ordered, and in this case it's the lowest numbered channel.
        # First we find the input channel numbers as ints, then find the min.
        ch_nums = [int(''.join(x for x in y if x.isdigit())) for y in chan_in]
        min_chan = 'ai%i' %min(ch_nums)

        for chan, value in received.items():
            if chan == min_chan:
                received[chan] = np.delete(value, 0) #removes first data point, which is wrong
            else:
                received[chan] = np.delete(value,-1) #removes last data point, a duplicate
            if chan not in input_labels and chan is not 't':
                received[getattr(self, chan).label] = received.pop(chan) # change back to the given channel labels if different from the real channel names

        return received


    def sweep(self, Vstart, Vend, chan_in=None, sample_rate=100, numsteps=1000):
        '''
        Sweeps between voltages specified in Vstart and Vend, dictionaries with
        output channel labels or names as keys. (e.g. Vstart={'ao1':3, 'piezo z':4})
        Specify the input channels you want to monitor by passing in input channel labels or names.
        Returns (output voltage dictionary, input voltage dictionary)
        '''

        output_data = {}
        for k in Vstart.keys():
            output_data[k] = np.linspace(Vstart[k], Vend[k], numsteps)

        received = self.send_receive(output_data, chan_in, sample_rate=sample_rate)

        return output_data, received


    def zero(self):
        for chan in self.outputs.values(): # loop over output channel objects
            self.sweep({chan.label: chan.V}, {chan.label: 0}, sample_rate=100000, numsteps=100000)
        print('Zeroed DAQ outputs.')
        logging.log('Zeroed DAQ outputs.')


class Channel():
    _V = 0
    def __init__(self, daq, name):
        '''
        daq = NIDAQ from Instrumental library
        name = channel name (ai# or ao#)
        '''
        self._daq = daq
        self.label = name # default label
        self._name = name # channel name ('ao#' or 'ai#'). Should not change.


    def __getstate__(self):
        self._save_dict = {}
        self._save_dict.update({
            'V': self._V,
            'label': self.label,
            'name': self._name
        })

        return self._save_dict


    def __repr__(self):
        return str(self.__class__.__name__) + '; name: '+ self._name+'; label: ' + self.label + '; V = %.3f' %self.V


class InputChannel(Channel):
    def __init__(self, daq, name):
        super().__init__(daq, name)

    @property
    def V(self):
        self._V = getattr(self._daq, self._name).read().magnitude
        return self._V


class OutputChannel(Channel):
    def __init__(self, daq, name):
        super().__init__(daq, name)

    @property
    def V(self):
        self._V = getattr(self._daq, self._name).read().magnitude
        return self._V

    @V.setter
    def V(self, value):
        self._V = value
        getattr(self._daq,  self._name).write('%sV' %value) # V is for pint units used in Instrumental package


if __name__ == '__main__':
    '''
    Out of date 11/3/2016
    '''
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
