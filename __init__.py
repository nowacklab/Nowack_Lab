import time
import os
# Workaround for scipy altering KeyboardInterrupt behavior
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

from IPython import get_ipython, display
ip = get_ipython()

from Nowack_Lab.Utilities import save

from matplotlib import rcParams
rcParams.update({'figure.autolayout': False}) # If set to True, will autoformat layout and prevent axis labels from getting cut off.

# import warnings
# warnings.filterwarnings("ignore") # This was to hide nanmin warnings, maybe not so good to have in general.

## Set experiment data path
inp = input('New experiment? y/(n): ')
if inp in ('y', 'Y'):
    while True:
        inp2 = input('Enter description of experiment: ')
        if inp2.find(' ') != -1:
            print('This is going to be a folder name. Please don\'t use spaces!')
        else:
            break
    save.set_experiment_data_dir(inp2)

## Check for remote data server connection
if not os.path.exists(save.get_data_server_path()):
    print('''SAMBASHARE not connected. Could not find path %s. If you want to change the expected path, modify the get_data_server_path function in Nowack_Lab/Utilities/save.py''' %save.get_data_server_path())





## Importing commonly used packages

ip.run_code('''
import numpy as np
import matplotlib.pyplot as plt
from imp import reload
from time import sleep
import sys, os

## Because I don't know how to do this otherwise, importing all functions and modules that we want in the namespace.
from Nowack_Lab.Utilities import utilities, save, logging, conversions, anim
from Nowack_Lab.Utilities.plotting import plot_mpl
from Nowack_Lab.Utilities.save import Measurement
from Nowack_Lab.Procedures.daqspectrum import DaqSpectrum
from Nowack_Lab.Procedures.heightsweep import Heightsweep
from Nowack_Lab.Procedures.mod2D import Mod2D
from Nowack_Lab.Procedures.mutual_inductance import MutualInductance
from Nowack_Lab.Procedures.navigation import move
from Nowack_Lab.Procedures.planefit import Planefit
from Nowack_Lab.Procedures.scanline import Scanline
from Nowack_Lab.Procedures.scanplane import Scanplane
from Nowack_Lab.Procedures.scanspectra import Scanspectra
from Nowack_Lab.Procedures.squidIV import SquidIV
from Nowack_Lab.Procedures.touchdown import Touchdown
from Nowack_Lab.Procedures.transport import RvsVg, RvsSomething, IV, IVvsVg, FourProbeRes
from Nowack_Lab.Procedures.magnetotransport import RvsB, RvsVg_B
from Nowack_Lab.Instruments.attocube import Attocube
from Nowack_Lab.Instruments.keithley import Keithley2400, Keithley2600, KeithleyPPMS
from Nowack_Lab.Instruments.montana import Montana
from Nowack_Lab.Instruments.nidaq import NIDAQ
from Nowack_Lab.Instruments.piezos import Piezos
from Nowack_Lab.Instruments.preamp import SR5113
from Nowack_Lab.Instruments.squidarray import SquidArray
from Nowack_Lab.Instruments.lockin import SR830
from Nowack_Lab.Instruments.ppms import PPMS
''');
