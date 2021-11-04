import h5py    
import numpy as np
import matplotlib.pyplot as plt
import time
#from Nowack_Lab.Utilities import datasaver

class SquidNoiseSearchPlotting():
    
    def spectrumplottter(self,units,conversion,freq,psdAve,psd_mean):
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
        
        
    def plotnoisepectra(self,sweepname):
        meas_num = 1
        filename = str(input('hdf5 filename: '))
        
        
        alreadyplotted = ['1']
        
        while True:
            f = h5py.File(filename, "r")
            conversion = f[sweepname]['conversion_factor'][()]
            units = f[sweepname]['units'][()]
            filenamelist = list(f[sweepname])

            i = 0
            while i < len(filenamelist):
                file = filenamelist[i]
                if file != 'measurement_done' and file!= 'conversion_factor' and file != 'units':
                    for ap in alreadyplotted:
                        if file != ap:
                            #try:
                                spectrum = f[sweepname][file]['spectra'][()]
                                psd_mean = f[sweepname][file]['mean'][()]
                                S_bias = f[sweepname][file]['squidparams']['SQUID bias'][()]
                                A_flux = f[sweepname][file]['squidparams']['Array flux'][()]
                                psdAve = spectrum[:,1]
                                freq = spectrum[:,0]
                                label_string = 'Aflux: '+str(A_flux)+';S_bias: '+str(S_bias)
                                plt.figure(1,figsize=(6,6))
                                plt.semilogy(freq, psdAve*conversion,label = label_string)
                                #ax.semilogy(freq, psd_mean*np.ones(len(freq))*conversion)
                                plt.xlabel('Frequency (Hz)')
                                plt.ylabel(r'Power Spectral Density ($\mathrm{%s/\sqrt{Hz}}$)' %units)
                                plt.xlim(0,1e3)
                                plt.legend()
                                #plt.show()
                                alreadyplotted.append(file)
                            #except:
                                time.sleep(1)

                i+=1
            plt.show()
            try:
                measurement_done = f[sweepname]['measurement_done'][()]
                if measurement_done == 'done':
                    print('done')
                    f.close()
                    break
            except:
                f.close()
                time.sleep(1)
                
        
        
        
        
        