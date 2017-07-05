from jsonpickle.ext import numpy as jspnp
import json, os, pickle, bz2, jsonpickle as jsp, numpy as np, re
from datetime import datetime
jspnp.register_handlers()
from copy import copy
import h5py, glob, matplotlib, inspect, platform, hashlib, shutil
import matplotlib.pyplot as plt
from . import utilities

'''
How saving and loading works:
1) Walks through object's __dict__, subdictionaries, and subobjects, picks out
numpy arrays, and saves them in a hirearchy in HDF5. Dictionaries are
represented as groups in HDF5, and objects are also represented as groups, but
with a ! preceding the name. This is parsed when loading.
2) All numpy arrays and matplotlib objects in the dictionary hierarchy are set
to None, and the object is saved to JSON.
3) The saved object is immediately reloaded to see if everything went well.
3a) First, the JSON file is loaded to set up the dictionary hierarchy.
3b) Second, we walk through the HDF5 file (identifying objects and dictionaries
as necessary) and populate the numpy arrays.
'''


class Measurement:
    _chan_labels = [] # DAQ channel labels expected by this class
    instrument_list = []
    fig = None

    def __init__(self):
        self.timestamp = ''

        self.make_timestamp_and_filename()


    def __getstate__(self):
        '''
        Returns a dictionary of everything we want to save to JSON.
        This excludes numpy arrays which are saved to HDF5
        '''
        def walk(d):
            d = d.copy() # make sure we don't modify original dictionary
            variables = list(d.keys()) # list of all the variables in the dictionary

            for var in variables: # copy so we don't change size of array during iteration
                ## Don't save numpy arrays to JSON
                if type(d[var]) is np.ndarray:
                    d[var] = None

                ## Don't save matplotlib objects to JSON
                try:
                    m = d[var].__module__
                    m = m[:m.find('.')] # will strip out "matplotlib"
                    if m == 'matplotlib':
                        d[var] = None
                except:
                    pass # built-in types won't have __module__

                if 'dict' in utilities.get_superclasses(d[var]):
                    d[var] = walk(d[var]) # This unfortunately erases the dictionary...

            return d # only return ones that are the right type.

        return walk(self.__dict__)


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
                filename =  max(glob.iglob(os.path.join(get_local_data_path(), get_todays_data_dir(),'*_%s.json' %cls.__name__)),
                                        key=os.path.getctime)
            except: # we must have taken one during the previous day's work
                folders = list(glob.iglob(os.path.join(get_local_data_path(), get_todays_data_dir(),'..','*')))
                # -2 should be the previous day (-1 is today)
                filename =  max(glob.iglob(os.path.join(folders[-2],'*_%s.json' %cls.__name__)),
                                        key=os.path.getctime)
        elif os.path.dirname(filename) == '': # if no path specified
            os.path.join(get_local_data_path(), get_todays_data_dir(), filename)

        ## Remove file extensions is given.
        ## This is done somewhat manually in case filename has periods in it for some reason.
        if filename[-5:] == '.json': # ends in .json
            filename = filename[:-5] # strip extension
        elif filename[-3:] == '.h5': # ends in .h5
            filename = filename[:-3] # strip extension
        elif filename[-4:] == '.pdf': # ends in .pdf
            filename = filename[:-4] # strip extension

        unwanted_keys += cls.instrument_list # don't load instruments

        obj = Measurement._load_json(filename+'.json', unwanted_keys)
        obj._load_hdf5(filename+'.h5')
        obj._load_instruments(instruments)

        return obj


    def _load_hdf5(self, filename, unwanted_keys = []):
        '''
        Loads data from HDF5 files. Will walk through the HDF5 file and populate
        the object's dictionary and subdictionaries (already loaded by JSON)
        '''
        with h5py.File(filename, 'r') as f:
            def walk(d, f):
                for key in f.keys():
                    if key not in unwanted_keys:
                        # check if it's a dictionary or object
                        if f.get(key, getclass=True) is h5py._hl.group.Group:
                            if key[0] == '!': # it's an object
                                walk(d[key[1:]].__dict__, f[key])
                                # [:1] strips the !; walks through the subobject
                            else: # it's a dictionary
                                # walk through the subdictionary
                                walk(d[key], f[key])
                        else:
                            d[key] = f[key][:] # we've arrived at a dataset

                    ## If a dictionary key was an int, convert it back
                    try:
                        newkey = int(key) # test if can convert to an integer
                        value = d.pop(key) # replace the key with integer version
                        d[newkey] = value # do this all stepwise in case of error
                    except:
                        pass

                return d

            walk(self.__dict__, f) # start walkin'


    def _load_instruments(self, instruments={}):
        '''
        Loads instruments from a dictionary.
        Specify instruments needed using self.instrument_list.
        '''
        for instrument in self.instrument_list:
            if instrument in instruments:
                setattr(self, instrument, instruments[instrument])
                if instrument == 'daq':
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
                elif 'dict' in utilities.get_superclasses(d[key]):
                    walk(d[key])

        walk(obj_dict)

        obj_string = json.dumps(obj_dict)
        obj = jsp.decode(obj_string)

        return obj


    def make_timestamp_and_filename(self):
        '''
        Makes a timestamp and filename from the current time.
        '''
        now = datetime.now()
        self.timestamp = now.strftime("%Y-%m-%d %I:%M:%S %p")
        self.filename = now.strftime('%Y-%m-%d_%H%M%S')
        self.filename += '_' + self.__class__.__name__


    def plot(self):
        '''
        Update all plots.
        '''
        if self.fig is None:
            self.setup_plots()


    def save(self, filename=None, savefig=True):
        '''
        Basic save method. Just calls _save. Overwrite this for each subclass.
        '''
        self._save(filename, savefig=True)
        return self.filename


    def _save(self, filename=None, savefig=True):
        '''
        Saves data. numpy arrays are saved to one file as hdf5,
        everything else is saved to JSON
        Saved data stored locally but also copied to the data server.
        If you specify no filename, one will be automatically generated based on
        this object's filename and the object will be saved in this experiment's data folder.
        If you specify a filename with no preceding path, it will save
        automatically to the correct folder for this experiment with the custom filename.
        Locally, saves to ~/data/; remotely, saves to /labshare/data/
        If you specify a relative (partial) path, the data will still be saved
        in the data directory, but in subdirectories specified in the filename.
        For example, if the filename is 'custom/custom_filename', the data will
        be saved in (today's data directory)/custom/custom_filename.
        If you specify a full path, the object will save to that path locally
        and to [get_data_server_path()]/[get_computer_name()]/other/[hirearchy past root directory]
        '''

        ## Saving to the experiment-specified directory
        if filename is None:
            if not hasattr(self, 'filename'): # if you forgot to make a filename
                self.make_timestamp_and_filename()
            filename = self.filename

        if os.path.dirname(filename) == '': # you specified a filename with no preceding path
            local_path = os.path.join(get_local_data_path(), get_todays_data_dir(), filename)
            remote_path = os.path.join(get_remote_data_path(), get_todays_data_dir(), filename)

        ## Saving to a custom path
        else: # you specified some sort of path
            local_path = filename
            remote_path = os.path.join(get_remote_data_path(), '..', 'other', *filename.replace('\\', '/').split('/')[1:]) # removes anything before the first slash. e.g. ~/data/stuff -> data/stuff
            # All in all, remote_path should look something like: .../labshare/data/bluefors/other/

        ## Save locally:
        local_dir = os.path.split(local_path)[0]
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        self._save_hdf5(local_path)
        self._save_json(local_path)

        nopdf = True
        if savefig and self.fig is not None:
            self.fig.savefig(local_path+'.pdf', bbox_inches='tight')
            nopdf = False

        ## Save remotely
        if os.path.exists(get_data_server_path()):
            try:
                # Make sure directories exist
                remote_dir = os.path.split(remote_path)[0]
                if not os.path.exists(remote_dir):
                    os.makedirs(remote_dir)

                ## Loop over filetypes
                for ext in ['.h5','.json','.pdf']:
                    if ext == '.pdf' and nopdf:
                        continue
                    # First make a checksum
                    local_checksum = _md5(local_path + ext)

                    # Copy the files
                    shutil.copyfile(local_path + ext, remote_path + ext)

                    # Make comparison checksums
                    remote_checksum = _md5(remote_path + ext)

                    # Check checksums
                    if local_checksum != remote_checksum:
                        print('%s checksum failed! Cannot trust remote file %s' %(ext, remote_path + ext))

            except Exception as e:
                if not os.path.exists(get_data_server_path()):
                    print('SAMBASHARE not connected. Could not find path %s. Object saved locally but not remotely.' %get_data_server_path())
                else:
                    print('Saving to data server failed!\n\nException details: %s\n\nremote path: %s\nlocal path:%s' %(e, remote_path, local_path))
        else:
            print('Not connected to %s, data not saved remotely!' %get_data_server_path())

        ## See if saving worked properly
        try:
            self.load(local_path)
        except:
            raise Exception('Reloading failed, but object was saved!')


    def _save_hdf5(self, filename):
        '''
        Save numpy arrays to h5py. Walks through the object's dictionary
        and any subdictionaries and subobjects, picks out numpy arrays,
        and saves them in the hierarchical HDF5 format.

        A subobject is designated by a ! at the beginning of the varaible name.
        '''

        with h5py.File(filename+'.h5', 'w') as f:
            def walk(d, group): # walk through a dictionary
                for key, value in d.items():
                    if type(key) is int:
                        key = str(key) # convert int keys to string. Will be converted back when loading
                    if type(value) is np.ndarray: # found a numpy array
                        d = group.create_dataset(key, value.shape,
                            compression = 'gzip', compression_opts=9
                        ) # save the numpy array as a dataset
                        d.set_fill_value = np.nan
                        d[...] = value # fill it with data
                    elif 'dict' in utilities.get_superclasses(value): # found a dictionary
                        new_group = group.create_group(key) # make a group with the dictionary name
                        walk(value, new_group) # walk through the dictionary
                    elif hasattr(value, '__dict__'): # found an object of some sort
                        if 'Measurement' in utilities.get_superclasses(value): # restrict saving Measurements.
                            new_group = group.create_group('!'+key) # make a group with !(object name)
                            walk(value.__dict__, new_group) # walk through the object dictionary

            walk(self.__dict__, f)


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


    def setup_plots(self):
        '''
        Set up all plots.
        '''
        self.fig, self.ax = plt.subplots() # example: just one figure


