import h5py
import numpy as np
from datetime import datetime
import json
from Nowack_Lab.Utilities.dataset import Dataset

class Saver():
    '''
    This is a wrapper for dataset that adds the functionality for saving
    and getting using a savelocationinstructionfile.
    '''
    _savelocationinstructionfile = ('C:\\ProgramData\\Datasaver\\'
                                        +'jba5962\\path_do_not_modify.json')

    @staticmethod
    def getsavepaths():
        '''
        Returns the current dictionary of save paths
        '''
        with open(Saver._savelocationinstructionfile,'r') as infile:
            return json.load(infile)

    @staticmethod
    def setsavepaths(paths):
        '''
        Sets current dictionary of save paths
        '''
        with open(Saver._savelocationinstructionfile,'w') as outfile:
            json.dump(paths, outfile)
            outfile.truncate()

    def __init__(self,name):
        filestowrite = self.generatefullfilenameandpath(name = name)
        self.datasets = {}
        for key in filestowrite.keys():
            self.datasets[key] = Dataset(filename)

    def make_timestamp(self):
        '''
        Makes a timestamp and filename from the current time.
        '''
        now = datetime.now()
        return now.strftime('%Y-%m-%d_%H%M%S')

    def generatefullfilenameandpath(self, name = ''):
        '''
        Returns a dict of filenames with full paths, generated from the
        get savepaths method

        kwargs:
        name = '' (str): placed after timestamp in filename.
        '''
        paths=getsavepaths()
        filenames = {}
        for key in paths.keys():
            filenames[key] = (paths[key]['exppath'] + make_timestamp() + name)
        return filenames

    def append(*args, **kwargs):
        '''
        append(self, pathtowrite, datatowrite, slice = False)
        Adds new data to dataset at path. Data may be a string, number, numpy
        array, or a nested dict. If a nested dict, leaves must be strings,
        numbers or numpy arrays. Data may not overwrite, however, dicts can be
        used that go through HDF5 groups that already exist.
        '''
        for one_dataset in self.datasets:
            one_dataset.append(*args, **kwargs)

    def get(*args, filetouse = 'localdir', **kwargs):
        '''
        get(self, pathtoget, filetouse = 'localdir', slice = False)
        Takes the path to an object in an h5 file and the object itself.
        If the object is a group, does nothing, but if the object is a
        dataset, finds the equivalent place in datadict (creating nested
        dics if needed), and puts the contents of obj there. Uses the file
        specified by filetouse keyword in the save config file.
        '''
        return self.datasets(filetouse).get(*args,**kwargs)
