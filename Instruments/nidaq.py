import sys, os

home = os.path.expanduser("~")
sys.path.append(os.path.join(home,'Documents','GitHub','Instrumental'))

try:
    from instrumental.drivers.daq import ni
    from instrumental import u
except:
    print('instrumental not imported in nidaq.py!')
import numpy as np
try:
    import PyDAQmx as mx
except:
    print('PyDAQmx not imported in nidaq.py!')
import time
from .instrument import Instrument

class NIDAQ(Instrument):
    '''
    For remote operation of the NI DAQ-6363.
    Slightly simplified version of Guen's squidpy driver;
    does not import/inherit anything from squidpy.
    Uses package Instrumental from Mabuchi lab at Stanford
    '''
    _label = 'daq'

    def __init__(self, zero=False, dev_name='Dev1', input_range=10, output_range=10):
        self._daq  = ni.NIDAQ(dev_name, input_range, output_range)
        self._dev_name = dev_name
        self._input_range = input_range
        self._output_range = output_range

        self.setup_inputs()
        self.setup_outputs()

        if zero:
            self.zero()


    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        self._save_dict = {}
        # for chan in self._ins + self._outs:
        #     self._save_dict[chan] = getattr(self, chan).V
        self._save_dict.update({
            '_device_name': self._dev_name,
            '_input_range': self._input_range,
            '_output_range': self._output_range,
            '_inputs': self.inputs,
            '_outputs': self.outputs,
        })

        return self._save_dict

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
        Getter:
        Makes a dictionary with keys = input channel labels, values = input channel objects
        To get the voltage of a channel by using the label, you would do something like:
            daq.inputs['squid'].V
        This is written as a property in case you decide to manually change the label of a channel.

        Setter:
        Set a bunch of input channel labels at once. d is a dictionary with keys = input channel labels, values = input channel real names
        e.g. {'squid': 'ai0'}
        '''
        self._inputs = {}
        for label, name in self.input_names.items():
            self._inputs[label] = getattr(self, name)
        return self._inputs


    @inputs.setter
    def inputs(self, d):
        '''
        Set a bunch of input channel labels at once. d is a dictionary with keys = input channel labels, values = input channel real names
        e.g. {'squid': 'ai0'} or {'squid': 0}
        '''
        for label, name in d.items():
            if type(name) is int:
                name = 'ai%i' %name
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
        Getter:
        Makes a dictionary with keys = output channel labels, values = output channel objects
        To set the voltage of a channel by using the label, you would do something like:
            daq.outputs['x'].V = 1

        Setter:
        Set a bunch of output channel labels at once. d is a dictionary with keys = output channel labels, values = output channel real names
        e.g. {'piezo x': 'ao0'}
        '''
        self._outputs = {}
        for label, name in self.output_names.items():
            self._outputs[label] = getattr(self, name)
        return self._outputs


    @outputs.setter
    def outputs(self, d):
        '''
        Set a bunch of output channel labels at once. d is a dictionary with keys = output channel labels, values = output channel real names
        e.g. {'piezo x': 'ao0'} or {'piezo x': 0}
        '''
        for label, name in d.items():
            if type(name) is int:
                name = 'ao%i' %name
            getattr(self, name).label = label


    @property
    def output_names(self):
        '''
        Returns a dictionary mapping output channel labels (keys) to the
        real channel names (values).
        '''
        self._output_names = {}
        for chan in self._outs:
            self._output_names[getattr(self, chan).label] = chan
        return self._output_names


    def monitor(self, chan_in, duration, sample_rate=100):
        '''
        Monitor any number of channels for a given duration.

        Example:

        Arguments:
            chan_in (list): channels for DAQ to monitor
            duration (float): acquisition time in seconds
            sample_rate (float): frequency of measurement

        Returns:
            dict: Voltages and measurement times for each channel
        '''
        if np.isscalar(chan_in):
            chan_in = [chan_in]

        # Prepare "data" for the Task. Send the current value of ao0
        # and tell the DAQ to output that value of ao0 for every data
        # point.
        numsteps = int(duration*sample_rate)
        data = {'t': np.array([0]*numsteps)}  ## HACK: This data is not used and just converted back to a duration in send_receive

        received = self.send_receive(data, chan_in=chan_in, sample_rate=sample_rate)

        return received


    def send_receive(self, data, chan_in=None, sample_rate=100):
        '''
        Send data to daq outputs and receive data on input channels.
        Data should be a dictionary with keys that are output channel labels or names
        and values can be float, list, or np.ndarray.
        Key can also be time, in which case the data will be converted to a
        duration using len(data['t'])/sample_rate = num_seconds
        Arrays should be equally sized for all output channels.
        chan_in is a list of all input channel labels or names you wish to monitor.
        '''
        try:
            # Make everything a numpy array
            data = data.copy() # so we don't modify original data

            no_output = False
            if 't' in data:
                no_output = True  # sending "t" suggests we do not want to write to output channels
                len_data = len(data.pop('t'))

            for key, value in data.items():
                value = value.copy() # so we don't modify original data
                if np.isscalar(value):
                    value = np.array([value])
                elif type(value) is list:
                    value = np.array(value)

                # Make sure daq does not go out of range
                absmax = abs(value).max()
                if absmax > self._output_range:
                    value = np.clip(value, -self._output_range, self._output_range)
                    print('%s is out of range for DAQ with output range %s! Set to max output.' %(absmax,self._output_range))

                # Repeat the last data point.
                # The DAQ for some reason gives data points late by 1. (see later)
                value = np.append(value, value[-1])

                # Add units for Instrumental
                value = value * u.V

                data[key] = value

            # Make sure there's at least one input channel (or DAQmx complains)
            if chan_in is None:
                chan_in = ['ai23'] # just a random channel
            elif np.isscalar(chan_in):
                chan_in = [chan_in]

            # Need to copy chan_in to ensure names don't change!
            chan_in = chan_in.copy()

            # Convert to real channel names
            output_labels = list(data.keys())
            for label in output_labels:
                if label in self.output_names: # this means we've labeled it something other than the channel name
                    data[self.output_names[label]] = data.pop(label) # replaces custom label with real channel name

            input_labels = chan_in.copy()
            for label in input_labels:
                if label in self.input_names: # this means we've used a custom label
                    chan_in.remove(label)
                    chan_in.append(self.input_names[label])

            # prepare a NIDAQ Task
            taskargs = tuple([getattr(self._daq, ch) for ch in list(data.keys()) + chan_in])
            task = ni.Task(*taskargs)
            if no_output:
                task.set_timing(n_samples = len_data, fsamp='%fHz' %sample_rate)  ## HACK
            else:
                some_data = next(iter(data.values())) # All data must be equal length, so just choose one.  ## HACK
                task.set_timing(n_samples = len(some_data), fsamp='%fHz' %sample_rate)  ## HACK:

            # run the task and remove units
            received = task.run(data)
            for key, value in received.items():
                received[key] = value.magnitude

            # Undo added data point
            # The daq gives data late by one.
            # This only happens on the lowest numbered input channel.
            # the nowacklab branch of Instrumental is modified so that channels
            # are ordered, and in this case it's the lowest numbered channel.
            # First we find the input channel numbers as ints, then find the min.
            ch_nums = [int(''.join(x for x in y if x.isdigit())) for y in chan_in]
            min_chan = 'ai%i' %min(ch_nums)

            for chan, value in received.items():
                if chan == min_chan:
                    received[chan] = np.delete(value, 0)  # removes first data point, which is wrong
                else:
                    received[chan] = np.delete(value,-1)  # removes last data point, a duplicate

            received2 = received.copy()
            for chan, value in received2.items():
                if chan not in input_labels and chan is not 't':
                    received[getattr(self, chan).label] = received.pop(chan)  # change back to the given channel labels if different from the real channel names

            return received
        except Exception as e:
            print('Daq send_receive failed! Make sure your version of nowacklab/Instrumental is current!')
            raise e


    def setup_inputs(self):
        self._ins = self._daq.get_AI_channels()
        for chan in self._ins:
            setattr(self, chan, InputChannel(self._daq, name=chan))


    def setup_outputs(self):
        self._outs = self._daq.get_AO_channels()
        for chan in self._outs:
            setattr(self, chan, OutputChannel(self._daq, name=chan))


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

        sent = '%s' %output_data.keys()

        received = self.send_receive(output_data, chan_in, sample_rate=sample_rate)

        if chan_in is not None:
            for k in received.keys():
                if k not in chan_in and k != 't':
                    raise Exception('DAQ channel name error! Sent keys: %s, Expected keys: %s, Received: %s' %(sent, chan_in, received.keys()))

        return output_data, received


    def zero(self, rate=100000, numsteps=100000):
        for chan in self.outputs.values(): # loop over output channel objects
            self.sweep({chan.label: chan.V}, {chan.label: 0}, sample_rate=rate, numsteps=numsteps)
        print('Zeroed DAQ outputs.')


class Channel(Instrument):
    _V = 0
    _conversion = 1 # build in conversion factor?
    def __init__(self, daq, name):
        '''
        daq = NIDAQ from Instrumental library
        name = channel name (ai# or ao#)
        '''
        self._daq = daq
        self.label = name # default label
        self._name = name # channel name ('ao#' or 'ai#'). Should not change.


    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        self._save_dict = {}
        self._save_dict.update({
            '_V': self._V,
            '_label': self.label,
            '_name': self._name
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
