from jsonpickle.ext import numpy as jspnp
import json, os, jsonpickle as jsp, numpy as np, subprocess, numpy
from datetime import datetime as dt
jspnp.register_handlers() # what is purpose of this line?
import h5py, glob, matplotlib, platform, hashlib, shutil, socket
import matplotlib.pyplot as plt
from . import utilities
import Nowack_Lab # Necessary for saving as Nowack_Lab-defined types

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


class Saver(object):
    subdirectory = ''  # Formerly "appendedpath".
        # Name of subdirectory off the main data directory where data is saved.

    def __init__(self):
        super().__init__()  # To deal with multiple inheritance mro
        self.make_timestamp_and_filename()

    def __getstate__(self):
        '''
        Returns a dictionary of everything that will save to JSON.
        This excludes numpy arrays which are saved to HDF5.
        '''
        def walk(d):
            '''
            Walk through dictionary and remove numpy arrays and matplotlib objs.
            '''
            d = d.copy()  # make sure we don't modify original dictionary
            keys = list(d.keys())  # make list to avoid dictionary changing size

            for k in keys:
                # Don't save numpy arrays to JSON
                if type(d[k]) is np.ndarray:
                    d[k] = None

                # Don't save matplotlib objects to JSON
                d[k] = _remove_mpl(d[k])

                # Walk through dictionaries
                if isinstance(d[k], dict):
                    d[k] = walk(d[k])

            return d

        return walk(self.__dict__)


    def __setstate__(self, state):
        '''
        Default method for loading from JSON.
        `state` is a dictionary.
        '''
        self.__dict__.update(state)


    def _copy_to_remote(self, localpath, remotepath):
        '''
        Copies h5, json, and pdf files at localpath.xxx to remotepath.xxx and
        verifies the copy with a md5 checksum.
        '''
        if remotepath is not None:
            try:
                # Loop over filetypes
                for ext in ['.h5','.json','.pdf']:
                    if os.path.isfile(localpath + ext):
                        local_checksum = _md5(localpath + ext)
                        shutil.copyfile(localpath + ext, remotepath + ext)
                        remote_checksum = _md5(remotepath + ext)

                        # Compare checksums
                        if local_checksum != remote_checksum:
                            print('%s checksum failed! \
                            Cannot trust remote file %s' %(ext, remotepath + ext))

            except Exception as e:
                print('Saving to data server failed!\n\n\
                Exception details: %s\n\n\
                remote path: %s\n\
                local path: %s' %(e, remotepath, localpath)
                )
        else:
            print('Not connected to %s, data not saved remotely!'\
                                %get_data_server_path())


    @classmethod
    def _load(cls, filename=None):
        '''
        Basic load method. Loads from JSON, then HDF5.

        Options for filename:
        - None: Load last saved object of this class
        - An index: Select from a list of objects of this class and select
        an object to load with the index (e.g. -2 gives the second-to-last)
        - a filename: Attempt to load file from current experiment directory.
        - a full path: Load file from given path
        '''

        if filename is None: # tries to find the last saved object
            filename = -1

        if type(filename) is int:
            experiment = os.path.join(get_local_data_path(),
                        get_todays_data_dir(), '..')
            paths = get_data_paths(experiment, cls.__name__)

            try:
                filename = paths[filename] # filename was an int originally
            except:
                raise Exception('could not find %s to load.' %cls.__name__)

        elif os.path.dirname(filename) == '': # if no path specified
            os.path.join(get_local_data_path(), get_todays_data_dir(), filename)

        # Remove file extensions
        filename = os.path.splitext(filename)[0]

        obj = Saver._load_json(filename+'.json')
        obj._load_hdf5(filename+'.h5')
        return obj


    def _load_hdf5(self, filename):
        '''
        Loads data from HDF5 files. Will walk through the HDF5 file and populate
        the object's dictionary and subdictionaries (already loaded by JSON)
        '''
        with h5py.File(filename, 'r') as f:
            def walk(d, f):
                '''
                Walk through dictionary and populate with h5 data.
                '''
                for key in f.keys():
                    # Dictionary or object
                    if f.get(key, getclass=True) is h5py._hl.group.Group:
                        if key[0] == '!': # it's an object
                            # [1:] strips the !; walk through the subobject
                            if d != {} and key[1:] in d:
                                walk(d[key[1:]].__dict__, f[key])
                        else:  # it's a dictionary
                            if key not in d:  # Needed for Zurich _save_dict
                                d[key] = dict()  # Empty dict to accept data
                            walk(d[key], f.get(key))

                    # Dataset
                    else:
                        d[key] = f[key][:]

                    # If a dictionary key was an int, convert it back
                    try:
                        newkey = int(key)  # test if can convert to an integer
                        value = d.pop(key)  # grab the value
                        d[newkey] = value  # new key that is integer
                    except:
                        pass

                return d

            walk(self.__dict__, f)  # start walkin'


    @staticmethod
    def _load_json(json_file):
        '''
        Loads an object from JSON.
        '''
        def walk(d):
            '''
            Walk through dictionary to check for classes not in the namespace.
            These will all be loaded as Savers.
            '''
            keys = list(d.keys())  # static list; dictionary changes size
            for key in keys:
                if 'py/object' in key:  # we found some sort of object
                    classname = d['py/object']
                    try:
                        exec(classname)  # see if class is in the namespace
                    except:
                        if 'Procedures' in classname:
                            d['py/object'] = classname.replace('Procedures',
                                    'Measurements')  # for legacy loading
                        else:
                            print('Cannot find class definition {0}: '.format(
                                classname) + 'using Saver object')
                            d['py/object'] = 'Nowack_Lab.Utilities.save.Saver'
                        if 'daqspectrum' in d['py/object']: # legacy
                            d['py/object'] = d['py/object'].replace('daq', '')
                if isinstance(d[key], dict):
                    d[key] = walk(d[key])
            return d

        with open(json_file, encoding='utf-8') as f:
            obj_dict = json.load(f)

        obj_dict = walk(obj_dict)

        # Decode with jsonpickle.
        obj_string = json.dumps(obj_dict)
        obj = jsp.decode(obj_string)

        return obj


    def _make_paths(self, filename):
        '''
        Generates paths for the local and remote save directories.

        Arguments:
        filename (string): Desired filename or path. None: auto-generated

        Returns:
        localpath, remotepath - paths to local and remote directories
        remotepath is None if data server not accessible
        '''
        # Saving to the experiment-specified directory
        if filename is None:
            if not hasattr(self, 'filename'):  # if you did not make a filename
                self.make_timestamp_and_filename()
            filename = self.filename

        # If you did not specify a filename with a path, generate a path
        if os.path.dirname(filename) == '':
                local_path = os.path.join(get_local_data_path(),
                                          get_todays_data_dir(),
                                          self.subdirectory,
                                          filename)
                remote_path = os.path.join(get_remote_data_path(),
                                           get_todays_data_dir(),
                                           self.subdirectory,
                                           filename)
        # Else, you specified some sort of path
        else:
            local_path = filename
            remote_path = os.path.join(get_remote_data_path(),
                                        '..', 'other',
                                        *filename.replace('\\', '/').split('/')[1:])
            # removes anything before the first slash. e.g. ~/data/stuff -> data/stuff
            # All in all, remote_path should look something like: .../labshare/data/bluefors/other/

        # Make local directory
        local_dir = os.path.split(local_path)[0]  # split off the filename
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # Make remote directory
        if os.path.exists(get_data_server_path()):
            remote_dir = os.path.split(remote_path)[0]
            if not os.path.exists(remote_dir):
                os.makedirs(remote_dir)
        else:
            remote_path = None

        return local_path, remote_path


    def _save(self, filename=None):
        '''
        Saves data in different formats:
        - JSON: contains the full dictionary structure of the saved object,
            minus numpy arrays which are saved to h5 instead.
        - h5: contains dictionary structure of variables involving numpy arrays,
            as well as all the data contained in the numpy arrays
        - pdf: quick PDF copy of the figure under self.fig

        Keyword arguments:
        filename -- Options:
        - None (recommended): filename is generated automatically from the timestamp
        - a filename: saved to default experiment directory with the given filename
        - partial path (e.g. /testing/myfile): saved to default experiment
        directory under the specified subdirectory (e.g. testing)
        - full path (e.g. C:/Documents/testing/myfile): saved to the specified full path

        Default location of experiments directory:
        - Local: ~/data/
        - Remote: /labshare/data/

        If custom paths are used, they will be saved remotely to the "other"
        directory rather than the "experiments" directory.
        '''

        localpath, remotepath = self._make_paths(filename)

        # Save locally
        self._save_hdf5(localpath)  # must save h5 first
        self._save_json(localpath)
        if hasattr(self, 'fig'):
            if self.fig is not None:
                self.fig.savefig(localpath+'.pdf', bbox_inches='tight')

        self._copy_to_remote(localpath, remotepath)

        # Test loading
        try:
            self.load(localpath)
        except:
            raise Exception('Reloading failed, but object was saved!')


    def _save_hdf5(self, filename):
        '''
        Save numpy arrays to h5py. Walks through the object's dictionary
        and any subdictionaries and subobjects, picks out numpy arrays,
        and saves them in the hierarchical HDF5 format.

        A subobject is designated by a ! at the beginning of the variable name.
        '''

        with h5py.File(filename+'.h5', 'w') as f:
            # Walk through the dictionary
            def walk(d, group):
                for key, value in d.items():
                    key = str(key)  # Some may be ints; convert to str
                    key = key.replace('/','-')  ## HACK: Zurich dict keys have / and will create unwanted groups in the base of the tree

                    if type(value) is np.ndarray:
                        # Save the numpy array as a dataset
                        d = group.create_dataset(key, value.shape,
                            compression = 'gzip', compression_opts=9,
                            dtype=np.dtype('float64'))
                        d.set_fill_value = np.nan
                        d[...] = value

                    # If a dictionary
                    elif isinstance(value, dict):
                        new_group = group.create_group(key) # make a group with the dictionary name
                        walk(value, new_group) # walk through the dictionary

                    # If some other object
                    elif hasattr(value, '__dict__'):
                        if isinstance(value, Saver):  # only Savers
                            # mark object by "!" and make a new group
                            new_group = group.create_group('!'+key)
                            walk(value.__dict__, new_group)  # walk through obj

            walk(self.__dict__, f)


    def _save_json(self, filename):
        '''
        Saves the Saver object to JSON with given filename.
        __getstate__ determines what variables are saved.
        '''
        if not exists(filename+'.json'):
            obj_string = jsp.encode(self)
            obj_dict = json.loads(obj_string)
            with open(filename+'.json', 'w', encoding='utf-8') as f:
                json.dump(obj_dict, f, sort_keys=True, indent=4)


    @classmethod
    def load(cls, filename=None):
        '''
        Basic load method. Just calls _load. May overwrite this for subclasses.
        Be sure to use subclass._load method, not Saver._load
        '''
        obj = Saver._load(filename)
        return obj


    def make_timestamp_and_filename(self):
        '''
        Makes a timestamp and filename from the current time.
        '''
        now = dt.now()
        self.timestamp = now.strftime("%Y-%m-%d %I:%M:%S %p")
        self.filename = now.strftime('%Y-%m-%d_%H%M%S')
        self.filename += '_' + self.__class__.__name__


    def save(self, filename=None, **kwargs):
        '''
        Basic save method. Just calls _save. May overwrite this for subclasses.
        '''
        self._save(filename, **kwargs)


