import os
# Workaround for scipy altering KeyboardInterrupt behavior
os.environ['FOR_DISABLE_CONSOLE_CTRL_HANDLER'] = '1'

from IPython import get_ipython, display
ip = get_ipython()

from .Utilities import save

# Set experiment data path
try:
    print('Current experiment: %s' %save.get_experiment_data_dir())
except:
    pass

print('Use save.set_experiment_data_dir to change experiments\n')

# Check for remote data server connection
if not os.path.exists(save.get_data_server_path()):
    print('''\nSAMBASHARE not connected. Could not find path %s.''' %save.get_data_server_path())

# Importing commonly used packages
setup_path = os.path.join(os.path.dirname(__file__),
                            'Utilities',
                            'setup',
                            save.get_computer_name() + '.py'
                        )
if not os.path.exists(setup_path):
    print('Setup file %s created.' %setup_path)
    with open(setup_path, 'a') as f:
        f.write(r'''"""
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
''')

ip.magic('run %s' %setup_path)