def exists(filename):
    inp='y'
    if os.path.exists(filename+'.json'):
        inp = input('File %s already exists! Overwrite? (y/n)' %(filename+'.json'))
    if inp not in ('y','Y'):
        print('File not saved!')
        return True
    return False

def get_computer_name():
    computer_name = utilities.get_computer_name()
    aliases = {'SPRUCE': 'bluefors', 'HEMLOCK': 'montana'} # different names we want to give the directories for each computer
    if computer_name in aliases.keys():
        computer_name = aliases[computer_name]
    return computer_name


def get_experiment_data_dir():
    '''
    Finds the most recently modified (current) experiment data directory. (Not the full path)
    '''

    latest_subdir = max(glob.glob(os.path.join(get_local_data_path(), '*/')), key=os.path.getmtime)

    return os.path.relpath(latest_subdir, get_local_data_path()) # strip just the directory name

    ## If we're sure that there will only be one directory per date. Bad assumption.
    # exp_dirs = []
    # for name in os.listdir(get_local_data_path()): # all experiment directories
    #     if re.match(r'\d{4}-', name[:5]): # make sure directory starts with "20XX-"
    #         exp_dirs.append(name)

    # exp_dirs.sort(key=lambda x: datetime.strptime(x[:10], '%Y-%m-%d')) # sort by date
    #
    # return exp_dirs[-1] # this is the most recent


