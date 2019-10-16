from __future__ import print_function
import time
from ..Utilities.save import Measurement
import numpy as np
from IPython.display import clear_output
import sys
from ..Utilities.dataset import Dataset
from ..Utilities.datasaver import Saver
from datetime import datetime
import copy

class Recorder(Measurement):
    '''
    Records a single parameter. Purpose is to add name functionality and
    wrap in a "sweepable" package. Calling the recorder runs it,
    and returns the data. Returned data may be:

    a) a dictionary with elements of types b) or c)
    b) a float, int or complex
    c) a nd.array or nd.arrayable list of floats complex or ints of arbitrary
        dimensions.
    '''
    def __init__(self, obj, prop, name, key = False):
        self.obj = obj
        self.prop = prop
        self.name = name
        self.returns = True
        self.key = key
        self.preamp = False
        if not hasattr(obj, "__getstate__"):
            print('Passed object does not have a getstate. Instrument '
                                            + 'config will not be saved!')
            self.savestate = False
        else:
            self.savestate = True


    def __call__(self, n):
        if self.key:
            returneddata = getattr(self.obj ,self.prop)[self.key]
        else:
            returneddata = getattr(self.obj ,self.prop)
        return returneddata

    def add_preamp(self, preamp):
        '''
        Associates a preamp with the measurement, ensuring its state is
        saved and that it is recorded that its gain modifies the recorded data
        The saved data will still be the exact returned values from the
        instrument, all mathematical correction for the gain must happen
        in post processing.
        '''

        self.preamp = preamp

    def _getconfig(self):
        config = {'Property recorded' : self.prop,
                  'Key used': self.key}

        if self.savestate:
            config['Instrument Configuration'] = self.obj.__getstate__()
        if self.preamp:
            config['Preamplified'] = self.preamp.__getstate__()
        return config


class Active(Measurement):
    '''
    Creates an "active" object from a property to be set of some object
    and a 1D array of values to take. Property must be settable, if it is
    gettable class will return its gotten value after setting. Delays code by
    .1 ms to allow properties time to change.
    '''
    def __init__(self, obj, prop, name, array, delay = 1e-3):
        self.prop = prop
        self.obj = obj
        self.array = array
        self.returns = True
        self.name = name
        self.delay = delay
        if not hasattr(obj, "__getstate__"):
            print('Passed object does not have a getstate. Instrument '
                                            + 'config will not be saved!')
            self.savestate = False
        else:
            self.savestate = True

    def __call__(self, n):
        setattr(self.obj, self.prop, self.array[n])
        try:
            time.sleep(self.delay)
            return getattr(self.obj, self.prop)
        except:
            pass

    def _getconfig(self):
        config = {'Values swept over' : self.array,
                                                'Property swept': self.prop,}
        if self.savestate:
            config['Instrument Configuration'] = self.obj.__getstate__()
        return config