def exists(filename):
    inp='y'
    if os.path.exists(filename+'.json'):
        inp = input('File %s already exists! Overwrite? (y/n)' %(filename+'.json'))
    if inp not in ('y','Y'):
        print('File not saved!')
        return True
    return False


def get_computer_name():
    computer_name = socket.gethostname()
    aliases = {'SPRUCE': 'bluefors', 'HEMLOCK': 'montana'} # different names we want to give the directories for each computer
    if computer_name in aliases.keys():
        computer_name = aliases[computer_name]
    return computer_name


def get_data_paths(experiment='', kind=''):
    '''
    Returns a list of the paths to every data file from a given experiment
    directory. Returns all kinds of saved objects unless one is specified by the
    kind kwarg.

    Keyword arguments:
    experiment (string): Full path of the experiment directory
        (uses current experiment if none given)
    kind (string): name of the Saver subclass
    '''
    # Use current experiment if none given
    if experiment == '':
        experiment = os.path.join(get_local_data_path(),
                                get_experiment_data_dir()
                            )

    # Get a list of all the date directories
    p = os.path.join(experiment, '*')
    g = list(glob.iglob(p))
    g.sort()

    paths = []
    # Iterate over dates and add all paths to given data files
    for dir in g:
        p = os.path.join(dir, '*%s.json' %kind)
        g2 = list(glob.iglob(p))
        g2.sort()
        paths += g2

    return paths


