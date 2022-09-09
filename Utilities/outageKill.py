'''Doc String:

This code kills all other kernels to gain control of the daq and 
attocubes then zeros the daq over one second and backs off the 
attocubes by 1000 steps.

Author: Alex Jarjour
Warning: this code will kill ALL OTHER PYTHON THREADS.
'''

import os
import sys
sys.path.append('C:/Users/Hemlock/Documents/GitHub') 
sys.path.append('C:/Users/Hemlock/Documents/GitHub/Instrumental') 
import numpy as np
from Nowack_Lab.Instruments.squidarray import SquidArray
from Nowack_Lab.Instruments.attocube import Attocube
from Nowack_Lab.Instruments.nidaq import NIDAQ

# Gets program id of this python kernel.
pid = os.getpid()

os.system('taskkill /f /fi "PID ne %i" /im python.exe' %pid) 



daq = NIDAQ()
vstart = {'ao0':daq.ao0.V,'ao1':daq.ao1.V,'ao2':daq.ao2.V,'ao3':daq.ao3.V} 
#starts sweep at current voltages
vend ={'ao0':0,'ao1':0,'ao2':0,'ao3':0}
#ends at zero
daq.sweep(vstart,vend)
#executes sweep

# Zero the SAA electronics
s = SquidArray()
s.zero()

# Steps the attos down to 500.

atto = Attocube()
atto.z.pos = 500