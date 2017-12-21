from __future__ import print_function
import time
from ..Utilities.save import Measurement
import numpy as np
import zhinst.utils
from IPython.display import clear_output
import sys

class Recorder(Measurement):
    '''
    Records a single parameter. Purpose is to add name functionality and
    wrap in a "sweepable" package. Calling the recorder runs it,
    and returns the data.
    '''
    def __init__(self, obj, prop, name):
        self.obj = obj
        self.prop = prop
        self.name = name

    def __call__(self, n):
        return getattr(self.obj ,self.prop)

class Active(Measurement):
    '''
    Creates an "active" object from a property to be set of some object
    and a 1D array of values to take. Property must be settable, if it is
    gettable class will return its gotten value after setting. Delays code by
    .1 ms to allow properties time to change.
    '''
    def __init__(self, obj, prop, name, array, delay = 1e-4):
        self.prop = prop
        self.obj = obj
        self.array = array
        self.name = name
        self.delay = delay

    def __call__(self, n):
        setattr(self.obj, self.prop, self.array[n])
        try:
            time.sleep(self.delay)
            return getattr(self.obj, self.prop)
        except:
            pass

class Sweep(Measurement):
    '''
    Executes a 1D sweep. Data is always indexed vs point number, time indexes
    and actively swept parameters may be added as Repeaters
    '''

    def __init__(self, name):
        self.repeaters = []
        self.sweeps_data = []
        self.name = name

    def __call__(self, n):
        '''
        Runs the sweep, appending the sweep data to self.sweeps_data and
        returning it.
        '''
        sweep_data = {}
        for point in range(self.points):
            clear_output()
            print('On point ' + str(point) + ' out of ' + str(self.points))
            sweep_data[point] = {}
            for r in self.repeaters:
                sweep_data[point][r.name] = r(point)

        self.sweeps_data.append(sweep_data)
        return sweep_data
    def describe(self):
        '''
        Describes the sweep
        '''

        description = ''
        for repeater in self.repeaters:
            if isinstance(repeater, Active):
                description += ('sweeps %s ' % repeater.name)
            elif isinstance(repeater, Recorder):
                description += ('records %s ' % repeater.name)
            elif isinstance(repeater, Sweep):
                description += ('runs subsweep %s ' % repeater.name)
            elif isinstance(repeater, Time):
                description += ('waits ')
            elif isinstance(repeater, Wait):
                description += ('waits for trip %s' % repeater.name)
            description += ('then ')
        description += ('ends.')
        print(description)

    def add_repeater(self, add_me):
        '''
        Adds a repeater, i.e., what to do at each point of the sweep. Can be
        another sweep. Repeaters are run in the order they are given. Repeaters
        must be Actives, Sweeps, Recorders, Waits or Times.
        '''
        self.repeaters.append(add_me)
    def remove_repeater(self, remove_me):
        '''
        Removes a repeater.
        '''
        self.repeaters.remove(remove_me)

    def set_points(self, points):
        '''
        Sets the number of points to take. All array based repeaters must have
        enough data points for the given number of points.
        '''
        self.points = points

class Time(Measurement):
    '''
    Creates a callable time object which can be used to delay execution
    until a certain time. All times are zeroed to when the instance is
    first called, unless restart is used.
    '''

    def __init__(self, times):
        self.hasbeencalled = False
        self.times = times
        self.name = 'time'
    def restart(self):
        '''
        Resets the zero of time to the next time seconds or waittime is called
        '''
        self.hasbeencalled = False
    def seconds(self):
        '''
        Sets the zero of time the first time it is called, after that,
        returns time since the first time it was called.
        '''
        if self.hasbeencalled:
            return time.time() - self.start_time
        else:
            self.hasbeencalled = True
            self.start_time = time.time()
            return 0.0
    def __call__(self, n):
        '''
        Holds execution until the measuretime passes the element of times given
        in the init at location n.
        '''
        while(self.seconds() < self.times[n]):
            pass
        return self.seconds()

class Wait(Measurement):

    '''
    Will wait until prop of obj is at the
    appropriate value in values. Valence determines if prop must be less
    than, greater than, or within tolerance (-1, 1, 0 respectively) of
    values(n). Must satisfy this condition for timetoaccept.
    '''

    def __init__(self, name, obj, prop, values, elem = False, valence = -1,
                    tolerance = 0, timeout = 10, timetoaccept = 1e-3):

        self.name = name
        self.obj = obj
        self.prop = prop
        self.values = values
        self.elem = elem
        self.valence = valence
        self.tolerance  = tolerance
        self.timeout = timeout
    def test(self):
        currst = getattr(self.obj, self.prop)
        if self.elem:
            currst = currst[self.elem]
        self.currst = currst
        if self.valence == -1:
            test = currst <= self.values[n]
        elif self.valence == 1:
            test = currst >= self.values[n]
        elif self.valence == 0:
            test = abs(currst - self.values[n]) < tolerance
        else:
            raise Exception('Valence must be -1,1 or 0')
        return test
    def __call__(self, n):
        tstart = time.time()
        start_time_in_range = tstart
        while(True):
            if time.time()- tstart > self.timeout:
                raise('Waiting timed out at value ' + str(self.values[n])
                        + ' of waiter ' + self.name)
            if not test:
                start_time_in_range = time.time()
            elif test and (time.time() - start_time_in_range) > timetoaccept:
                break
        return currst

def replace_values(ref, newvalues):
    '''
    Replaces values in a list passed by reference without disturbing
    the reference
    '''
    if len(ref) != len(newvalues):
        raise Exception("newvalues must have the same length as ref!")
    length = len(ref)
    ref.extend(newvalues)
    for i in range(length):
        ref.pop(0)