def get_data_server_path():
    '''
    Returns full path of the data server's main directory, formatted based on OS.
    '''
    if platform.system() == 'Windows':
        return r'\\SAMBASHARE\labshare\data'
    elif platform.system() == 'Darwin': # Mac
        return '/Volumes/labshare/data/'
    elif platform.system() == 'Linux':
        return '/mnt/labshare/data/'
    else:
        raise Exception('What OS are you using?!? O_O')


def get_local_data_path():
    '''
    Returns full path of the local data directory.
    '''
    return os.path.join(
                os.path.expanduser('~'),
                'data',
                get_computer_name(),
                'experiments'
            )


def get_remote_data_path():
    '''
    Returns full path of the remote data directory.
    '''
    return os.path.join(
                get_data_server_path(),
                get_computer_name(),
                'experiments'
            )


def get_todays_data_dir():
    '''
    Returns name of today's data directory.
    '''
    experiment_path = get_experiment_data_dir()
    now = datetime.now()
    todays_data_path = os.path.join(experiment_path, now.strftime('%Y-%m-%d'))

    # Make local and remote directory
    dirs = [get_local_data_path()]
    if os.path.exists(get_data_server_path()):
        dirs += [get_remote_data_path()]
    for d in dirs:
        try:
            filename = os.path.join(d, todays_data_path)
            if not os.path.exists(filename):
                os.makedirs(filename)
        except Exception as e:
            print(e)

    return todays_data_path


def set_experiment_data_dir(description=''):
    '''
    Run this when you start a new experiment (e.g. a cooldown).
    Makes a new directory in the data folder corresponding to your computer
    with the current date and a description of the experiment.
    '''
    now = datetime.now()
    now_fmt = now.strftime('%Y-%m-%d')

    # Make local and remote directories:
    dirs = [get_local_data_path()]
    if os.path.exists(get_data_server_path()):
        dirs += [get_remote_data_path()]
    for d in dirs:
        try:
            filename = os.path.join(d, now_fmt + '_' + description)
            if not os.path.exists(filename):
                os.makedirs(filename)
        except:
            print('Error making directory %s' %d)


def _md5(filename):
    '''
    Calculates an MD5 checksum for the given file
    '''
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
