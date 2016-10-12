from jsonpickle.ext import numpy as jspnp
import json, os, pickle, bz2, jsonpickle as jsp, numpy as np
from datetime import datetime
jspnp.register_handlers()
from copy import copy
import h5py

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
            'filename': 'filename'
        })
        return {key: getattr(self, value) for key, value in self._save_dict.items() if type(getattr(self, value)) is not np.ndarray}


    def __setstate__(self, state):
        '''
        Default method for loading from JSON.
        `state` is a dictionary.
        '''

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
    def fromjson(json_file, unwanted_keys = [], decompress=True):
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

        if decompress:
            obj._decompress() # undo compression

        return obj


    @classmethod
    def load(cls, json_file, instruments={}, unwanted_keys=[]):
        '''
        Basic load method. Calls fromjson, not loading instruments, then loads instruments.
        Overwrite this for each subclass if necessary.
        Pass in an array of the names of things you don't want to load.
        By default, we won't load any instruments, but you can pass in an instruments dictionary to load them.
        '''
        unwanted_keys += cls.instrument_list
        obj = Measurement.fromjson(json_file, unwanted_keys)
        obj.load_instruments(instruments)

        append = json_file[json_file.rfind('_')+1:json_file.rfind('.')] # extracts the appended string
        Measurement.__init__(obj, append) # to create save_dict
        return obj


    def load_instruments(self, instruments={}):
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


    def save(self):
        '''
        Basic save method. Just calls tojson. Overwrite this for each subclass.
        '''
        self._save()


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

        self.tojson(json_dict, filename)
        self.tohdf5(hdf5_dict, filename)


    def tohdf5(self, hdf5_dict, filename):
        with h5py.File(filename+'.h5', 'w') as f:
            for key, value in hdf5_dict.items():
                dset = f.create_dataset(key, data=getattr(self, value),
                    compression = 'gzip', compression_opts=9
                )


    def tojson(self, json_dict, filename):
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
