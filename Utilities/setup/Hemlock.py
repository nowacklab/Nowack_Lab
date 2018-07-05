r"""
Template setup file for handling imports.
Modify for each computer as you see appropriate.
Run using get_ipython().magic('run %s' %setup_path)
to import directly into the IPython Kernel.
"""

import os

from IPython import get_ipython
ip = get_ipython()

here = os.path.dirname(__file__)
path = os.path.join(here, 'common_imports.py')

ip.magic('run %s' %path)

# Comment out undesired import commands below
from Nowack_Lab.Utilities import utilities, save, logging, conversions, anim, constants
from Nowack_Lab.Utilities.plotting import plot_mpl
from Nowack_Lab.Utilities.say import say
from Nowack_Lab.Utilities.save import Saver
from Nowack_Lab.Measurements.daqspectrum import DaqSpectrum, SQUIDSpectrum
from Nowack_Lab.Measurements.dctransport import DAQ_IV, RvsT_Montana_Keithley
from Nowack_Lab.Measurements.heightsweep import Heightsweep
from Nowack_Lab.Measurements.measurement import Measurement
from Nowack_Lab.Measurements.mod2D import Mod2D
from Nowack_Lab.Measurements.mutual_inductance import MutualInductance
from Nowack_Lab.Measurements.navigation import move
from Nowack_Lab.Measurements.planefit import Planefit
from Nowack_Lab.Measurements.scanline import Scanline
from Nowack_Lab.Measurements.scanplane import Scanplane
from Nowack_Lab.Measurements.scanspectra import Scanspectra
from Nowack_Lab.Measurements.squidIV import SquidIV
from Nowack_Lab.Measurements.touchdown import Touchdown
from Nowack_Lab.Measurements.transport import RvsVg, RvsTime, RvsT, RvsVg_Vtg, RvsT_RT_to_4K, RvsVg_T, RvsT_Montana
from Nowack_Lab.Measurements.magnetotransport import RvsB, RvsVg_B, RvsB_BlueFors, RvsVg_B_BlueFors
from Nowack_Lab.Instruments.attocube import Attocube
from Nowack_Lab.Instruments.keithley import Keithley2400, Keithley2450, Keithley2600, KeithleyPPMS
from Nowack_Lab.Instruments.lakeshore import Lakeshore372
from Nowack_Lab.Instruments.montana import Montana
from Nowack_Lab.Instruments.nidaq import NIDAQ
from Nowack_Lab.Instruments.piezos import Piezos
from Nowack_Lab.Instruments.preamp import SR5113
from Nowack_Lab.Instruments.squidarray import SquidArray
from Nowack_Lab.Instruments.lockin import SR830
from Nowack_Lab.Instruments.ppms import PPMS
from Nowack_Lab.Instruments.magnet import Magnet, AMI420
from Nowack_Lab.Instruments.zurich import HF2LI
