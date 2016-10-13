from jsonpickle.ext import numpy as jspnp
import json, os, pickle, bz2, jsonpickle as jsp, numpy as np
from datetime import datetime
jspnp.register_handlers()
from copy import copy
import h5py, glob

class Measurement:
    instrument_list = []

    def __init__(self, append=None):
        self._save_dict = {} # this is a dictionary where key = name of thing you want to appear in JSON, value = name of variable you want to save.
        self.timestamp = ''

        self.make_timestamp_and_filename(append)
        Measurement.__getstate__(self) # to create the save_dict without using overridden subclass getstate


    def __getstate__(self):
        '''
        Returns a dictionary of everything we want to save to JSON.
        In a subclass, you must call this method and then update self.save_dict.
        '''
        self._save_dict.update({
            'timestamp': 'timestamp',
            'filename': 'filename',
            'save dict': '_save_dict'
        })
        return {key: getattr(self, value) for key, value in self._save_dict.items() if type(getattr(self, value)) is not np.ndarray}


    def __setstate__(self, state):
        '''
        Default method for loading from JSON.
        `state` is a dictionary.
        '''
        setattr(self, '_save_dict', state['save dict'])

        for k in list(state.keys()):
            try:
                state[self._save_dict[k]] = state.pop(k) # replace formatted keys with variable names
            except:
                print('Couldn\'t load %s' %k)
        self.__dict__.update(state)


    def add_to_save(self, name, alias=None):
        '''
        Adds a variable to the save dictionary.
        Give its name as a string, and give an alias if you would like it saved with a different string descriptor.
        '''
        if alias is None:
            alias = name
        self._save_dict.update({alias: name})


    @staticmethod
    def _fromjson(json_file, unwanted_keys = []):
        '''
        Loads an object from JSON.
        '''
        with open(json_file, encoding='utf-8') as f:
            obj_dict = json.load(f)
        for key in unwanted_keys: # get rid of keys you don't want to load
            try:
                obj_dict['py/state'].pop(key)
            except:
                pass # if we accidentally give a key that's not there
        obj_string = json.dumps(obj_dict)
        obj = jsp.decode(obj_string)

        return obj


    @classmethod
    def load(cls, filename=None, instruments={}, unwanted_keys=[]):
        '''
        Basic load method. Calls _fromjson, not loading instruments, then loads from HDF5, then loads instruments.
        Overwrite this for each subclass if necessary.
        Pass in an array of the names of things you don't want to load.
        By default, we won't load any instruments, but you can pass in an instruments dictionary to load them.
        '''
        if filename is None: # finds the last saved object
            try:
                filename =  max(glob.iglob(os.path.join(get_todays_data_path(),'*_%s.json' %cls._append)),
                                        key=os.path.getctime)
            except: # we must have taken one during the previous day's work
                folders = list(glob.iglob(os.path.join(get_todays_data_path(),'..','*')))
                # -2 should be the previous day (-1 is today)
                filename =  max(glob.iglob(os.path.join(folders[-2],'*_%s.json' %cls._append)),
                                        key=os.path.getctime)
            filename = filename.rpartition('.')[0] #remove extension

        unwanted_keys += cls.instrument_list
        obj = Measurement._fromjson(filename+'.json', unwanted_keys)
        obj._load_hdf5(filename+'.h5')
        obj._load_instruments(instruments)

        append = filename[filename.rfind('_')+1:] # extracts the appended string
        Measurement.__init__(obj, append) # to create save_dict
        return obj


    def _load_hdf5(self, filename, unwanted_keys = []):
        '''
        Loads data from HDF5 files.
        '''
        with h5py.File(filename, 'r') as f:
            for key in f.keys():
                if key not in unwanted_keys:
                    setattr(self, key, f[key][:]) # converts to numpy array


    def _load_instruments(self, instruments={}):
        '''
        Loads instruments from a dictionary.
        Specify instruments needed using self.instrument_list.
        '''
        for instrument in self.instrument_list:
            if instrument in instruments:
                setattr(self, instrument, instruments[instrument])
            else:
                setattr(self, instrument, None)


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


    def _save(self, path = '.', filename=None, compress=True):
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

        if compress:
            ## Figure out what to save as JSON vs HDF5 - only looks one level deep for now.
            json_dict = {}
            hdf5_dict = {}
            for key, value in self._save_dict.items(): # key = name we want to save with, value = actual name of variable
                if type(getattr(self,value)) is np.ndarray: # checks if this variable is a numpy array
                    hdf5_dict[key] = value # Numpy arrays will get converted to hdf5
                else:
                    json_dict[key] = value # everything else gets saved to JSON
        else:
            json_dict = self._save_dict

        self._save_json(json_dict, filename)
        self._save_hdf5(hdf5_dict, filename)


    def _save_hdf5(self, hdf5_dict, filename):
        with h5py.File(filename+'.h5', 'w') as f:
            for key, value in hdf5_dict.items():
                dset = f.create_dataset(key, data=getattr(self, value),
                    compression = 'gzip', compression_opts=9)


    def _save_json(self, json_dict, filename):
        '''
        Saves an object to JSON. Specify a custom filename,
        or use the `filename` variable under that object.
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
