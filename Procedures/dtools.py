import h5py
import numpy as np
import json
import os
from datetime import datetime, timedelta
import re
import fnmatch

class Data(dict):
    def __init__(self, *args, **kwargs):
        super(Data, self).__init__(*args, **kwargs)
        self.__dict__ = self
    def __dir__(self):
        a = list(self.__dict__)
        for key in self.keys():
            a.append(key)
        return a

def loadData(fname):
    '''
    take a path for a data file and return a dictionary with the same
    data and keys

    calls the recursive loader function to load data with nested structure
    '''
    f = h5py.File(fname, "r")
    return Data(loader(f))

def loader(obj):
    '''
    recursively load the Groups in a h5py file.
    '''
    data = Data()
    for key in obj.keys():
        if type(obj[key]) is h5py._hl.dataset.Dataset:
            data[key] = obj[key][:]
        elif type(obj[key]) is h5py._hl.group.Group:
            data[key] = loader(obj[key])
    return data

def loadConfig(fname):
    '''
    take a path for a configuration json file and return a dictionary with
    the configuration of all the instruments
    '''
    with open(fname) as f:
        config = json.load(f)
    #get rid of annoying py/object, py/state keys
    config = config["py/state"]
    config = cleanDict(config)
    #get rid of useless readout of all DAQ channels
    if "daq" in config.keys():
        config["daq"] = {"input range": config["daq"]["input range"],
                         "output range": config["daq"]["output range"]}
    return Data(config)

def loadMeasurement(fname):
    '''
    take a path for a configuation json file or a h5 datafile and return a dictionary
    with both the data and the configuration
    '''
    [fname, ext] = os.path.splitext(fname)
    if ext not in [".json", ".h5"]:
        print("provided file not a json or h5 file, data not loaded")
        return
    data = loadData(fname + ".h5")
    config = loadConfig(fname + ".json")
    measurement = {"config": config, "data": data}
    return Data(measurement)

def cleanDict(d):
    '''
    Take a configuration dictionary and clean out entries used to reconstruct
    python objects that clutter up the file
    '''
    for key in d.keys():
        if type(d[key]) is dict:
            if "py/state" in d[key].keys():
                d[key] = d[key]["py/state"]
            d[key] = cleanDict(d[key])
    return d


def dictStructure(data_dict, indent=0):
    '''
    Returns the sructure of the keys in the supplied dictionary.
    '''
    for key, val in data_dict.items():
        #exclude useless keys used to re-instantiate objects
        if key not in ["py/object", "py/state", "dtype"]:
            print('  ' * indent + str(key))
        if isinstance(val, dict):
            dictStructure(val, indent+1)

def binData(data, bin_size):
    '''
    Takes a 1D data set and divides it in to bins of size bin_size as best as possible
    Left over data that does not fit nicely into a bin is not used.
    Within each bin, the average is computed
    '''
    num_bins = int(len(data)/bin_size)
    truncated_data = data[0:num_bins*bin_size]
    data_reshape = np.reshape(truncated_data, (num_bins, -1))
    data_ave = np.zeros(data_reshape.shape[0])
    for i in range(data_reshape.shape[0]):
        bin_ave = np.mean(data_reshape[i,:])
        data_ave[i] = bin_ave
    return data_ave

def binCut(cut, bin_size):
    '''
    Takes a linecut and bins the signal and the position parts, while maintaining the
    location and the timestamp structure of the dict
    '''
    binned = cut
    binned["signal"] = binData(cut["signal"], bin_size)
    binned["position"] = binData(cut["position"], bin_size)
    binned["label"] = cut["label"] + " binned @ " + str(bin_size)
    return binned

def finder(d, key, found=[]):
    '''
    recursively search a dictionary d for all instances of
    a certain key.

    returns a list of entries that all had the requested key
    '''
    if key in d:
        found.append(d[key])
    for k in d:
        if isinstance(d[k], dict):
            found = finder(d[k], key, found)
    return found

def reformat_time(timestamp):
    '''
    takes an org-mode formatted timestamp and re-formats the string to match the
    format used when saving datafiles.

    INPUT: timestamp (str) - a timestamp formatted in the default org-mode format
    [2016-12-20 Tue 12:04]

    RETURNS: date (datetime.datetime) - a timestamp formatted in the way that
    datafiles are saved

    EXAMPLE: date =  dtools.format_timestamp("[2016-12-20 Tue 12:04]")
    '''
    date = datetime.strptime(timestamp[1:11]+timestamp[15:21],
                             "%Y-%m-%d %H:%M")
    return date

def time_from_file(filename):
    '''
    takes a filename and finds the timestamp of the measurement using a regex match
    '''
    datafile_regex = re.compile( "[0-2][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]_[0-2][0-9][0-6][0-9][0-6][0-9]")
    match = datafile_regex.search(filename)
    if match:
        return datetime.strptime(match.group(), "%Y-%m-%d_%H%M%S")
    else:
        return None

def file_from_time(timestamp, directory = "/Volumes/labshare/data"):
    '''
    takes a timestamp and returns datafiles generated with a maching timestamp
    the search begins at the specified directory, defaulting to /Volumes/
    if no match is found, the dataset with the closest timestamp is generated
    '''
    #create an array of candidate timestamps
    matches = None
    diff = timedelta.max

    #reformat supplied org timestamp into a datetime.datetime object
    timestamp = reformat_timestamp(timestamp)

    #iterate through directories, looking at datafiles
    for subidr, dirs, files in os.walk(directory):
        for filename in files:
            time = time_from_file(filename)
            if time is not None:
                if abs(time - timestamp) <= diff:
                    diff = abs(time - timestamp)
                    matches = filename
    return matches
