import h5py    
import numpy as np
import matplotlib.pyplot as plt
import time
#from Nowack_Lab.Utilities import datasaver

def spectrumplottter(units,conversion,freq,psdAve,psd_mean):
    fig = plt.figure(figsize=(12, 6))
    axloglog = fig.add_subplot(121)
    axloglog.set_xlabel('Frequency (Hz)')
    axloglog.set_ylabel(r'Power Spectral Density ($\mathrm{%s/\sqrt{Hz}}$)' %units)
    axloglog.loglog(freq, psdAve*conversion)
    #ax['loglog'].annotate(params, xy=(0.02,.45), xycoords='axes fraction',fontsize=8, ha='left', va='top',family='monospace')

    axsemilog = fig.add_subplot(122)
    axsemilog.set_xlabel('Frequency (Hz)')
    axsemilog.set_ylabel(r'Power Spectral Density ($\mathrm{%s/\sqrt{Hz}}$)' %units)
    axsemilog.semilogy(freq, psdAve*conversion)
    axsemilog.semilogy(freq, psd_mean*np.ones(len(freq))*conversion)
    axsemilog.set_xlim([freq[0],1e3])
    axsemilog.annotate('500Hz-1kHz mean = '+f'{psd_mean:.3e}'+'($\mathrm{%s/\sqrt{Hz}}$)' %units, xy=(0.05,.95), xycoords='axes fraction',fontsize=12, ha='left', va='top', family='monospace')
    plt.show()


meas_num = 1
print('running')
filename = 'C:\\data\\experiments\\2021-10-05_10-5-2021_low_noise_search\\2021-10-07_172930_tuning_lockpoint.hdf5'#str(input('hdf5 filename: '))
while True:
    f = h5py.File(filename, "r")
    conversion = f['config']['conversion_factor'][()]
    units = f['config']['units'][()]
    try:
        spectrum = f['noise_measurement%s' %meas_num]['spectra'][()]
        psd_mean = f['noise_measurement%s' %meas_num]['mean'][()]
        psdAve = spectrum[:,1]
        freq = spectrum[:,0]
        self.spectrumplottter(units,conversion,freq,psdAve,psd_mean)
        meas_num += 1
    except:
        time.sleep(1)
        f.close()
    try:
        measurement_done = f['measurement_done'][()]
        if measurement_done == 'done' and meas_num == len(list(f))-1:
            print('done')
            break
    except:
        time.sleep(1)
        f.close()
        
        
        
        
        