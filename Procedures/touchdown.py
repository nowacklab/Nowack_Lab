from IPython import display
from scipy.stats import linregress as line
import time
import matplotlib.pyplot as plt
import numpy as np
from msvcrt import getch


class Touchdown():
    def __init__(self, z_piezo, atto, lockin, daq, low_temp = False):    
        self.touchdown = False
        self.V_to_C = 2530e3 # 2530 pF/V * (1e3 fF/pF), calibrated 20160423 by BTS, see ipython notebook
        self.attosteps = 200 #number of attocube steps between sweeps

        self.z_piezo = z_piezo
        self.atto = atto
        self.lockin = lockin
        self.daq = daq
                
        isLowTemp = input('Testing at low temperature? [y/(n)]')
        if isLowTemp in ('y', 'Y'):
            self.low_temp = True
        else:
            self.low_temp = False
        
        self.configure_attocube()
        self.configure_lockin()
        self.configure_piezo()
        
        self.Vpiezo_full = []
        self.cap_full = []
        self.rsquared = []

        self.fig = plt.figure()
        self.ax = plt.gca()
        
    def do(self):
        td_count = 0
        tot_attosteps = 0
        attosteps = self.attosteps
        
        while not self.touchdown:
            #Check for exit
            key = ord(getch())
            if key == 27: #ESC
                break
        
            plt.clf()
            plt.title('Touchdown #%i, attocube has moved %i steps.' %(td_count, tot_attosteps))
            self.check_balance()
            
            td_count = td_count + 1
            tot_attosteps = tot_attosteps + attosteps
            
            #atto.up([attosteps, None, None])
            self.Vpiezo_full = []
            self.cap_full = []
            self.rsquared = []
            num_avg = 10

            numsteps = int(self.z_piezo.Vmax/self.z_piezo_step/num_avg) # sweep in groups of num_avg points
            for i in range(numsteps): 
                piezo_sweep_voltage, cap_voltage, t = self.z_piezo.split_sweep(0, self.z_piezo.Vmax, self.z_piezo_step, self.z_piezo_freq, i, numsteps)
                self.plot_cap(piezo_sweep_voltage, cap_voltage)

                if self.rsquared[i] > 0.9:
                    self.touchdown = True
                    V_td = self.get_touchdown_voltage()
                    if V_td > 0.75*self.z_piezo.Vmax:
                        self.touchdown = False
                        attosteps = attosteps/4 #make sure we don't crash!
                    break

            # monitor_cap('ai2', 20)
            self.z_piezo.V = 0

        self.lockin.amplitude = 0
            
        return V_td

    def check_balance(self):
        V_unbalanced = 10e-6 # We can balance better than 10 uV

        if self.lockin.R > V_unbalanced:
            raise Exception("Balance the capacitance bridge!")
        
    def configure_attocube(self):
        """ Set up z attocube """
        self.atto.mode = ['stp', 'gnd', 'gnd']
        self.atto.frequency = [200, None, None]
        if self.low_temp:
            self.atto.voltage = [55, None, None]
        else:
            self.atto.voltage = [40, None, None] #RT values    
    
    def configure_lockin(self):
        """ Set up lockin amplifier for capacitance detection """
        self.lockin.amplitude = 1
        self.lockin.frequency = 24989 # prime number ^_^
        self.lockin.set_out(1, 'R')
        self.lockin.set_out(2, 'theta')
        self.lockin.sensitivity = 5*self.lockin.R # lockin voltage should not increase by more than a factor of 5 during touchdown
        self.lockin.time_constant = 10e-3
        self.lockin.reserve = 'Low Noise'
        self.lockin.auto_phase()
        # self.check_balance() # do this in do function instead
        
            
    def configure_piezo(self):
        """ Set up z piezo parameters """
        self.z_piezo.in_channel = self.lockin.ch1_daq_input

        
        self.z_piezo_freq = 1/(5*self.lockin.time_constant) # measurement dwell time is 5 times longer than lockin time constant
        self.z_piezo_max_rate = 15 #V/s
        self.z_piezo_step = self.z_piezo_max_rate/self.z_piezo_freq
    
    def get_touchdown_voltage(self):
        
        V = self.Vpiezo_full
        C = self.cap_full
        
        r2_thresh = 0.98
        r2 = 1
        
        end = len(V)
        i=end+1-5 # fit at least 5 points; the +1 is perhaps counterintuitive, but it works
        
        while r2 > r2_thresh: # start fitting points from highest piezo voltage, add points until line fit becomes too bad
            i = i - 1
            m_td, b_td, r, _, _ = line(V[i:end], C[i:end])
            r2 = r**2
        
        m_approach, b_approach, _, _, _ = line(V[0:i], C[0:i])
        plt.figure()
        plt.plot(V, m_approach*np.array(V)+b_approach - C[0])
        plt.plot(V[i:end], m_td*np.array(V[i:end])+b_td - C[0])
        plt.plot(V,C - C[0],'.')
        
        V_td = (b_td - b_approach)/(m_approach - m_td)
        
        return V_td

    def plot_cap(self, Vpiezo, Vcap):
        Vcap = self.lockin.convert_output(Vcap) # convert to actual lockin voltage
        C = [v*self.V_to_C for v in Vcap] # convert to capacitance

        # plt.figure(self.fig.number)
        plt.plot(Vpiezo, C-C[0], 'k.')
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')
        plt.xlim(0, self.z_piezo.Vmax)
        
        slope, intercept, r, _, _ = line(Vpiezo, C)
        plt.plot(Vpiezo, slope*np.array(Vpiezo)+intercept-C[0] ,'-r')
        plt.draw()
        
        self.Vpiezo_full = self.Vpiezo_full + Vpiezo
        self.cap_full = self.cap_full + C
        self.rsquared.append(r**2)

        display.display(self.fig)
        display.clear_output(wait=True)

    def monitor_cap(self, inp, dur):
        data, t = self.daq.monitor(inp, dur)
        plt.figure()
        plt.plot(t,list(np.array(data)*self.lockin.sensitivity/10/1e-6))
        plt.xlabel('time (s)')
        plt.ylabel('capacitance imbalance (uV)')
        
        plt.show()
        
if __name__ == '__main__':
    import sys
    sys.path.append(r'C:\Users\Hemlock\Documents\GitHub\Nowack_Lab\Equipment_Drivers')
    sys.path.append(r'C:\Users\Hemlock\Documents\GitHub\Nowack_Lab\Procedures')
    sys.path.append(r'C:\Users\Hemlock\Documents\GitHub\Instrumental')
    import piezo as pz

    import attocube, srs, nidaq, time, touchdown 
    daq = nidaq.NIDAQ(False)
    atto = attocube.Attocube()
    lockin = srs.SR830('GPIB::09::INSTR')
    x_piezo = pz.Piezo('x', 15, True, daq, 'ao1')
    y_piezo = pz.Piezo('y', 15, True, daq, 'ao2')
    z_piezo = pz.Piezo('z', 15, False, daq, 'ao3')
    print('start td init')
    lockin.ch1_daq_input = 'ai2'

    td = touchdown.Touchdown(z_piezo, atto, lockin, daq)
    daq.ao3 = 0.00000001
    print('ao3', daq.ao3)
    
    print('end td init')
    
