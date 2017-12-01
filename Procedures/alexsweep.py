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

    def __call__(self):
        data = {}
        for obj in self.datatypes:
            data[obj.name] = obj
        return data

    def add_datatype(self, add_me):
        '''
        Adds a data type to the recorder.
        '''
        self.datatypes.append(add_me)

    def remove_datatype(self, remove_me):
        '''
        Removes a data type from the recorder
        '''
        self.datatypes.remove(remove_me)
    def list_datatypes(self):
        '''
        Lists the datatypes included in the recorder.
        '''
        for obj in self.datatypes:
            print(obj.name)

class Sweep(Measurement):

    def __init__(self):
        self.repeaters = []
        self.is_active = True;
        self.sweeps_data = []

    def __call__(self):
        '''
        Runs the sweep, appending the sweep data to self.sweeps_data.
        '''
        if is_active:
            sweep_data = {}
            for value in self.values_to_take:
                self.active = value;
                sweep_data[value] = {}
                for r in repeaters:
                    sweep_data[n][r.name] = r
            self.sweeps_data.append[sweep_data]
        else:
            for n in range(self.points):
                self.active = value;
                sweep_data[n] = {}
                for r in repeaters:
                    sweep_data[n][r.name] = r
        self.sweeps_data.append[sweep_data]
    def active(self, object_to_sweep, values_to_take):
        '''
        Sets the active to be swept. There may only be one!
        Object to sweep must have a name attribute.
        '''
        self.values_to_take = values_to_take
        self.object_to_sweep = object_to_sweep

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
