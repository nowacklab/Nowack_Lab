from jsonpickle.ext import numpy as jspnp
import json, os, pickle, bz2, jsonpickle as jsp, numpy as np
from datetime import datetime
jspnp.register_handlers()
from copy import copy
import h5py, glob, matplotlib

class Measurement:
    _chan_labels = [] # DAQ channel labels expected by this class
    instrument_list = []

    def __init__(self, append=None):
        self.timestamp = ''

        self.make_timestamp_and_filename(append)


    def __getstate__(self):
        '''
        Returns a dictionary of everything we want to save to JSON.
        This excludes numpy arrays which are saved to HDF5
        '''
        variables = list(self.__dict__.keys())

        ## If in the future, we want to blacklist some variables.
        # for var in self._blacklist:
        #     variables.remove(var)

        for var in variables.copy(): # copy so we don't change size of array during iteration
            ## Don't save numpy arrays to JSON
            if type(getattr(self, var)) is np.ndarray:
                variables.remove(var)

            ## Don't save matplotlib objects to JSON
            try:
                m = getattr(self,var).__module__
                m = m[:m.find('.')] # will strip out "matplotlib"
                if m == 'matplotlib':
                    variables.remove(var)
            except:
                pass # built-in types won't have __module__

        return {var: getattr(self, var) for var in variables}


    def __setstate__(self, state):
        '''
        Default method for loading from JSON.
        `state` is a dictionary.
        '''
        self.__dict__.update(state)


    @classmethod
    def load(cls, filename=None, instruments={}, unwanted_keys=[]):
        '''
        Basic load method. Calls _load_json, not loading instruments, then loads from HDF5, then loads instruments.
        Overwrite this for each subclass if necessary.
        Pass in an array of the names of things you don't want to load.
        By default, we won't load any instruments, but you can pass in an instruments dictionary to load them.
        '''

        if filename is None: # tries to find the last saved object; not guaranteed to work
            try:
                filename =  max(glob.iglob(os.path.join(get_todays_data_path(),'*_%s.json' %cls._append)),
                                        key=os.path.getctime)
            except: # we must have taken one during the previous day's work
                folders = list(glob.iglob(os.path.join(get_todays_data_path(),'..','*')))
                # -2 should be the previous day (-1 is today)
                filename =  max(glob.iglob(os.path.join(folders[-2],'*_%s.json' %cls._append)),
                                        key=os.path.getctime)
            filename = filename.rpartition('.')[0] #remove extension

        unwanted_keys += cls.instrument_list # don't load instruments

        obj = Measurement._load_json(filename+'.json', unwanted_keys)
        obj._load_hdf5(filename+'.h5')
        obj._load_instruments(instruments)

        return obj


    def _load_hdf5(self, filename, unwanted_keys = []):
        '''
        Loads data from HDF5 files.
        '''
        with h5py.File(filename, 'r') as f:
            for key in f.keys():
                if key not in unwanted_keys:
                    setattr(self, key, f[key][:]) # converts to numpy array.


    def _load_instruments(self, instruments={}):
        '''
        Loads instruments from a dictionary.
        Specify instruments needed using self.instrument_list.
        '''
        for instrument in self.instrument_list:
            if instrument in instruments:
                setattr(self, instrument, instruments[instrument])
            elif 'daq' in instruments:
                for ch in self._chan_labels:
                    if ch not in self.daq.outputs and ch not in self.daq.inputs:
                        raise Exception('Need to set daq channel labels! Need a %s' %ch)
            else:
                setattr(self, instrument, None)



    @staticmethod
    def _load_json(json_file, unwanted_keys = []):
        '''
        Loads an object from JSON.
        '''
        with open(json_file, encoding='utf-8') as f:
            obj_dict = json.load(f)

        def walk(d):
            for key in list(d.keys()): # convert to list because dictionary changes size
                if key in unwanted_keys: # get rid of keys you don't want to load
                    d[key] = None
                elif type(d[key]) is dict:
                    walk(d[key])

        walk(obj_dict)

        obj_string = json.dumps(obj_dict)
        obj = jsp.decode(obj_string)

        return obj


    def make_timestamp_and_filename(self, append=None):
        '''
        Makes a timestamp and filename from the current time.
        Use `append` to tack on something at the end of the filename.
        '''
        now = datetime.now()
        self.timestamp = now.strftime("%Y-%m-%d %I:%M:%S %p")
        self.filename = now.strftime('%Y-%m-%d_%H%M%S')
        if append:
            self.filename += '_' + append


    def save(self, path= '.', filename=None):
        '''
        Basic save method. Just calls _save. Overwrite this for each subclass.
        '''
        self._save(path, filename)


    def _save(self, path = '.', filename=None):
        '''
        Saves data. numpy arrays are saved to one file as hdf5,
        everything else is saved to JSON
        '''
        if filename is None:
            try:
                filename = self.filename # see if this exists
            except: # if you forgot to make a filename
                filename = ''

        if filename == '':
            self.make_timestamp_and_filename()
            filename = self.filename

        filename = os.path.join(path, filename)

        # if compress:
        #     ## Figure out what to save as JSON vs HDF5 - only looks one level deep for now.
        #     json_dict = {}
        #     hdf5_dict = {}
        #     for key, value in self.__dict__.items(): # key = name we want to save with, value = actual name of variable
        #         if type(getattr(self,value)) is np.ndarray: # checks if this variable is a numpy array
        #             hdf5_dict[key] = value # Numpy arrays will get converted to hdf5
        #         else:
        #             json_dict[key] = value # everything else gets saved to JSON
        # else:
        #     json_dict = self.__dict__

        self._save_json(filename)
        self._save_hdf5(filename)

        try:
            Measurement.load(filename)
        except:
            raise Exception('Reloading failed, but object was saved!')


    def _save_hdf5(self, filename):
        '''
        Save numpy arrays to h5py.
        '''
        with h5py.File(filename+'.h5', 'w') as f:
            for key, value in self.__dict__.items():
                if type(value) is np.ndarray:
                    d = f.create_dataset(key, value.shape,
                        compression = 'gzip', compression_opts=9
                        )
                    d.set_fill_value = np.nan
                    d[...] = value


    def _save_json(self, filename):
        '''
        Saves an object to JSON. Specify a custom filename,
        or use the `filename` variable under that object.
        Through __getstate__, ignores any numpy arrays when saving.
        '''
        if not exists(filename+'.json'):
            obj_string = jsp.encode(self)
            obj_dict = json.loads(obj_string)
            with open(filename+'.json', 'w', encoding='utf-8') as f:
                json.dump(obj_dict, f, sort_keys=True, indent=4)


