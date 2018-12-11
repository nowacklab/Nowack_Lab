import h5py
import numpy as np

class Dataset():
    '''
    This code manages saving to and loading from an HDF5 file. It includes
    functionality to allow reading and writing of nested dictionaries with
    leaves including numpy arrays. It further allows iterative saving to those
    numpy arrays with overwrite protection
    '''
    allowedtypes = [float, int,complex]
    allowednonlisttypes = [str, float, int, complex]

    dtype_string = h5py.special_dtype(vlen=str)

    def __init__(self, filename):
        '''
        Creates the hdf5 file for saving.
        '''
        self.filename = filename
        print(self.filename)

    def get(self, pathtoget,slc = False):
        '''
        Gets the element of the hdf5 at path. Path must be a string of
        keys seperated by '/'. If path does not descend to a dataset in the h5,
        then it will return a dictionary with nested keys in the structure of
        the subgroup of the h5. If path does reach a dataset, and that dataset
        is an array, you may give a slice object to specify what data you want
        from the array
        '''
        datadict = {}
        def _loaddict(path, obj):
            '''
            Takes the path to an object in an h5 file and the object itself.
            If the object is a group, does nothing, but if the object is a
            dataset, finds the equivalent place in datadict (creating nested
            dics if needed), and puts the contents of obj there.
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
        f = h5py.File(self.filename,'r') #opens the h5 file
        loc = False
        if isinstance(f[pathtoget],h5py._hl.dataset.Dataset):
            #is the thing you asked for a dataset, or a group?
            if slc:
                toreturn = f[pathtoget][slc]
            else:
                toreturn = f[pathtoget][...]
        elif isinstance(f[pathtoget],h5py._hl.group.Group):
            datadict = {}
            f[pathtoget].visititems(_loaddict)
            #visititems recursively applies loaddict at every item of path.
            #datadict modified by reference.
            toreturn = datadict
        else:
            raise Exception('Unrecognized h5 type at specified path')
            toreturn = None
        f.close()
        return toreturn

    def append(self, pathtowrite, datatowrite, slc = False,
               chunks=None):
        '''
        Adds new data to dataset at path. Data may be a string, number, numpy
        array, or a nested dict. If a nested dict, leaves must be strings,
        numbers or numpy arrays. Data may not overwrite, however, dicts can be
        used that go through HDF5 groups that already exist.

        Params:
        ~~~~~~~
        pathtowrite: (string): path to save dataset.  Starts with '/'
        datatowrite: (string, number, numpy array, list, nested dict): data to write
        slc:         (tuple or False): if slc: existing[slc] = datatowrite

        '''
        [cleandatatowrite, dtype] = self.sanitize(datatowrite)
        if isinstance(cleandatatowrite, dict) and dtype is dict:
            def _loadhdf5(path, obj, dtype):
                '''
                Takes the path to an object in an dict file and the object
                itself. If the object is a dict, does nothing, but if the
                object is not, finds the equivalent place in f (creating nested
                groups if needed), and puts the contents of obj there.
                '''
                sep = '/'
                h5path = pathtowrite + sep.join([str(place) for place in path])
                if not isinstance(obj, dict):
                    self._writetoh5(data = obj, path = h5path, dtype=dtype,
                                    chucks=chucks)
            self.dictvisititems(cleandatatowrite, _loadhdf5)
        elif isinstance(cleandatatowrite, (np.ndarray, list) +
                                            tuple(self.allowedtypes))  and slc:
                    self._appenddatah5(self.filename, cleandatatowrite,
                                       pathtowrite, slc, dtype)
        else:
            #print(datatowrite)
            self._writetoh5(data=cleandatatowrite, 
                            path=pathtowrite, 
                            dtype=dtype,
                            chunks=chunks)



    def _writetoh5(self, **kwargs):
        '''
        Tries to write to h5, giving an opportunity to change path
        if there is already data at the path. This only writes complete
        objects to fresh datasets.
        Keyword arguments:

        data (numpy array, str or number): the data to be written. Numpy
                                            arrays must already be sanitized
                                            to ensure they do not contain
                                            objects.

        path (str): location to write data. should be in hdf5 path format.
        '''
        f = h5py.File(self.filename,'a')
        try:
            f[kwargs['path']]
            f.close()
            newpath = input('Path ' + kwargs['path'] +
                            ' has been used already! Type a new path: ')
            kwargs['path']=newpath
            self._writetoh5(**kwargs)
        except KeyError:
            f.create_dataset(kwargs['path'], data = kwargs['data'], 
                             dtype=kwargs['dtype'], 
                             chunks=kwargs['chunks'])
            f.close()


    def dictvisititems(self, dictionary, function):
        '''
        Applies function at every node of nested dict, passing the path as a
        list as the first argument, and the object itself as the second.
        '''
        def recursivevisit(dictionary, function, keylist):
            for key in dictionary.keys():
                [cleandatatowrite, dtype] = dictionary[key]
                function(keylist + [key], cleandatatowrite, dtype)
                if isinstance(cleandatatowrite, dict):
                    recursivevisit(cleandatatowrite, function, keylist + [key])
        recursivevisit(dictionary, function, [])

    def _appenddatah5(self, filename, numpyarray, pathtowrite, slc, dtype):
        '''
        Adds data to an existing array in a h5 file. Can only overwrite nan's
        and empty strings,
        such arrays should be instantiated with writetoh5
        '''
        f = h5py.File(filename,'r+')
        dataset = f[pathtowrite]
        newshape = np.shape(numpyarray)
        oldstuff = dataset[slc]
        oldshape = np.shape(np.squeeze(oldstuff))
        if newshape !=  oldshape:
            f.close()
            print(numpyarray)
            print(oldstuff)
            raise ValueError('Slice shape '+ str(oldshape) +
             ' does not match data shape ' + str(newshape))
        elif np.all(np.isnan(oldstuff)) or np.all(oldstuff == ''):
            dataset[slc] = numpyarray
            f.close()
        else:
            shouldoverwrite = input('Data already written to ' + pathtowrite +
                                    ' at location ' + str(slc) +
                                    '. Type OVERWRITE to overwrite, else, code'
                  ' creates a new array at antioverwrite_ + file and saves '
                                                              +'data + there')
            if shouldoverwrite == 'OVERWRITE':
                dataset[slc] = numpyarray
                f.close()
            else:
                fao = h5py.File('antioverwrite_' + filename,'a')
                try:
                    fao.create_dataset(pathtowrite, data = dataset, dtype=dtype)
                    fao[pathtowrite][slc] = numpyarray
                    fao.close()
                    f.close()
                except:
                    fao.close()
                    f.close()
                    self._appenddatah5('antioverwrite_' + filename,
                                        numpyarray, pathtowrite, slc, dtype)

    def sanitize(self,data):
        '''
        Sanitizes input before loading into an h5 file. If sanitization fails,
        prints a message and converts to a string.

        returns:
        ~~~~~~~~
        [cleandata, dtype]
            cleandata is data that has been cleaned to fit nicely into hdf5
                If type(cleandata) is dict, 
                    cleandata[key] = sanitize(data[key]) which is a list

            dtype is the type of dtype passed to h5py's create_dataset
                None if you do not want to overwrite cleandata's dtype
        '''
        if any([isinstance(data, sometype) for sometype in
                                                    self.allowednonlisttypes]):
            cleandata = data
            dtype = None
        elif type(data) == np.ndarray:
            if data.dtype in [np.dtype(a) for a in self.allowedtypes]:
                cleandata = data
                dtype = None
            else:
                try:
                    cleandata = np.array(data, dtype = 'float')
                    dtype = None
                except ValueError:
                    try:
                        cleandata = np.asarray(data, dtype=np.bytes_)
                        dtype = self.dtype_string
                    except ValueError:
                        print('Could not convert dtype of numpy array to float.'
                            +' Saving as a string')
                        cleandata = str(data)
                        dtype = None

        elif type(data) == list:
            if all([any([isinstance(elem, sometype) for sometype in
                                        self.allowedtypes]) for elem in data]):
                cleandata = data
                dtype = None
            else:
                try: 
                    asciidata = [str(n).encode('ascii', 'ignore') 
                                 for n in data] 
                    cleandata = asciidata
                    dtype = self.dtype_string
                except:
                    print('List with unauthorized types. Most likely something' +
                                ' that could not be converted to strings. ' + 
                                'Attempting to convert to string.')
                    try:
                        cleandata = str(data)
                        dtype = None
                        print('Success!')
                    except:
                        shouldcontinue = input('COULD NOT CONVERT TO STRING. '
                                    + 'DATA WILL NOT BE SAVED. Continue y/(n)')
                        if shouldcontinue != 'y':
                            raise TypeError('TypeError: could not convert to h5')
                        cleandata = 'unconvertable'
                        dtype = None
        elif isinstance(data, dict):
            cleandata = {}
            dtype = dict
            for key in data.keys():
                cleandata[key] = self.sanitize(data[key])
        else: #todo: add conversion to utf-8 for string containing numpys
            print('Could not recognize type. Attempting to convert to string.')
            try:
                cleandata = str(data)
                dtype = None
                print('Success!')
            except:
                shouldcontinue = input('COULD NOT CONVERT TO STRING. '
                + 'DATA WILL NOT BE SAVED. Continue y/(n)')
                if shouldcontinue != 'y':
                    raise TypeError('TypeError: could not convert to h5')
                cleandata = 'unconvertable'
                dtype = None

        return [cleandata, dtype]

    def dim_get(self, datasetname):
        '''
        returns f[datasetname].dims
        '''
        with h5py.File(self.filename,'r') as f:
            try:
                return f[datasetname].dims
            except:
                raise

    def make_dim(self, datasetname, dim_number, label, dim_dataset_name,
                 dim_name):
        '''
        For a given dataset named datasetname that contains an array, label 
        the dimensions in h5.  This is how you make xarray import these
        h5 files without conversion

        Params:
        ~~~~~~~
        datasetname (string):       Dataset name
        dim_number (int):           Dimension number (first dimension is 0)
        label (string):             Name of dimension.  
                                    Appears in metadata of datasetname 
                                        under DIMENSION_LABELS
                                    Appears in attributes in xarray
        dim_dataset_name (string):  Name of the dimension dataset.
                                    Must be a previously created datset.  
                                    Appears as the xarray dimension name
        dim_name (string):          name of the dimension.   
                                    Appears in metadata of dim_dataset_name
                                    Does not appear in xarray
        '''
        with h5py.File(self.filename, 'a') as f:
            try:
                f[datasetname].dims[dim_number].label = label
                f[datasetname].dims.create_scale(f[dim_dataset_name], dim_name)
                f[datasetname].dims[dim_number].attach_scale(
                                        f[dim_dataset_name])
            except:
                raise

    def dim_set(self, datasetname, dim_number, label):
        '''
        This is probably useless!

        for /datasetname, set dim[dim_number] = label
        Params:
        ~~~~~~~
        datasetname (string):   dataset name
        dim_number (int):       dimension number
        label (string):         name of dimension
        '''
        with h5py.File(self.filename,'a') as f:
            try:
                f[datasetname].dims[dim_number].label = label
            except:
                raise

    def dim_create_scale(self, datasetname, dim_dataset_name, dim_name):
        '''
        This is probably useless so don't use it!!

        creates scale for the given dataset
        f[datasetname].create_scale(f[dim_dataset_name], dim_name)

        Params:
        ~~~~~~~
        datasetname (string):       dataset name
        dim_dataset_name (string):  name of the dimension dataset
        dim_name (string):          name of the dimension 
        '''
        with h5py.File(self.filename, 'a') as f:
            try:
                f[datasetname].dims.create_scale(f[dim_dataset_name], dim_name)
            except:
                raise
        
    def dim_attach_scale(self, datasetname, dim_number, dim_dataset_name):
        '''
        This is probably unnecessary, so don't use it!

        f[datasetname].dims[dim_number].attach_scale(f[dim_dataset_name])
        '''
        with h5py.File(self.filename, 'a') as f:
            try:
                f[datasetname].dims[dim_number].attach_scale(
                                        f[dim_dataset_name])
            except:
                raise

    def get_attr(self, datasetname, *args, **kwargs):
        '''
        Just a wrapper for dataset.attrs.get(*args, **kwargs)
        params:
        ~~~~~~~
        datasetname (string): name of dataset, full path
        name (string): name of attribute to get
        default=None (string): defaults to getting this one if 
                                name does not exist

        '''
        with h5py.File(self.filename, 'r') as f:
            try:
                return f[datasetname].attrs.get(*args, **kwargs)
            except:
                raise
    def create_attr(self, datasetname, name, data, dtype=None, **kwargs):
        '''
        Just a wrapper for dataset.attrs.create(*args, **kwargs)

        There is no warning for overwriting so DON'T BE STUPID

        params:
        ~~~~~~~
        datasetname (string): name of dataset, full path
        name (string): name of attribute to set
        data: value of attribute, will be put through np.array(data)
        shape=None (tuple): shape of attribute, overrides data.shape
                        I think it reshapes
        dtype=None (numpy dtype): data type for the attribute, overrides
                            data.dtype
        '''
        with h5py.File(self.filename, 'a') as f:
            try:
                if type(data) is str:
                    dtype=self.dtype_string
                f[datasetname].attrs.create(name, data,
                                            dtype=dtype, **kwargs)
            except:
                raise
                

    def create_attr_dict(self, datasetname, dict_to_attr, prefix=''):
        '''
        For a given dataset named datasetname, take a dictionary 
        dict_to_attr and stuff it into the attributes of datasetname.
        Prepend prefix to each key to avoid overwriting.  

        There is no warning for overwriting so DON'T BE STUPID

        params:
        ~~~~~~
        datasetname (string): name of dataset, full path
        dict_to_attr (dict):  dictionary of values.  
                              Supported formats: int, string, float, 
                              complex, list.  Anything else gets 
                              turned into a string.
        prefix (string):      prefix to prepend to keys when adding to 
                              datasetname
        '''
        with h5py.File(self.filename, 'a') as f:
            for key in dict_to_attr.keys():
                data = dict_to_attr[key]
                dtype = None
                if type(data) not in self.allowedtypes:
                    if type(data) not in [str, list]:
                        print('create_attr_dict: ' + 
                        '{0} is a {1}.  Not supported.  Saving str'.format(
                        key, type(data)))

                    data = str(data)

                if type(data) is str:
                    dtype=self.dtype_string

                f[datasetname].attrs.create(prefix+key, data, dtype=dtype)


