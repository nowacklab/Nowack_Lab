from __future__ import print_function
import time
from ..Utilities.save import Measurement
import numpy as np
from IPython.display import clear_output
import sys
from ..Utilities.dataset import Dataset

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

    def __init__(self, name, pathtosave = '/', bi = True,
                                    saveasyougo = False, saveatend = True):
        self.repeaters = []
        self.sweeps_data = []
        self.name = name
        self.ns = []
        self.bi = bi
        self.saveasyougo = saveasyougo
        if (saveasyougo or saveatend) and not filename:
            raise Exception('Must specify filename for saving')
        elif saveasyougo or saveatend :
            self.savedata = Datasaver(name)
        self.saveatend = saveatend


    def __call__(self, n):
        '''
        Runs the sweep, appending the sweep data to self.sweeps_data.
        '''
        if n in self.ns:
            shoulduse = input('This n has already been used. If you want to use'
                              +' it anyway, overwriting data, type OVERWRITE. '
                              + 'Otherwise, type another n to use')
            if shoulduse == 'OVERWRITE':
                pass
            else:
                n = shoulduse
        self.ns.append(n)
        sweep_data = []
        if self.waiter:
            self.waiter.reset()
        for point in  range(self.points):
            clear_output()
            print('On point ' + str(point) +
                                        ' out of ' + str(self.points))
            sweep_data.append({})
            for r in self.repeaters:
                if(self.waiter and self.waiter.test(n)):
                    break
                if hasattr(r,"name"):
                    sweep_data[point][r.name] = r(point)
                    if self.saveasyougo:
                        self.savedata.append(self.pathtosave
                                + '\%i\%s' % (point, r.name), r(point))
                else:
                    r(point)
        if self.bi:
            for point in  range(self.points):
                clear_output()
                print('On point ' + str(point) +
                                        ' out of ' + str(self.points))
                sweep_data.append({})
                for r in self.repeaters:
                    if(self.waiter and self.waiter.test(n)):
                        break
                    if hasattr(r,"name"):
                        sweep_data[point + self.points][r.name] = r(
                                                self.points - point - 1)
                        if self.saveasyougo:
                            self.savedata.append(self.pathtosave
                            + '\%i\%s' % (point + self.points, r.name),
                                     r(self.points - point - 1))
                    else:
                        r(self.points - point)



        if self.saveatend:
            self.savedata.append(self.pathtosave, sweep_data)
            self.save()
        return sweep_data

    def run(self):
        '''
        Runs the sweep. This is used only if the sweep is the outermost one.
        If neither saveasyougo or saveatend is enabled, enables saveatend.
        '''
        if not (self.saveasyougo or self.saveatend):
            self.saveatend = True
        self.__call__(0)
        stufftosave = input('Please enter any description you want to save: ')
        self.savedata.append(self.pathtosave + '\description', stufftosave)

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
            elif isinstance(repeater, Delayer):
                description += ('delays execution for %f seconds '
                                % repeater.delay )
            description += ('then ')
        description += ('repeats.')
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

    def remove_all_repeaters(self):
        '''
        Remove all repeaters
        '''
        self.repeaters = []

    def set_points(self, points, waiter = False):
        '''
        Sets the number of points to take. All array based repeaters must have
        enough data points for the given number of points. If waiter is set
        to a wait object, the sweep will terminate when that wait object's
        test as applied to the nth element of it's values is true.
        '''
        self.points = points
        self.waiter = waiter

    def process_data(self, sweepnum, listofkeys, sweepdata = False):
        '''
        Returns a one d array of the data at location list of keys from the
        sweepnum-th sweep
        '''
        if not sweepdata:
            sweepdata = self.sweeps_data
        sweep = sweepdata[sweepnum]
        data = []
        for key in range(len(sweep.keys())):
            elem =  sweep[str(key)]
            processed = np.zeros(len(listofkeys))
            for i in range(len(listofkeys)):
                processed[i] = elem[listofkeys[i]]
                data.append(processed)
        return data

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
    def restart(self, n):
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
        if not self.hasbeencalled:
            self.hasbeencalled = True
            self.start_time = time.time()
        while(self.seconds() < self.times[n]):
            pass
        return self.seconds()

class Delayer(Measurement):
    '''
    Delays execution for a fixed amount of time
    '''

    def __init__(self, delay):
        self.delay = delay

    def __call__(self, n):
        starttime = time.time()
        while(time.time() - starttime<self.delay):
            pass


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
        self.timetoaccept = timetoaccept
        self.start_time_in_range = False

    def reset(self):
        '''
        Resets the timer on acceptance so that the test can be used multiple
        times. This is unnecessary if the waiter is called itself.
        '''
        self.start_time_in_range = False

    def insttest(self, n):
        currst = getattr(self.obj, self.prop)
        if self.elem:
            currst = currst[self.elem]
        self.currst = currst
        if self.valence == -1:
            test = currst <= self.values[n]
        elif self.valence == 1:
            test = currst >= self.values[n]
        elif self.valence == 0:
            test = abs(currst - self.values[n]) < self.tolerance
        else:
            raise Exception('Valence must be -1,1 or 0')
        return test

    def test(self, n):
        if not self.insttest(n) or not self.start_time_in_range:
            self.start_time_in_range = time.time()
            return False
        elif self.insttest(n) and ((time.time() - self.start_time_in_range)
                                                    >  self.timetoaccept):
            return True
        else:
            return False


    def __call__(self, n):
        tstart = time.time()
        start_time_in_range = tstart
        print('Waiting to ' + self.name)
        while(True):
            if time.time()- tstart > self.timeout:
                raise Exception('Waiting timed out at value '
                    + str(self.values[n]) + ' of waiter ' + self.name)
            if self.test(n):
                print('Done')
                break
        return time.time() - tstart
