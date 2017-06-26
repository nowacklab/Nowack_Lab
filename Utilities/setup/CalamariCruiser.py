"""
Template setup file for handling imports.
Modify for each computer as you see appropriate.
Any commands run here run directly in the IPython Kernel.
"""

import os

from IPython import get_ipython
ip = get_ipython()

here = os.path.dirname(__file__)
path = os.path.join(here, 'common_imports.py')

ip.magic('run %s' %path)

# Uncomment desired import commands below
# from Nowack_Lab.Utilities import utilities, save, logging, conversions, anim, constants
# from Nowack_Lab.Utilities.plotting import plot_mpl
# from Nowack_Lab.Utilities.save import Measurement
# from Nowack_Lab.Procedures.daqspectrum import DaqSpectrum, SQUIDSpectrum
# from Nowack_Lab.Procedures.heightsweep import Heightsweep
# from Nowack_Lab.Procedures.mod2D import Mod2D
# from Nowack_Lab.Procedures.mutual_inductance import MutualInductance
# from Nowack_Lab.Procedures.navigation import move
# from Nowack_Lab.Procedures.planefit import Planefit
# from Nowack_Lab.Procedures.scanline import Scanline
# from Nowack_Lab.Procedures.scanplane import Scanplane
# from Nowack_Lab.Procedures.scanspectra import Scanspectra
# from Nowack_Lab.Procedures.squidIV import SquidIV
# from Nowack_Lab.Procedures.touchdown import Touchdown
# from Nowack_Lab.Procedures.transport import RvsVg, RvsTime, RvsT
# from Nowack_Lab.Procedures.magnetotransport import RvsB, RvsVg_B
# from Nowack_Lab.Instruments.attocube import Attocube
# from Nowack_Lab.Instruments.keithley import Keithley2400, Keithley2600, KeithleyPPMS
# from Nowack_Lab.Instruments.montana import Montana
# from Nowack_Lab.Instruments.nidaq import NIDAQ
# from Nowack_Lab.Instruments.piezos import Piezos
# from Nowack_Lab.Instruments.preamp import SR5113
# from Nowack_Lab.Instruments.squidarray import SquidArray
# from Nowack_Lab.Instruments.lockin import SR830
# from Nowack_Lab.Instruments.ppms import PPMS
# from Nowack_Lab.Fun.callme import call
