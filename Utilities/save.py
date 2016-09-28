from jsonpickle.ext import numpy as jspnp
import json, os, pickle, bz2, jsonpickle as jsp, numpy as np
from datetime import datetime
jspnp.register_handlers()
from copy import copy


class Measurement:
    instrument_list = []

    self._replacement = b'\\\\\\r'
    self.timestamp = ''

    def __init__(self, append=None):
        self.make_timestamp_and_filename(append)
        Measurement.__getstate__(self) # to create the save_dict without using overridden subclass getstate

    def __getstate__(self):
        '''
        Returns a dictionary of everything we want to save to JSON.
        In a subclass, you must call this method and then update self.save_dict.
        '''
        self.save_dict = {'_replacement': self._replacement,
                        'timestamp': self.timestamp,
                        'filename': self.filename
        }
        return self.save_dict


    def __setstate__(self, state):
        '''
        Default method for loading from JSON.
        `state` is a dictionary.
        '''

        self.__dict__.update(state)


    def _compress(self, d = None):
        '''
        Compresses variables in the given dictionary.
        By default, uses self.__dict__.
        Right now, just numpy arrays are compressed.
        '''
        if d is None:
            d = self.__dict__

        for key in list(d.keys()):
            if type(d[key]) is np.ndarray:
                d[key] = self._compress_numpy(d[key])
            elif type(d[key]) is dict:
                self._compress(d[key])


    def _compress_numpy(self, array):
        '''
        Compresses a numpy array before saving to json
        First pickles, and then compresses with bz2.
        After that, it replaces all carriage returns \r to \\\\\\r,
        a safe string that will not appear in a bytes object.
        If for some reason it does, we tack on more \\!
        '''
        array = pickle.dumps(array)
        array = bz2.compress(array)

        ### OKAY DUMB STUFF AHEAD, YOU'VE BEEN WARNED
        # We need to convert carriage returns to something safe
        # or else JSON will throw them away!
        self._replacement = b'\\\\\\r' # Something that will not be in a bytes
        while not array.find(self._replacement): # In case it is...
            self._replacement = b'\\' + self._replacement # ...add more \\!!
        array = array.replace(b'\r', self._replacement)
        return array


    def _decompress(self, d=None):
        '''
        Deompresses variables in the given dictionary.
        By default, uses self.__dict__.
        Right now, just numpy arrays are decompressed.
        '''
        if d is None:
            d = self.__dict__

        for key in list(d.keys()):
            if type(d[key]) is bytes:
                try:
                    d[key] = self._decompress_numpy(d[key])
                except:
                    pass
            elif type(d[key]) is dict:
                self._decompress(d[key])


    def _decompress_numpy(self, array):
        '''
        decompresses a numpy array loaded from json.
        First undoes carriage returns BS, then bz2 compression, then unpickles.
        '''

        array = array.replace(self._replacement, b'\r') #_replacement should exist

        array = bz2.decompress(array)
        array = pickle.loads(array)
        return array


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
                print('%s not loaded!\n' %instrument)


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
        self.tojson()


    def tojson(self, path = '.', filename=None, compress=True):
        '''
        Saves an object to JSON. Specify a custom filename,
        or use the `filename` variable under that object.
        '''
        if compress:
            self._compress() # compress the object

        if filename is None:
            try:
                filename = self.filename # see if this exists
            except: # if you forgot to make a filename
                filename = ''

        if filename == '':
            self.make_timestamp_and_filename()
            filename = self.filename

        filename = os.path.join(path, filename)

        inp='y'
        if os.path.exists(filename+'.json'):
            inp = input('File %s already exists! Overwrite? (y/n)' %filename)
        if inp not in ('y','Y'):
            print('File not saved!')
        else:
            obj_string = jsp.encode(self)
            obj_dict = json.loads(obj_string)
            with open(filename+'.json', 'w', encoding='utf-8') as f:
                json.dump(obj_dict, f, sort_keys=True, indent=4)

        if compress:
            self._decompress() # so we can still play with numpy arrays


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
