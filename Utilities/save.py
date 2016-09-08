from jsonpickle.ext import numpy
import json, os, pickle, bz2, jsonpickle as jsp, numpy as np
numpy.register_handlers()
from copy import copy

class Measurement:
    _replacement = None

    def __getstate__(self):
        self.save_dict = {'_replacement': self._replacement}
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


    def tojson(self, filename=None, compress=True):
        '''
        Saves an object to JSON. Specify a custom filename,
        or use the `filename` variable under that object.
        '''
        if compress:
            self.compress() # compress the object
            self.AAAreplacement = self._replacement # in case sort_keys order messes up

        if filename is None:
            try:
                filename = self.filename
            except:
                filename = 'no_filename_given'

        obj_string = jsp.encode(self)
        obj_dict = json.loads(obj_string)
        with open(filename+'.json', 'w', encoding='utf-8') as f:
            # dumps = json.dumps(obj_dict, f, sort_keys=True, indent=4)
            # dumps = dumps.replace('\r','\\r')
            # f.write(dumps)
            json.dump(obj_dict, f, sort_keys=True, indent=4)
        if compress:
            del self.AAAreplacement # in case sort_keys order messes up

    @staticmethod
    def fromjson(json_file, decompress=True):
        with open(json_file, encoding='utf-8') as f:
            obj_dict = json.load(f)
        obj_string = json.dumps(obj_dict)
        obj = jsp.decode(obj_string)

        if decompress:
            # obj._replacement = obj.AAAreplacement  # in case sort_keys order messes up
            # del obj.AAAreplacement # in case sort_keys order messes up
            obj.decompress() # undo compression

        return obj


    def generate_filename(self, path):
        '''
        generates a filename from the current time
        '''
        self.measurement_time = datetime.now()
        self.time = self.measurement_time.strftime('%Y-%m-%d_%H%M%S')
        self.filename = os.path.join(path,self.time)
