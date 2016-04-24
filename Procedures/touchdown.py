from IPython import display
from scipy.stats import linregress as line
import time

class Touchdown():
    def __init__(self, z_piezo, atto, lockin, cap_input, low_temp = False):    
        self.touchdown = False
        self.cap_input = cap_input
        self.V_to_C = 2530e3 # 2530 pF/V * (1e3 fF/pF), calibrated 20160423 by BTS, see ipython notebook

        self.z_piezo = z_piezo
        self.atto = atto
        self.lockin = lockin
        self.low_temp = low_temp
        
        self.configure_attocube()
        self.configure_lockin()
        self.configure_piezo()
        
        self.Vpiezo_full = []
        self.cap_full = []
        self.rsquared = []

    def do(self):
        while not self.touchdown:            
            #atto.up([200, None, None])
            self.Vpiezo_full = []
            self.cap_full = []
            self.rsquared = []
            num_avg = 10

            numsteps = int(self.z_piezo.Vmax/self.z_piezo_step/num_avg) # sweep in groups of num_avg points
            for i in range(numsteps): 
                piezo_sweep_voltage, cap_voltage, t = self.z_piezo.split_sweep(0, self.z_piezo.Vmax, self.z_piezo_step, self.z_piezo_freq, i, numsteps)
                self.plot_cap(piezo_sweep_voltage, cap_voltage)

                if self.rsquared[i] > 0.8:
                    self.touchdown = True
                    V_td = self.get_touchdown_voltage()
                    break

            # monitor_cap('ai2', 20)
            self.z_piezo.V = 0

        return V_td

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
        V_unbalanced = 10e-6 # We can balance better than 10 uV
        self.lockin.amplitude = 1
        self.lockin.frequency = 25000
        self.lockin.set_out(1, 'R')
        self.lockin.set_out(2, 'theta')
        self.lockin.sensitivity = 5*self.lockin.R # lockin voltage should not increase by more than a factor of 5 during touchdown
        self.lockin.time_constant = 10e-3
        self.lockin.reserve = 'Low Noise'
        self.lockin.auto_phase()
        if self.lockin.R > V_unbalanced:
            raise Exception("Balance the capacitance bridge!")
            
    def configure_piezo(self):
        """ Set up z piezo parameters """ 
        self.z_piezo_max_rate = 15 #V/s
        self.z_piezo_freq = 1/(5*lockin.time_constant) # measurement dwell time is 5 times longer than lockin time constant
        self.z_piezo_step = self.z_piezo_max_rate/self.z_piezo_freq
    
    def get_touchdown_voltage(self):
        
        V = self.Vpiezo_full
        C = self.cap_full
        
        r2_thresh = 0.95
        r2 = 1
        
        end = len(V)
        i=end-2 # fit at least 3 points
        
        while r2 > r2_thresh: # start fitting points from highest piezo voltage, add points until line fit becomes too bad
            i = i - 1
            m_td, b_td, r, _, _ = line(V[i:end], C[i:end])
            r2 = r**2
        
        m_approach, b_approach, _, _, _ = line(V[0:i], C[0:i])
        figure()
        plot(V, m_approach*array(V)+b_approach - C[0])
        plot(V[i:end], m_td*array(V[i:end])+b_td - C[0])
        plot(V,C - C[0],'.')
        
        V_td = (b_td - b_approach)/(m_approach - m_td)
        
        return V_td

    def plot_cap(self, Vpiezo, Vcap):
        Vcap = self.lockin.convert_output(Vcap) # convert to actual lockin voltage
        C = [v*self.V_to_C for v in Vcap] # convert to capacitance

        plot(Vpiezo, C-C[0], 'k.')
        xlabel('Piezo voltage (V)')
        ylabel(r'$C - C_{balance}$ (fF)')

        xlim(0, self.z_piezo.Vmax)
        
        slope, intercept, r, _, _ = line(Vpiezo, C)
        plot(Vpiezo, slope*array(Vpiezo)+intercept-C[0] ,'-r')

        self.Vpiezo_full = self.Vpiezo_full + Vpiezo
        self.cap_full = self.cap_full + C
        self.rsquared.append(r**2)

        display.display(gcf())
        display.clear_output(wait=True)

    def monitor_cap(self, inp, dur):
        daq = nidaq.NIDAQ()
        data, t = daq.monitor(inp, dur)
        figure()
        plot(t,list(array(data)*self.lockin.sensitivity/10/1e-6))
        xlabel('time (s)')
        ylabel('capacitance imbalance (uV)')
        
if __name__ == '__main__':
	touchdown = Touchdown(z_piezo, atto, lockin, 'ai2')
	touchdown.do()