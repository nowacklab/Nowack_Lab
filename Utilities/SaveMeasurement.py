import sys
import os
import inspect
from Nowack_Lab.Utilities.datasaver import Saver

class Measurement(Saver):

    def __init__(self, name = ''):
        super().__init__(name = name)

    def saveinstruments(path, instruments):
        '''
        Saves all the instruments to activedataset, at path/Instruments
        '''
        instrumentstatus = {}
        for instrument in instruments.keys():
            instrumentstatus[instrument] = (
                                        instruments[instrument].__getstate__())
        self.append(path + '/Instruments', instrumentstatus)

    def savething(self, path, obj):
        '''
        Saves an object, checking if it has a __getstate__, then checking
        if it is a matplotlib plot, then if it is not a method, buildin, or
        function, trying to save it to an HDF5.
        '''
        print(obj)
        if hasattr(obj, 'name'):
            path = path + '/' + obj.name
        if hasattr(obj, '__getstate__'):
            self.append(path + '/getstate/', obj.__getstate__)
        if hasattr(obj, 'savefig'):
            self.savefigure(obj, path + '/matplotlibfigure/')
        if not (inspect.ismethod(obj) or inspect.isbuiltin(obj)
                                                or inspect.isfunction(obj)):
            try:
                self.append(path, obj)
            except:
                print('Could not save %s at %s' % (str(obj), str(path)))
        else:
            print('Did not save %s at %s because it is a method'
                                                    % (str(obj), str(path)))

    def _recursiveattrvisit(self, obj, attrlist, func):
        '''
        Applies function to every attr of self, even nested. Attrlist is the
        list of attrs to get to obj, from a root obj. function is passed
        listofattrs in a HDF5 path format as its first argument, and obj as
        it's second. Uses a dir call to get the attributes. Ignores attributes
        with __"name"__ formatting.
        '''
        path = ""
        for attr in attrlist:
            path = path + "/" + attr
        func(path, obj)
        for attr in dir(obj):
            if not(len(attr)>4 and all(attrchar == '_' for attrchar in
                                            [attr[i] for i in [0,1,-2,-1]])):
                self._recursiveattrvisit(getattr(obj, attr),
                                                       attrlist + [attr],func)

    def save(self, quiet = True):
        '''
        Saves all attributes of self recursively.
        '''
        if quiet:
            oldprint = sys.stdout
            sys.stdout = open(os.devnull, 'w')
        self._recursiveattrvisit(self, [], self.savething)
        if quiet:
            sys.stdout = oldprint
