import Nowack_Lab.Procedures, Nowack_Lab.Instruments, Nowack_Lab.Utilities

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True}) # will avoid axis labels getting cut off

# import warnings
# warnings.filterwarnings("ignore") # This was to hide nanmin warnings, maybe not so good to have in general.


## Importing commonly used packages
from IPython import get_ipython, display
ip = get_ipython()
ip.kernel.do_execute('''
import numpy as np
import matplotlib.pyplot as plt
from imp import reload
from time import sleep
import sys, os

## For interactive matplotlib plots
from IPython import get_ipython
get_ipython().magic('matplotlib notebook')

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
from Nowack_Lab.Procedures.squidIV import SquidIV
from Nowack_Lab.Procedures.touchdown import Touchdown
from Nowack_Lab.Instruments.attocube import Attocube
from Nowack_Lab.Instruments.keithley import Keithley2400
from Nowack_Lab.Instruments.montana import Montana
from Nowack_Lab.Instruments.nidaq import NIDAQ
from Nowack_Lab.Instruments.piezos import Piezos
from Nowack_Lab.Instruments.preamp import SR5113
from Nowack_Lab.Instruments.squidarray import SquidArray
from Nowack_Lab.Instruments.lockin import SR830

''', silent=True)
