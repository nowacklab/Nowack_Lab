from Nowack_Lab import DisableInits
import sys
import os
<<<<<<< HEAD
import time

def set_experiment_data_path():
    from Nowack_Lab.Utilities import save

    ## Set experiment data path
    try:
        print('Current experiment: %s' %save.get_experiment_data_dir())
    except:
        pass
    inp = input('New experiment? y/(n): ')
    if inp in ('y', 'Y'):
        while True:
            inp2 = input('Enter description of experiment: ')
            if inp2.find(' ') != -1:
                print('This is going to be a folder name. ' + 
                      'Please don\'t use spaces!')
            else:
                break
        save.set_experiment_data_dir(inp2)

def check_remote_data_server_connection():
    ## Check for remote data server connection
    if not os.path.exists(save.get_data_server_path()):
        print(
            "SAMBASHARE not connected. Could not find path {}. ".format( 
                save.get_data_server_path()
            ) +
            "If you want to change the expected path, modify the " + 
            "get_data_server_path function in Nowack_Lab/Utilities/save.py"
            );



def import_packages():
    ## Importing commonly used packages
    from IPython import get_ipython
    ip = get_ipython()
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
    from Nowack_Lab.Procedures.daqspectrum import DaqSpectrum, SQUIDSpectrum
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
    from Nowack_Lab.Procedures.transport import RvsVg, RvsTime, RvsT
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
    #from Nowack_Lab.Fun.callme import call
    ''');

if (DisableInits.disable_all_inits is False):
    # Workaround for scipy altering KeyboardInterrupt behavior
    os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

    set_experiment_data_path()
    check_remote_data_server_connection()

    from matplotlib import rcParams
    # If set to True, will autoformat layout and prevent axis labels from getting cut off.
    rcParams.update({'figure.autolayout': False}) 

    # import warnings
    # warnings.filterwarnings("ignore") 
    # # This was to hide nanmin warnings, maybe not so good to have in general.


    if (DisableInits.disable_nl_imports is False):
        import_packages()



