from NowackLab.Utilities.dataset import dataset

class SaveMeasurement(datasaver):

    def __init__(self, name):
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

    def savething(path, obj):
        '''
        Saves an object, checking if it has a __getstate__, then checking
        if it is a matplotlib plot, then saving trying to save it to an HDF5.
        '''
        if hasattr(obj, 'name'):
            path = path + '/' + obj.name

        if hasattr(obj, '__getstate__'):
            self.append(path, obj.__getstate__)
        elif hasattr(obj, 'savefig'):
            self.savefigure(obj, path)
        else:
            try:
                self.append(path, obj)
            except:
                print('Could not save %s at %s' % (str(obj), str(path)))

    def recursiveattrvisit(obj, attrlist, func):
        '''
        Applies function to every attr of obj, even nested. Attrlist is the
        list of attrs to get to obj, from a root obj. function is passed
        listofattrs in a HDF5 path format as its first argument, and obj as
        it's second. Uses a dir call to get the attributes. Ignores attributes
        with __"name"__ formatting
        '''
        path = ""
        for attr in attrlist:
            path = path + "/" + attr
        func(path, obj)
        for attr in dir(obj):
            if not(len(attr)>4 and all(attrchar = '_' for attrchar in
                                            [attr[i] for i in [0,1,-2,-1]]):
                self.recursiveattrvisit(obj.attr, attrlist + [attr],function)
