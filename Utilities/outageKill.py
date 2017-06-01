import os

import numpy as np

pid = os.getpid();

os.system('taskkill /f /fi "PID ne %i" /im python.exe' %pid)


import Nowack_Lab

daq = NIDAQ();
vstart = {'ao0':daq.ao0.V,'ao1':daq.ao1.V,'ao2':daq.ao2.V,'ao3':daq.ao3.V}
vend ={'ao0':0,'ao1':0,'ao2':0,'ao3':0}
daq.sweep(vstart,vend)
atto = Attocube()
atto.z.step(-1000)