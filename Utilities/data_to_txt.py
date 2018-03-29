'''
Convert an HDF5 file to plain txt. Start of a new dataset is marked by #.
From commandline, run "python data_to_txt.py <filename>"
"##" Marks the beginning of a dictionary or object
"#" Marks the beginning of a numpy array
"@@" Marks the end of a dictionary or object
"@" Marks the end of a numpy array
'''
import sys, os
import numpy as np

from Nowack_Lab.Utilities.save import Measurement
from Nowack_Lab.Utilities import utilities

def data_to_txt(filename):
    '''
    filename: path to .h5 or .json file from a Measurement
    '''

    m = Measurement.load(filename)
    filename = os.path.splitext(filename)[0]
    with open(filename+'.txt', 'w') as f:
        # Walk through the dictionary
        def walk(d):
            for key, value in d.items():
                # If a numpy array is found
                if type(value) is np.ndarray:
                    f.write('# %s\n' %key)
                    f.write(str(value.tolist()))
                    f.write('\n@ \n')
                elif 'dict' in utilities.get_superclasses(value):
                    f.write('## %s\n' %key)
                    walk(value)  # walk through the dictionary
                    f.write('@@\n')
                # If the there is some other object
                elif hasattr(value, '__dict__'):
                    # Restrict saving Measurements.
                    if 'Measurement' in utilities.get_superclasses(value):
                        f.write('## %s\n' %key)
                        walk(value.__dict__)
                        f.write('@@\n')
        walk(m.__dict__)

if __name__ == '__main__':
    data_to_txt(sys.argv[1])