def get_experiment_data_dir():
    '''
    Returns the current experiment data directory. (Not the full path)
    '''
    path = os.path.join(os.path.dirname(__file__),
                                'setup',
                                get_computer_name() + '.txt'
                            )
    with open(path, 'r') as f:
        exp = f.read()

    return exp.rstrip()  # rstrip to remove /n, /r etc.


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
    now = dt.now()
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


def open_experiment_data_dir():
    filename = get_local_data_path()
    if platform.system() == "Windows":
        os.startfile(filename)
    else:
        opener ="open" if platform.system() == "Darwin" else "xdg-open"
        subprocess.call([opener, filename])


def set_experiment_data_dir(description=''):
    '''
    Run this when you start a new experiment (e.g. a cooldown).
    Makes a new directory in the data folder corresponding to your computer
    with the current date and a description of the experiment.
    '''
    now = dt.now()
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

    path = os.path.join(os.path.dirname(__file__),
                                'setup',
                                get_computer_name() + '.txt'
                            )
    with open(path, 'w') as f:
        f.write(now_fmt + '_' + description)


def _md5(filename):
    '''
    Calculates an MD5 checksum for the given file
    '''
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def _remove_mpl(obj):
    def _is_mpl_object(obj):
        if hasattr(obj, '__module__'):  # Check if NOT a built-in type
            if 'matplotlib' in obj.__module__:
                return True

    if _is_mpl_object(obj):
        obj = None

    # check for lists of mpl objects
    elif type(obj) is list:
        if len(obj) > 0:
            if _is_mpl_object(obj[0]):
                obj = None

    return obj