class Sweep(Measurement):
    '''
    Executes a 1D sweep. Data is always indexed vs point number, time indexes
    and actively swept parameters may be added as Repeaters
    '''

    def __init__(self, name, pathtosave = '/', bi = True, runcount = 1,
                 pausebeforesweep = 0, saveasyougo = False, saveatend = True,
                 svr = False, saveconfig = True):

        if saveatend and saveasyougo:
            raise Exception('only one saving method allowed!')
        self.repeaters = []
        self.name = name
        self.ns = []
        self.bi = bi
        self.sweep_data = {}
        self.runcount = runcount
        self.returns = True
        self.saveasyougo = saveasyougo
        self.pathtosave = pathtosave
        self.pausebeforesweep = pausebeforesweep
        if (saveconfig or saveasyougo or saveatend) and not svr:
            self.savedata = Saver(name)
        elif svr:
            self.savedata = svr
        self.saveatend = saveatend
        self.saveconfig = saveconfig

    def _getconfig(self):
        config = {}
        repeaterorder = []
        for r in self.repeaters:
            repeaterorder.append(r.name)
            if hasattr(r, "_getconfig"):
                cur_config =  r._getconfig()
                config[r.name] = cur_config
        config['repeater order'] = repeaterorder
        return config

    def _setuprepeatersave(self, init, iter, repeater, testdata):
        '''
        Sets up saving of data for one repeater
        '''
        if repeater.returns:
            repeater.issliced = True
            if isinstance(testdata,dict):
                emptytestdata = copy.deepcopy(testdata)
                self.dictvisititems(emptytestdata, self._replacewithempty)
            elif isinstance(testdata, (float, int)):
                emptytestdata = np.full(self.points, np.nan)
            elif isinstance(testdata, (np.ndarray, list)):
                a = list(np.shape(testdata))
                a.insert(0, self.points)
                datashape = tuple(a)
                emptytestdata = np.full(datashape, np.nan)
            else:
                repeater.issliced = False
                self.sweep_data['iteration: ' + str(iter)]['forward'][repeater.name] = {}
                if self.bi:
                    self.sweep_data['iteration: ' + str(iter)]['reverse'][repeater.name] = {}
            if repeater.issliced:
                self.sweep_data['iteration: ' + str(iter)]['forward'][repeater.name] = emptytestdata
                if self.saveasyougo:
                    self.savedata.append(self.pathtosave +
                    'initialization: %s/iteration: %s/forward/%s/'
                    %(str(init),str(iter),  repeater.name), emptytestdata)
                if self.bi:
                    self.sweep_data['iteration: ' + str(iter)]['reverse'][repeater.name] = copy.deepcopy(emptytestdata)
                    if self.saveasyougo:
                        self.savedata.append(self.pathtosave +
                        'initialization: %s/iteration: %s/reverse/%s/'
                        %(str(init),str(iter),  repeater.name), copy.deepcopy(emptytestdata))

    def dictvisititems(self, dictionary, function):
        '''
        Applies function at every node of nested dict, passing the path as a
        list as the first argument, and the object itself as the second.
        '''
        def recursivevisit(dictionary, function, keylist):
            for key in dictionary.keys():
                if isinstance(dictionary[key], dict):
                    recursivevisit(dictionary[key], function, keylist + [key])
                else:
                    dictionary[key] = function(keylist + [key], dictionary[key])
        recursivevisit(dictionary, function, [])


    def _replacewithempty(self, keys, element):
        '''
        If element is a list, removes all data, and adds a new first dimension
        of length numpoints. If element is an int or a float, returns a
        array of length numpoints.
        '''

        if isinstance(element, (list, np.ndarray)):
            a = list(np.shape(element))
            a.insert(0, self.points)
            datashape = tuple(a)
            element = np.full(datashape, np.nan)
        elif isinstance(element, (int,float)):
            element = np.full(self.points, np.nan)
        return element

    def _sliceload(self, superdataset, subdataset, slice):
        '''
        Superdataset and subdataset must have the same structure, except each
        leaf of superdataset must have an extra first dimension. Each leaf in
        subdataset will be loaded into slice of each leaf of superdict.
        '''
        subdataset = copy.deepcopy(subdataset)
        if isinstance(subdataset, dict):
            def _loaddict(path, obj):
                '''
                Takes the path to an object in an subdataset and the object
                itself. If the object is a dict, does nothing, but if the
                object is not, loads it into slice at the same location in
                superdataset
                '''
                if not isinstance(obj, dict):
                    currentdictlevel = superdataset
                    for key in path[:-1]:
                        currentdictlevel = currentdictlevel[key]
                    currentdictlevel[path[-1]][slice] = obj
            self.dictvisititems(subdataset, _loaddict)
        elif isinstance(subdataset, (np.ndarray, list, int, float)):
            superdataset[slice] = subdataset
        return superdataset


    def __call__(self, n):
        '''
        Runs the sweep, appending the sweep data to self.sweeps_data.
        Config will only be returned on the first call (that is, n = 0)
        '''
        #procedural instrument saving. Experimental. Still save by hand as well.
        if n == 0 and self.saveconfig:
            self.savedata.append('/config/', self._getconfig())
        for k in range(self.runcount):
            if self.bi:
                self.sweep_data['iteration: ' + str(k)] = {'forward':{}, 'reverse':{}}
            else:
                self.sweep_data['iteration: ' + str(k)] = {'forward':{}}
            time.sleep(self.pausebeforesweep)
            init = n
            iter = k
            if self.waiter:
                self.waiter.reset()
            for point in  range(self.points):
                #clear_output()
                #print('On point ' + str(point) +
                #                            ' out of ' + str(self.points))
                for r in self.repeaters:
                    if(self.waiter and self.waiter.test(n)):
                        break
                    if r.returns:
                        returneddata = r(point)
                        if point == 0:
                             self._setuprepeatersave(init, iter, r,
                                                          returneddata)
                        if r.issliced:
                            self._sliceload(
                                    self.sweep_data['iteration: ' + str(iter)]
                                    ['forward'][r.name], returneddata,
                                    slice(point, point+1))
                            if self.saveasyougo:
                                self.savedata.append(self.pathtosave +
                                'initialization: %s/iteration: %s/forward/%s/'
                                %(str(init),str(iter),  r.name),
                                returneddata, slice(point, point+1))
                        else:
                            self.sweep_data['iteration: ' + str(iter)]['forward'][r.name][str(point)] = (
                                                        returneddata)
                            if self.saveasyougo:
                                self.savedata.append(self.pathtosave +
                                'initialization: %s/iteration: %s/forward/%s/%s/'
                                %(str(init),str(iter),  r.name,
                                  str(point)),  returneddata)
                    else:
                        r(point)
            if self.bi:
                time.sleep(self.pausebeforesweep)
                for point in  range(self.points):
                    #clear_output()
                    #print('On point ' + str(point) +
                    #                            ' out of ' + str(self.points))
                    for r in self.repeaters:
                        if(self.waiter and self.waiter.test(n)):
                            break
                        if r.returns:
                            returneddata = r(self.points - point - 1)
                            if r.issliced:
                                self._sliceload(
                                        self.sweep_data['iteration: ' + str(iter)]
                                        ['reverse'][r.name], returneddata,
                                        slice(point, point+1))
                                if self.saveasyougo:
                                    self.savedata.append(self.pathtosave +
                                    'initialization: %s/iteration: %s/reverse/%s/'
                                    %(str(init),str(iter),  r.name),
                                    returneddata, slice(point, point+1))
                            else:
                                self.sweep_data['iteration: ' + str(iter)]['reverse'][r.name][str(point)] = (
                                                            returneddata)
                                if self.saveasyougo:
                                    self.savedata.append(self.pathtosave +
                                    'initialization: %s/iteration: %s/reverse/%s/%s/'
                                    %(str(init),str(iter),  r.name,
                                      str(point)),  returneddata)
                        else:
                            r(self.points - point - 1)
        if self.saveatend:
            self.savedata.append(self.pathtosave + 'initialization: %s/'
                                                % str(n), self.sweep_data)
            #self.save()
        return self.sweep_data

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
                if isinstance(repeater.delay, (np.ndarray,list)):
                    description += ('delays execution for a variable time')
                else:
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