def exists(filename):
    inp='y'
    if os.path.exists(filename+'.json'):
        inp = input('File %s already exists! Overwrite? (y/n)' %(filename+'.json'))
    if inp not in ('y','Y'):
        print('File not saved!')
        return True
    return False


def get_cooldown_data_path():
    with open(os.path.join(os.path.dirname(__file__),'paths.json'),'r') as f:
        data = json.load(f)
    path = os.path.join(os.path.expanduser('~'), *data['cooldown'])
    return path


def get_todays_data_path():
    cooldown_path = get_cooldown_data_path()
    now = datetime.now()
    todays_data_path = os.path.join(cooldown_path, now.strftime('%Y-%m-%d'))

    # Make the directory
    if not os.path.exists(todays_data_path):
        os.makedirs(todays_data_path)
    return todays_data_path


def set_cooldown_data_path(description=''):
    '''
    Run this when you start a new cooldown.
    Makes a new directory in the Montana data folder
    with the current date and a description of the cooldown.
    Writes to paths.json to store the name of the data directory.
    '''
    now = datetime.now()
    now_fmt = now.strftime('%Y-%m-%d')

    filetuple = ('Dropbox (Nowack lab)', 'TeamData', 'Montana', 'cooldowns', now_fmt + '_' + description)

    paths = {'cooldown': filetuple}
    with open(os.path.join(os.path.dirname(__file__),'paths.json'), 'w') as f:
        json.dump(paths, f)

    # Make the directory
    _home = os.path.expanduser('~')
    filename = os.path.join(_home, os.path.join(*filetuple))
    if not os.path.exists(filename):
        os.makedirs(filename)
