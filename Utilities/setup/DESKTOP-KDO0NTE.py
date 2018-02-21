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
from Nowack_Lab.Utilities.save import Measurement
from Nowack_Lab.Utilities.say import say
from Nowack_Lab.Procedures.daqspectrum import DaqSpectrum, SQUIDSpectrum
from Nowack_Lab.Procedures.dctransport import DAQ_IV
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
from Nowack_Lab.Procedures.transport import RvsVg, RvsTime, RvsT, RvsVg_Vtg, RvsT_RT_to_4K, RvsVg_T
from Nowack_Lab.Procedures.magnetotransport import RvsB, RvsVg_B, RvsB_BlueFors, RvsVg_B_BlueFors
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
