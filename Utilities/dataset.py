



from . import utilities
import os
import h5py
import numpy as np

class Dataset:
    _subsets = []
    def __init__(self, filename=None):
        '''
        Creates the hdf5 file for saving.
        '''

    def get(self, path,slice = False):
        '''
        Gets the element of the hdf5 at path. Path must be a string of
        keys seperated by '/'. If path does not descend to a dataset in the h5,
        then it will return a dictionary with nested keys in the structure of
        the subgroup of the h5. If path does reach a dataset, and that dataset
        is an array, you may give a slice object to specify what data you want
        from the array
        '''

        f = h5py.File(self.filename,'r') #opens the h5 file
        loc = False
        if isinstance(f[path],h5py._hl.dataset.Dataset):
            #is the thing you asked for a dataset, or a group?
            if slice:
                toreturn = f[path][slice]
            else:
                toreturn = f[path][...]
        elif isinstance(f[path],h5py._hl.group.Group):
            datadict = {}
            f.visititems(loaddict(path,f,datadict))
            #visititems recursively applies loaddict at every item of path.
            #datadict modified by reference.
            toreturn = datadict
        else:
            raise Exception('Unrecognized h5 type at specified path')
            toreturn = None
        f.close()
        return toreturn

    def append(self, pathtowrite, datatowrite):
        '''
        Adds new data to dataset at path. Data may be a string, number, numpy
        array, or a nested dict. If a nested dict, leaves must be strings,
        numbers or numpy arrays. Data may not overwrite, however, dicts can be
        used that go through HDF5 groups that already exist.
        '''

    def _appenddatah5(self, numpyarray, pathtowrite, slice):
        '''
        Adds data to an existing array in a h5 file. Can only overwrite nan's,
        such arrays should be instantiated with writetoh5
        '''
        f = h5py.File(self.filename,'w')
        dataset = f[pathtowrite]
        array = np.array(dataset[slice])
        if np.shape(numpyarray) !=  np.shape(array):
            f.close()
            raise Exception('Slice and data are not the same shape')
        if np.all(np.isnan(array)):
            dataset[slice] = numpyarray
        else:
            shouldoverwrite = input('Data already written to ' + pathtowrite +
                                    'at location ' + str(slice) +
                                    '. Type OVERWRITE to overwrite, else, code'
                  'creates a new array at path+_antioverwrite and saves data'
                                                                   + 'there')




        f.close()
    def writetoh5(**kwargs):
        '''
        Tries to write to h5, giving an opportunity to change path
        if there is already data at the path. This only writes complete
        objects to fresh datasets.
        Keyword arguments:

        data (numpy array, str or number): the data to be written. Numpy
                                            arrays must already be sanitized
                                            to ensure they do not contain
                                            objects.

        path (str): location to write data:


        '''
            try:
                f = h5py.File(self.filename,'w')
                f.create_dataset(**kwargs)
                f.close()
            except:
                newpath = input('Path ' + kwargs['path'] +
                                ' has been used already! Type a new path')
                kwargs['path']=newpath
                writetoh5(**kwargs)

    def sanitzenumpy(numpyarray):
        '''
        Makes sure the numpyarray is not object type, and if it is, tries
        casting to float. If that fails, converts it to a string
        '''
        if numpyarray.dtype == np.dtype('object'):
            try:
                numpyarray = np.array(numpyarray, dtype = 'float')
            except:
                print('Could not convert object type numpy array to float.'
                      +' Saving as a string')
                numpyarray = str(list(numpyarray))
        return numpyarray

    def loaddict(path, obj, datadict):
        '''
        Takes the path to an object in an h5 file and the object itself. If the
        object is a group, does nothing, but if the object is a dataset, finds the
        equivalent place in datadict (creating nested dics if needed), and puts the
        contents of obj there.
        '''
        if isinstance(obj, h5py._hl.dataset.Dataset):
            listpath = path.split('/')#split the path into individual keys
            currentdictlevel = datadict
            for key in listpath[:-1]: #iterate through all keys except the last
                if not key in currentdictlevel.keys():
                    currentdictlevel[key] = {} #if it doesn't exist, create it
                currentdictlevel = currentdictlevel[key] #go down one level
            currentdictlevel[listpath[-1]] = obj[...]
            #at the bottom, set the key value equal to the contents of the obj.

    def get_computer_name():
        computer_name = utilities.get_computer_name()
        aliases = {'SPRUCE': 'bluefors', 'HEMLOCK': 'montana'} # different names we want to give the directories for each computer
        if computer_name in aliases.keys():
            computer_name = aliases[computer_name]
        return computer_name

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
