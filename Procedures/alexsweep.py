from __future__ import print_function
import time
from ..Utilities.save import Measurement
import numpy as np
import zhinst.utils
import sys

class Recorder(Measurement):
    '''
    Records some parameters. Usually is the repeater for the inner most
    sweep in a sweep chain. Calling the recorder runs it, and returns the data.
    '''
    def __init__(self):
        self.datatypes = [];
        self.returns = True

    def __call__(self):
        data = {}
        for elem in self.datatypes:
            data[elem[0]] = getattr(elem[1],elem[2])
        return data

    def add_datatype(self, obj, property):
        '''
        Adds a data type to the recorder.
        '''
        self.datatypes.append([obj.name + ' ' + property, obj, property])

    def remove_datatype(self, obj, property):
        '''
        Removes a data type from the recorder
        '''
        self.datatypes.remove([obj.name + ' ' + property, obj, property])
    def list_datatypes(self):
        '''
        Lists the datatypes included in the recorder.
        '''
        for elem in self.datatypes:
            print(elem[0])

class Sweep(Measurement):

    def __init__(self):
        self.repeaters = []
        self.is_active = True;
        self.sweeps_data = []

    def __call__(self):
        '''
        Runs the sweep, appending the sweep data to self.sweeps_data.
        '''
        if self.is_active:
            sweep_data = {}
            for value in self.values_to_take:
                setattr(self.object_to_sweep, self.property_to_sweep, value)
                sweep_data[value] = {}
                for r in self.repeaters:
                    ret = False
                    try:
                        ret = r.returns
                    except:
                        pass
                    if ret:
                        sweep_data[value][r.name] = r
        else:
            for point in range(self.points):
                sweep_data[point] = {}
                for r in self.repeaters:
                    sweep_data[point][r.name] = r
        self.sweeps_data.append(sweep_data)
    def active(self, obj, prop, values_to_take):
        '''
        Sets the active to be swept. There may only be one!
        Object to sweep must have a name attribute.
        '''
        self.values_to_take = values_to_take
        self.object_to_sweep = obj
        self.property_to_sweep = prop

    def add_repeater(self, add_me):
        '''
        Adds a repeater, i.e., what to do at each point of the sweep. Can be
        another sweep. Repeaters are run in the order they are given. Repeaters
        which accept parameters should be given as lambda functions,
        to delay their execution.
        '''
        self.repeaters.append(add_me)
    def remove_repeater(self, remove_me):
        '''
        Removes a repeater.
        '''
        self.repeaters.remove(remove_me)

    def set_points(self, points):
        '''
        Sets the number of points to take for a passive sweep.
        Will be ignored if active.
        '''
        self.points = points
    def switch_active(self):
        '''
        Changes the sweep from active to passive and vise versa
        '''
        self.is_active = not self.is_active;
        if self.is_active:
            message = 'active'
        else:
            message = 'not active'
        print('the sweep is ' + message)
