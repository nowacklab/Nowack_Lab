import h5py
import numpy as np
from datetime import datetime
import json
import os
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
        for path in paths.keys():
            if not os.path.exists(paths[path]['exppath']):
                os.makedirs(paths[path]['exppath'])
        with open(Saver._savelocationinstructionfile,'w') as outfile:
            json.dump(paths, outfile)
            outfile.truncate()

    @staticmethod
    def make_timestamp(subday = True):
        '''
        Makes a timestamp and filename from the current time. Subday
        determines whether hours, minutes and seconds are included.
        '''
        now = datetime.now()
        if subday:
            timestamp = now.strftime('%Y-%m-%d_%H%M%S_')
        else:
            timestamp =  now.strftime('%Y-%m-%d_')
        return timestamp



    def __init__(self, name = '', addtimestamp = True):
        filestowrite = self.generatefullfilenameandpath(name = name,
                                                    addtimestamp=addtimestamp)
        self.datasets = {}
        for key in filestowrite.keys():
            self.datasets[key] = Dataset(filestowrite[key])

    def savefigure(self, figure, name):
        paths = getsavepaths
        for key in paths.keys():
            figure.savefig(paths[key]['exppath'] + '\\' + make_timestamp +
                                                            'figure_' + name)
    def generatefullfilenameandpath(self, name = '', addtimestamp = True):
        '''
        Returns a dict of filenames with full paths, generated from the
        get savepaths method

        kwargs:
        name = '' (str): placed after timestamp in filename.
        '''
        paths = self.__class__.getsavepaths()
        filenames = {}
        if addtimestamp:
            timecomp = self.__class__.make_timestamp()
        else:
            timecomp = ''
        for key in paths.keys():
            filenames[key] = (paths[key]['exppath']
                                    +  '\\' + timecomp
                                    + name + '.hdf5')
        return filenames

    def append(self,*args, **kwargs):
        '''
        append(self, pathtowrite, datatowrite, slice = False)
        Adds new data to dataset at path. Data may be a string, number, numpy
        array, or a nested dict. If a nested dict, leaves must be strings,
        numbers or numpy arrays. Data may not overwrite, however, dicts can be
        used that go through HDF5 groups that already exist.
        '''
        for dataset_name in self.datasets.keys():
            self.datasets[dataset_name].append(*args, **kwargs)

    def get(self,*args, filetouse = 'local', **kwargs):
        '''
        get(self, pathtoget, filetouse = 'localdir', slice = False)
        Takes the path to an object in an h5 file and the object itself.
        If the object is a group, does nothing, but if the object is a
        dataset, finds the equivalent place in datadict (creating nested
        dics if needed), and puts the contents of obj there. Uses the file
        specified by filetouse keyword in the save config file.
        '''
        return self.datasets[filetouse].get(*args,**kwargs)
