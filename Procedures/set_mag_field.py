import time
import numpy as np
from Nowack_Lab.Instruments import KEPCO
from Nowack_Lab.Instruments import keysight

alpha = 833.824*1e-6
beta = 689.544*1e-6
delta = 3.464*1e-6


kepco = KEPCO.kepcoBOP()
kepco.source = 'I'
kepco.Iout = 0
kepco.Vout = 70
kepco.output = 'on'
magnetps = keysight.Keysight34461A(gpib_address='USB0::0x2A8D::0x1401::MY60046284::INSTR')
magnetps.Irange = 1
folder = r'F:\data\Hemlock\experiments\logging'
currentfilename = folder + '\\' + 'current' + '.txt'

#This function calculates the current out for a target field value B (uT)
#based on the current flux gate sensor field b (uT) value and current output i (A)
def targetI(B, b, i):
    return (B-b+beta*i-delta)/alpha
#This function measures the flux gate sensor signal. It returns the preamp gain,
#signal received on daq (V), and the calculated field value (uT)
def fieldnow():
    updatefilename = folder + '\\' + 'fieldupdate' + '.txt'
    while True:
        with open(updatefilename) as f:
            a = f.readline()
        try:
            float(a.split(',')[0])
            break
        except:
            pass
    return(float(a.split(',')[0]))
#This function calculates the current field at sample based on sensor reading and coil magnet current
def currentB(b, i):
    return b+(alpha-beta)*i+delta
#This function measures the current field at sample based on sensor reading and coil magnet current
def measurecurrentB():
    b = fieldnow()
    i = magnetps.I
    return currentB(b, i)
#This function changes the current to reach a targed field on sample in unit of uT
def switchfield(target):
    i = magnetps.I
    b = fieldnow()
    I = targetI(target, b, i)
    n = 0
    while abs(magnetps.I-I)>3e-5 and n<50:
        currentiout = kepco.Iout
        currenti = magnetps.I
        Iout = -currenti+I+currentiout
        if abs(Iout)<0.5:
            kepco.Iout = Iout
        else:
            kepco.Iout = 0.5*np.copysign(1, Iout)
        time.sleep(0.2)
        n = n+1
#This function keeps reading the target field value from file and check if the current field is at the target field. If not, change the field to target.
def checkfield():
    targetfilename = folder + '\\' + 'target' + '.txt'
    with open(targetfilename) as f:
        targetfield = float(f.readline())
    currentfield = measurecurrentB()
    if abs(targetfield-currentfield)>0.025*1e-6:
        time.sleep(4)
        currentfield = measurecurrentB()
        with open(targetfilename) as f:
            targetfield = float(f.readline())
        if abs(targetfield-currentfield)>0.025*1e-6:
            switchfield(targetfield)
    writestring = str(magnetps.I)
    file = open(currentfilename,'w')
    file.write(writestring)
    file.close()
while True:
    checkfield()
    time.sleep(1)
