import datetime
import time
import numpy as np
import h5py
from scipy.interpolate import interp1d
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import matplotlib.dates as datefmt
import serial


fitfile = 'F:\\data\\Hemlock\\experiments\\2024-06-19_Arduino_fluxgate_readout_calibration\\2024-06-20_124011_coilcurrent_vs_fluxgatesensor.hdf5'

fss = []
fss1 = []
fss2 = []
fss3 = []
fss4 = []
fss5 = []
fss6 = []
fb = []
fg = []
fitdata = []
fit = []
def line(x, m, b):
    return(np.array(x)*m+b)
with h5py.File(fitfile, "r") as f:
    fss1 = np.array(f['forward']['sensor field 1(uT)'])
    fss2 = np.array(f['forward']['sensor field 1(uT)'])
    fss3 = np.array(f['forward']['sensor field 1(uT)'])
    fss4 = np.array(f['forward']['sensor field 1(uT)'])
    fss5 = np.array(f['forward']['sensor field 1(uT)'])
    fss6 = np.array(f['forward']['sensor field 1(uT)'])
    fss.append((fss1+fss2+fss3+fss4+fss5+fss6)/6)
    fb.append(list(f['forward']['magnetcurrent (A)']))
    fit.append(curve_fit(line, fb[-1][1:-2], fss[-1][1:-2]))
    fitdata.append(fit[-1][0][1]+fit[-1][0][0]*np.array(fb[-1]))
    fss1 = np.array(f['reverse']['sensor field 1(uT)'])
    fss2 = np.array(f['reverse']['sensor field 1(uT)'])
    fss3 = np.array(f['reverse']['sensor field 1(uT)'])
    fss4 = np.array(f['reverse']['sensor field 1(uT)'])
    fss5 = np.array(f['reverse']['sensor field 1(uT)'])
    fss6 = np.array(f['reverse']['sensor field 1(uT)'])
    fss.append((fss1+fss2+fss3+fss4+fss5+fss6)/6)
    fb.append(list(f['reverse']['magnetcurrent (A)']))
    fit.append(curve_fit(line, fb[-1][1:-2], fss[-1][1:-2]))
    fitdata.append(fit[-1][0][1]+fit[-1][0][0]*np.array(fb[-1]))
field = (fss[0]+np.flip(fss[1]))/2
difference = (fss[0]-fitdata[0]+np.flip(fss[1]-fitdata[1]))/2
a = {'field': field, 'difference': difference}
correction = interp1d(a['field'], a['difference'])
def correctB(b):
    return b-correction(b)


folder = r'F:\data\Hemlock\experiments\logging'
ser = serial.Serial('COM7',9600)

datestring = None
starttime = time.time()
updatefilename = folder + '\\' + 'fieldupdate' + '.txt'
targetfilename = folder + '\\' + 'target' + '.txt'
while True:
    #check date
    try:
        if datestring != str(datetime.date.today()):
            datestring = str(datetime.date.today())
            loggingfilename = folder + '\\' + datestring + '.txt'
        Vout = []
        Bfield = []
        writestring = ''
        while float(ser.readline().strip().decode('utf-8')) != 1:
            pass
        for i in range(2):
            Vout.append(float(ser.readline().strip().decode('utf-8'))/2**24 * 4096/2000)
            B = Vout[i]/(4*12.2*100)
            if B<100e-6 and B>-100e-6:
                B = correctB(B)
            Bfield.append(B)
            writestring = writestring+str(Bfield[i])+','
        file = open(updatefilename,'w')
        file.write(writestring[0:-1])
        file.close()
        if time.time()-starttime>9.5:
            starttime = starttime+10
            with open(targetfilename) as f:
                targetfield = float(f.readline())
            writestring = str(datetime.datetime.now().time())[0:8] + ',' + writestring + str(targetfield) + ' \n'
            file = open(loggingfilename,'a')
            file.write(writestring)
            file.close()
    except ValueError:
        print('Error Recording Data')
    except KeyboardInterrupt:
        file.close()
        print('Fluxgate sensor monitoring has ended')
        break