class Current_Time(Measurement):
    '''
    if lt (local time) is False, returns time since epoch.
    If lt is true, returns local time in YYYYMMDDHHSS format
    '''

    def __init__(self, lt = False):
        self.lt = lt
        self.returns = True
        if not lt:
            self.name = 'Current Time since epoch (Seconds)'
        else:
            self.name = 'Current local time (YYYYMMDDHHMMSS)'
    def __call__(self,n):
        if self.lt:
            now = datetime.now()
            return now.strftime('%Y%m%d%H%M%S')
        else:
            return time.time()

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
        self.returns = True
    def restart(self, n):
        '''
        Resets the zero of time to the next time seconds or the class is called
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

    def _getconfig(self):
        return {'Times delayed until' : self.times}

class Delayer(Measurement):
    '''
    Delays execution for a fixed amount of time
    '''

    def __init__(self, delay, multidelayorder = 1):
        self.delay = delay
        self.name = 'Delayer, delays for ' + str(delay) + ' sec'
        self.returns = False

    def __call__(self, n):
        if isinstance(self.delay, (np.ndarray,list)):
            time.sleep(self.delay[n])
        else:
            time.sleep(self.delay)

class Wait(Measurement):

    '''
    Will wait until prop of obj is at the
    appropriate value in values. Valence determines if prop must be less
    than, greater than, or within tolerance (-1, 1, 0 respectively) of
    values(n). Must satisfy this condition for timetoaccept.
    '''

    def __init__(self, name, obj, prop, values, elem = False, valence = -1,
                    tolerance = 0, timeout = 10, interval = 1,
                                                        timetoaccept = 1e-3):

        self.name = name
        self.returns = True
        self.obj = obj
        if not hasattr(obj, "__getstate__"):
            print('Passed object does not have a getstate. Instrument '
                                            + 'config will not be saved!')
            self.savestate = False
        else:
            self.savestate = True
        self.prop = prop
        self.values = values
        self.elem = elem
        self.valence = valence
        self.tolerance  = tolerance
        self.timeout = timeout
        self.timetoaccept = timetoaccept
        self.interval = interval
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
        self.start_time_in_range = tstart
        print('Waiting to ' + self.name)
        while(True):
            time.sleep(self.interval)
            if time.time()- tstart > self.timeout:
                raise Exception('Waiting timed out at value '
                    + str(self.values[n]) + ' of waiter ' + self.name)
            if self.test(n):
                print('Done')
                break
        return time.time() - tstart

    def _getconfig(self):
        config = {'Measured Property' : self.values, 'Key of measured item':
        self.elem,
      'Valence of test (-1 less than, 1 greater than, 0 within tolerance)':
        self.valence, 'Tolerance of test, in as measured units' :
        self.tolerance, 'Timeout (s)': self.timeout, 'Time to accept (s)' :
        self.timetoaccept, 'Sampling interval (s)' :self.interval}
        if self.savestate:
            config['Instrument Configuration'] = self.obj.__getstate__()
        return config
