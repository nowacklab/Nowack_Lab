import numpy as np
import matplotlib.pyplot as plt
import time
from Nowack_Lab.Utilities.datasaver import Saver

class AustinSquidTuning:
    
    def __init__(self,daq,s,preamp,DAQSpec):
        self.daq = daq
        self.s = s
        self.preamp = preamp
        self.DAQSpec = DAQSpec
        savedataname = input('Give file name to squid noise tuning measurement: ')
        self.savedata = Saver(savedataname)
        
    def take_noise_spectra(self,plot = True,fileheader = ''):
        self.DAQSpec.findnoiselevel()
        if plot == True:
            self.DAQSpec.simpleplot()
        
        spectrum_label = time.strftime('%H:%M:%S') + 'Aflux' + str(np.round(self.s.__getstate__()['Array flux'],2)) + '_Sflux' + str(np.round(self.s.__getstate__()['SQUID bias'],0))
        self.savedata.append(fileheader+'/noise_measurement_%s/spectra' %spectrum_label,np.transpose(np.array([self.DAQSpec.f,self.DAQSpec.psdAve*self.DAQSpec.conversion])))
        self.savedata.append(fileheader+'/noise_measurement_%s/mean' %spectrum_label,self.DAQSpec.psd_mean)
        self.savedata.append(fileheader+'/noise_measurement_%s/conversion_Vphi0' %spectrum_label,1/self.DAQSpec.conversion)
        self.savedata.append(fileheader+'/noise_measurement_%s/units' %spectrum_label,self.DAQSpec.units)
        self.savedata.append(fileheader+'/noise_measurement_%s/squidparams/' %spectrum_label,self.s.__getstate__())
        self.savedata.append(fileheader+'/noise_measurement_%s/daqparams/' %spectrum_label,self.daq.__getstate__())
        self.savedata.append(fileheader+'/noise_measurement_%s/preampparams/' %spectrum_label,self.preamp.__getstate__())

        
    def tune_A_bias(self,A_bias_vals):
        print('tuning A_bias')
        signal_amplitude = 0
        signal_amplitude_limit = 1
        for A_bias in np.arange(A_bias_vals[0],A_bias_vals[1],A_bias_vals[2]):
            self.s.A_bias = A_bias
            time.sleep(.25)
            new_sig = self.daq.monitor(['raw'], 1, sample_rate=15000)['raw']
            new_sig_sorted = sorted(new_sig)
            peak_to_peak = np.mean(new_sig_sorted[-100:-1])-np.mean(new_sig_sorted[0:100])
            if peak_to_peak > signal_amplitude and peak_to_peak > signal_amplitude_limit:
                signal_amplitude = peak_to_peak
                A_bias_max_amplitude = A_bias
            elif peak_to_peak < signal_amplitude and peak_to_peak > signal_amplitude_limit:
                self.s.A_bias = A_bias_max_amplitude
                time.sleep(.25)
                print('A_bias tuned at ',A_bias_max_amplitude,' uA')
                return(A_bias_max_amplitude)
            elif A_bias >= (A_bias_vals[1]-A_bias_vals[2]):
                print('Could not find A_bias point with maximized signal amplitude')
                break

            
    def tune_offset(self,offset_vals):
        print('tuning offset')
        center_offset = 100
        for offset in np.arange(offset_vals[0],offset_vals[1],offset_vals[2]):
            self.s.offset = offset
            time.sleep(.25)
            new_sig = self.daq.monitor(['raw'], 1, sample_rate=15000)['raw']
            new_sig_sorted = sorted(new_sig)
            peak_deviation_from_zero = abs(np.mean(new_sig_sorted[-100:-1])+np.mean(new_sig_sorted[0:100]))
            if peak_deviation_from_zero < center_offset:
                center_offset = peak_deviation_from_zero
                offset_centered_signal = offset
            elif peak_deviation_from_zero > center_offset:
                self.s.offset = 0
                time.sleep(.25)
                self.s.offset = offset_centered_signal
                time.sleep(.25)
                print('offset tuned at ',offset_centered_signal,' uA')
                return(offset_centered_signal)
            elif offset >= (offset_vals[1]-offset_vals[2]):
                print('Could not find offset which centered the signal about zero')
                break
        
        
    def tune_S_bias(self,S_bias_vals):
        print('tuning S_bias')
        signal_amplitude = 0
        signal_amplitude_limit = .05
        for S_bias in np.arange(S_bias_vals[0],S_bias_vals[1],S_bias_vals[2]):
            self.s.S_bias = S_bias
            time.sleep(.25)
            new_sig = self.daq.monitor(['raw'], 1, sample_rate=15000)['raw']
            new_sig_sorted = sorted(new_sig)
            peak_to_peak = np.mean(new_sig_sorted[-100:-1])-np.mean(new_sig_sorted[0:100])
            if peak_to_peak > signal_amplitude and peak_to_peak > signal_amplitude_limit:
                signal_amplitude = peak_to_peak
                S_bias_max_amplitude = S_bias
            elif peak_to_peak < signal_amplitude and peak_to_peak > signal_amplitude_limit:
                self.s.S_bias = S_bias_max_amplitude
                time.sleep(.25)
                print('S_bias tuned at ',S_bias_max_amplitude,' uA')
                return(S_bias_max_amplitude)
            elif S_bias >= (S_bias_vals[1]-S_bias_vals[2]):
                print('Could not find S_bias point with maximized signal amplitude > ',signal_amplitude_limit,' V')
                break
                

    def tune_A_flux(self,A_flux_vals):
        print('tuning A_flux')
        decrease = False
        i = 1
        for A_flux in np.arange(A_flux_vals[0],A_flux_vals[1],A_flux_vals[2]):
            self.s.A_flux = A_flux
            self.s.reset()
            time.sleep(.25)
            new_sig = self.daq.monitor(['raw'], 1, sample_rate=15000)['raw']
            new_sig_sorted = sorted(new_sig)
            peak_deviation_from_zero = abs(np.mean(new_sig_sorted[-100:-1])+np.mean(new_sig_sorted[0:100]))
            if i == 1:
                center_offset = peak_deviation_from_zero
                i += 1
            if decrease == False:
                if peak_deviation_from_zero < center_offset :
                    center_offset = peak_deviation_from_zero
                    A_flux_centered_signal = A_flux
                    decrease = True
                else:
                    center_offset = peak_deviation_from_zero
            
            if decrease == True:
                if peak_deviation_from_zero < center_offset:
                    center_offset = peak_deviation_from_zero
                    A_flux_centered_signal = A_flux
                if peak_deviation_from_zero > center_offset:
                    self.s.A_flux = 0
                    self.s.reset()
                    time.sleep(.25)
                    self.s.A_flux = A_flux_centered_signal
                    self.s.reset()
                    time.sleep(.25)
                    print('A_flux tuned at ',A_flux_centered_signal,' uA')
                    return(A_flux_centered_signal)
            if A_flux >= (A_flux_vals[1]-A_flux_vals[2]):
                print('Could not find A_flux which centered the signal about zero')
                break
                
              
    def tune_S_flux(self,S_flux_vals):
        print('tuning S_flux')
        decrease = False
        i = 1
        for S_flux in np.arange(S_flux_vals[0],S_flux_vals[1],S_flux_vals[2]):
            self.s.S_flux = S_flux
            self.s.reset()
            time.sleep(.25)
            new_sig = self.daq.monitor(['raw'], 1, sample_rate=15000)['raw']
            new_sig_sorted = sorted(new_sig)
            peak_deviation_from_zero = abs(np.mean(new_sig_sorted[-100:-1])+np.mean(new_sig_sorted[0:100]))
            if i == 1:
                center_offset = peak_deviation_from_zero
                i += 1
            if decrease == False:
                if peak_deviation_from_zero < center_offset :
                    center_offset = peak_deviation_from_zero
                    S_flux_centered_signal = S_flux
                    decrease = True
                else:
                    center_offset = peak_deviation_from_zero
            
            if decrease == True:
                if peak_deviation_from_zero < center_offset:
                    center_offset = peak_deviation_from_zero
                    S_flux_centered_signal = S_flux
                if peak_deviation_from_zero > center_offset:
                    self.s.S_flux = 0
                    self.s.reset()
                    time.sleep(.25)
                    self.s.S_flux = S_flux_centered_signal
                    self.s.reset()
                    time.sleep(.25)
                    print('S_flux tuned at ',S_flux_centered_signal,' uA')
                    return(S_flux_centered_signal)
            if S_flux >= (S_flux_vals[1]-S_flux_vals[2]):
                print('Could not find S_flux which centered the signal about zero')
                break
                
                
    def tune_by_huristics(self,find_conversion = False,check_hysteretics = False):
        self.s.zero()
        
        self.s.testSignal = 'On'
        self.s.testInput =  'A_flux'
        
        A_bias_coarse_tune = self.tune_A_bias([10,50,2])
        A_bias_fine_fine_tune = self.tune_A_bias([A_bias_coarse_tune-2,A_bias_coarse_tune+2,.25])
        
        offset_coarse_tune = self.tune_offset([0,5,.1])
        offset_fine_tune = self.tune_offset([offset_coarse_tune-.1,offset_coarse_tune+.1,.01])
        
        self.s.lock('Array')
        
        self.s.testInput = 'S_flux'
        self.s.testSignal = 'On'
        
        if check_hysteretics == True:
            self.check_hysteretic()
        
        S_bias_coarse_tune = self.tune_S_bias([0,2000,25])
        S_bias_fine_tune = self.tune_S_bias([S_bias_coarse_tune-25,S_bias_coarse_tune+25,2])
        
        A_flux_coarse_tune = self.tune_A_flux([0,25,2])
        A_flux_fine_fine_tune = self.tune_A_flux([A_flux_coarse_tune-2,A_flux_coarse_tune+2,.1])
        
        self.s.lock('squid')
        
        self.s.testSignal = 'Off'
        
        if find_conversion == True:
            print('sweeping S_flux to find conversion factor')
            s_flux_jump = self.find_conversion_factor(S_flux_vals = [0,40,2], coarse = True, plot = False)
            conversion_factor = self.find_conversion_factor(S_flux_vals = [s_flux_jump-3,s_flux_jump+1,.2], coarse = False, plot = True)
        
        S_flux_coarse_tune = self.tune_S_flux([0,50,2])
        S_flux_fine_fine_tune = self.tune_S_flux([S_flux_coarse_tune-2,S_flux_coarse_tune+2,.25])
        
        self.savedata.append('/huristic_squid_params/',self.s.__getstate__())
       
        
    def find_conversion_factor(self,S_flux_vals = [0,40,2], coarse = False, plot = True):
        self.s.sensitivity = 'Med'
        s_fluxes = []
        saa_voltage = []
        saa_voltage_diff = []
        i = 0
        for s_flux in np.arange(S_flux_vals[0],S_flux_vals[1],S_flux_vals[2]):
            self.s.S_flux = s_flux
            self.s.reset()
            time.sleep(.25)
            s_fluxes.append(s_flux)
            saa_voltage.append(np.mean(self.daq.monitor(['raw'], 1, sample_rate=15000)['raw']))
            if i > 0:
                saa_voltage_diff.append(np.abs(saa_voltage[i]-saa_voltage[i-1]))
                if saa_voltage_diff[i-1] > 1.4:
                    s_flux_jump = s_flux
                    if coarse == True:
                        self.s.sensitivity = 'High'
                        return(s_flux_jump)
            i += 1

        if plot == True:
            plt.figure()
            plt.plot(s_fluxes,saa_voltage)
            plt.xlabel('S_flux')
            plt.ylabel('Voltage')
            plt.show()

        conversion_factor = max(saa_voltage_diff)*10
        print('Conversion Factor = ',conversion_factor,' V/Phi_0')
        
        self.savedata.append('/conversion/conversion_factor',conversion_factor)
        self.savedata.append('/conversion/s_flux_sweep',np.transpose(np.array([s_fluxes,saa_voltage])))
        self.savedata.append('/conversion/squidparams/',self.s.__getstate__())
        self.savedata.append('/conversion/preampparams/',self.preamp.__getstate__())
        self.DAQSpec.conversion = 1/conversion_factor
        self.DAQSpec.units = 'Phi_0'
        self.s.sensitivity = 'High'
        return(conversion_factor)
    
    def check_hysteretic(self):
        print('sweeping S_bias, checking for hysteresis')
        self.s.testSignal = 'Off'
        s_biases = np.arange(0,1500,50)
        s_bias_up = []
        voltage_up = []
        s_bias_down = []
        voltage_down = []
        for s_bias in s_biases:
            self.s.S_bias = s_bias
            s_bias_up.append(s_bias)
            voltage_up.append(np.mean(self.daq.monitor(['raw'], 1, sample_rate=15000)['raw']))
        for s_bias in reversed(s_biases):
            self.s.S_bias = s_bias
            s_bias_down.append(s_bias)
            voltage_down.append(np.mean(self.daq.monitor(['raw'], 1, sample_rate=15000)['raw']))
            
        plt.figure()
        plt.plot(s_bias_up,voltage_up,label='sweeping up')
        plt.plot(s_bias_down,voltage_down,label='sweeping down')
        plt.title('Hysteretics')
        plt.xlabel('S_bias')
        plt.ylabel('Voltage (V)')
        plt.legend()
        plt.show()
        
        self.savedata.append('/hysteretics/s_bias_sweep_up',np.transpose(np.array([s_bias_up,voltage_up])))
        self.savedata.append('/hysteretics/s_bias_sweep_down',np.transpose(np.array([s_bias_down,voltage_down])))
        self.savedata.append('/hysteretics/squidparams/',self.s.__getstate__())
        self.savedata.append('/hysteretics/daqparams/',self.daq.__getstate__())
        self.s.testSignal = 'On'
    
    def lock_squid_at_lock_point(self,A_bias,offset,S_bias,A_flux,S_flux):
        self.s.zero()
        self.s.testInput =  'A_flux'
        self.s.testSignal = 'On'
        time.sleep(.5)
        if A_bias != 'nan':
            self.s.A_bias = A_bias
        time.sleep(.5)
        if offset != 'nan':
            self.s.offset = offset
            time.sleep(.5)
            self.s.lock('Array')
        time.sleep(.5)
        self.s.testInput = 'S_flux'
        self.s.testSignal = 'On'
        time.sleep(.5)
        if S_bias !='nan':
            self.S_bias = S_bias
        time.sleep(.5)
        if A_flux != 'nan':
            self.A_flux = A_flux
            time.sleep(.5)
            self.s.lock('squid')
        time.sleep(.5)
        self.s.testSignal = 'Off'
        if S_flux != 'nan':
            self.s.S_flux = S_flux



