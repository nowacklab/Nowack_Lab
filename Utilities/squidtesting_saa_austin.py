# import standard libraries
import matplotlib
%matplotlib notebook
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import numpy as np
import time

# imports the DAQ, preamp, and starcryo electronics scripts
import Nowack_Lab.Instruments.nidaq
import Nowack_Lab.Instruments.squidarray
import Nowack_Lab.Instruments.preamp

# import the main instrument class from the DAQ, preamp, and starcryo electronics script
from Nowack_Lab.Instruments.nidaq       import NIDAQ
from Nowack_Lab.Instruments.squidarray  import SquidArray
from Nowack_Lab.Instruments.preamp      import SR5113

from Nowack_Lab.Utilities.relay       import Relay
from Nowack_Lab.Utilities.datasaver import Saver
#import Nowack_Lab.Procedures.mutual_inductance

#from Nowack_Lab.Procedures.mutual_inductance    import MutualInductance2
#from Nowack_Lab.Procedures.mutual_inductance    import MutualInductance_sweep
from  Nowack_Lab.Procedures.austindaqspectrum import DaqSpectrum

from Nowack_Lab import set_experiment_data_path
set_experiment_data_path()

s = SquidArray()
preamp = SR5113(port='COM5')
daq = NIDAQ()
r = Relay(daq)

daq.outputs = {}
daq.inputs = {
        'raw':3,
        'dc':4,
        'saa':5
}


instruments = {
        'daq':daq,
        'squidarray':s,
        'preamp':preamp
}

DAQSpec = DaqSpectrum({'daq':daq,'preamp':preamp,'squidarray':s})
