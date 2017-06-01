'''Doc String:

This code kills all other kernels to gain control of the daq and 
attocubes then zeros the daq over one second and backs off the 
attocubes by 1000 steps.

Author: Alex Jarjour
Warning: this code will kill ALL OTHER PYTHON THREADS.

'''



import os

import numpy as np

pid = os.getpid(); # Gets program id of this python kernel.

os.system('taskkill /f /fi "PID ne %i" /im python.exe' %pid) 
#kills all running python kernels other than this one

import Nowack_Lab

daq = NIDAQ();
vstart = {'ao0':daq.ao0.V,'ao1':daq.ao1.V,'ao2':daq.ao2.V,'ao3':daq.ao3.V} 
#starts sweep at current voltages
vend ={'ao0':0,'ao1':0,'ao2':0,'ao3':0}
#ends at zero
daq.sweep(vstart,vend)
#executes sweep
atto = Attocube()
atto.z.step(-1000)
#steps the attos down by 1000 steps.