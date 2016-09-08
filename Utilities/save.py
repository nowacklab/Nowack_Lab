from jsonpickle.ext import numpy as jspnp
import json, os, pickle, bz2, jsonpickle as jsp, numpy as np
from datetime import datetime
jspnp.register_handlers()
from copy import copy

class Measurement:
    _replacement = None
    timestamp = ''

    def __getstate__(self):
        self.save_dict = {'_replacement': self._replacement,
                        'timestamp': self.timestamp,
                        'filename': self.filename
        }
        return self.save_dict

    def compress(self):
        '''
        Compresses variables in __dict__. Right now, just numpy arrays
        '''
        d = copy(self.__dict__)
        for var in d:
            if type(getattr(self,var)) is np.ndarray:
                setattr(self, var, self.compress_numpy(getattr(self,var)))


    def compress_numpy(self, array):
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
        # AAA makes it first in the list of dict_keys
        self._replacement = b'\\\\\\r' # Something that will not be in a bytes
        while not array.find(self._replacement): # In case it is...
            self._replacement = b'\\' + self._replacement # ...add more \\!!
        array = array.replace(b'\r', self._replacement)
        return array


    def decompress(self):
        '''
        Decompresses variables in __dict__.
        '''
        d = copy(self.__dict__)
        for var in d:
            vari = getattr(self,var)
            if type(vari) is bytes:
                try:
                    vari = self.decompress_numpy(vari)
                    if type(vari) is np.ndarray:
                        setattr(self,var,vari)
                except:
                    pass


    def decompress_numpy(self, array):
        '''
        Decompresses a numpy array loaded from json.
        First undoes carriage returns BS, then bz2 compression, then unpickles.
        '''

        array = array.replace(self._replacement, b'\r') #_replacement should exist

        array = bz2.decompress(array)
        array = pickle.loads(array)
        return array


    @staticmethod
    def fromjson(json_file, decompress=True):
        '''
        Loads an object from JSON.
        '''
        with open(json_file, encoding='utf-8') as f:
            obj_dict = json.load(f)
        obj_string = json.dumps(obj_dict)
        obj = jsp.decode(obj_string)

        if decompress:
            obj.decompress() # undo compression

        return obj


    @staticmethod
    def load(json_file):
        '''
        Basic load method. Just calls fromjson.
        Overwrite this for each subclass if necessary.
        '''
        return Measurement.fromjson(json_file)


    def make_timestamp_and_filename(self, postpend=None):
        '''
        Makes a timestamp and filename from the current time.
        Use `postpend` to tack on something at the end of the filename.
        '''
        now = datetime.now()
        self.timestamp = now.strftime("%Y-%m-%d %I:%M:%S %p")
        self.filename = now.strftime('%Y%m%d_%H%M%S')
        if postpend:
            self.filename += '_' + postpend


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
            self.compress() # compress the object

        if filename is None:
            try:
                self.filename # see if this exists
            except: # if you forgot to make a filename
                filename = self.filename

        if filename == '':
            self.make_timestamp_and_filename()
            filename = self.filename

        filename = os.path.join(path, filename)

        obj_string = jsp.encode(self)
        obj_dict = json.loads(obj_string)
        with open(filename+'.json', 'w', encoding='utf-8') as f:
            json.dump(obj_dict, f, sort_keys=True, indent=4)
