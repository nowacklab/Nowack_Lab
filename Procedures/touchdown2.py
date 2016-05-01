from IPython import display
from scipy.stats import linregress as line
import time
import matplotlib.pyplot as plt
import numpy as np
from msvcrt import getch

class Touchdown2():
    def __init__(self, z_piezo, atto, lockin, daq, cap_input, low_temp = False):    
        self.touchdown = False
        self.V_to_C = 2530e3 # 2530 pF/V * (1e3 fF/pF), calibrated 20160423 by BTS, see ipython notebook
        self.attosteps = 100 #number of attocube steps between sweeps
        self.numfit = 10       # number of points to fit line to while collecting data  
                
        self.z_piezo = z_piezo
        self.atto = atto
        self.lockin = lockin
        self.daq = daq
        
        self.lockin.ch1_daq_input = cap_input
                
        self.low_temp = low_temp
        
        self.configure_attocube()
        self.configure_piezo() # Need this to set up time constant of lockin properly
        self.configure_lockin()
        
        self.V = [] # Piezo voltage
        self.C = [] # Capacitance
        self.C0 = None # Cap offset
        self.extra = 0 # Extra points to add to fit after TD detected

        self.fig = plt.figure()
        self.ax = plt.gca()
        display.clear_output()
        
    def check_balance(self):
        V_unbalanced = 10e-6 # We can balance better than 10 uV

        if self.lockin.R > V_unbalanced:
            raise Exception("Balance the capacitance bridge!")    
       
       
    def do(self, planescan=False):
        V_td = None
        attosteps = self.attosteps
        
        numsteps = int(2*self.z_piezo.Vmax/self.z_piezo_step)
        self.V = np.linspace(-self.z_piezo.Vmax, self.z_piezo.Vmax, numsteps)
        
        while not self.touchdown: # loop will move up attocubes every time
        
            self.check_balance()

            self.C = [None]*numsteps # Capacitance       
            self.C0 = None # Cap offset
            self.extra = 0
            
            for i in range(numsteps):
                self.z_piezo.V = self.V[i]
                Vcap = getattr(self.daq, self.lockin.ch1_daq_input)
                Vcap = self.lockin.convert_output(Vcap) # convert to a lockin voltage
                Cap = Vcap*self.V_to_C
                if self.C0 == None: 
                    self.C0 = Cap # make the first point zero
                self.C[i] = Cap - self.C0
                self.plot_cap(i)
                if i >= self.numfit: # start checking after min number of pts
                    self.check_touchdown(i)
                    
                if self.touchdown:
                    if self.extra < 3: # take three extra points for fit
                        self.extra = self.extra + 1 
                    else:    
                        V_td = self.get_touchdown_voltage(i, plot=False)                        
                        if V_td > 0.6*self.z_piezo.Vmax:
                            self.touchdown = False
                            attosteps = self.attosteps/4 #make sure we don't crash! Don't keep on updating attosteps, otherwise it will go to zero eventually, and that means continuous!!!
                        elif V_td < 0.4*self.z_piezo.Vmax:
                            self.touchdown = False
                            attosteps = -self.attosteps/4 #move the other direction to bring V_td closer to midway #make sure we don't crash! Don't keep on updating attosteps, otherwise it will go to zero eventually, and that means continuous!!!
                        break
                
            V_td = self.get_touchdown_voltage(i, plot=True) # just for plotting
                
            if planescan:
                if V_td == None:
                    raise Exception('Need to adjust attocubes, piezo couldn\'t make it to the plane or touchdown has already happened!') # only check once, or else attocubes are aligned!
                  
            self.z_piezo.V = 0
                
            #self.touchdown = True
            if not self.touchdown:
                self.z_piezo.V = -self.z_piezo.Vmax # before moving attocubes, make sure we're far away from the sample!
                self.atto.up([attosteps, None, None]) 
                                  
        self.lockin.amplitude = 0            
                    
        return V_td

        
    def check_touchdown(self, i): 
        dev_from_mean = self.C[i]/abs(np.mean(self.C[i-self.numfit:i]))
        
        if dev_from_mean > 20: # Look at the last self.numfit points before i, and see if this point is much higher
            self.touchdown = True
            
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
        self.lockin.sensitivity = 50e-6 # set this relatively high to make sure get good reading of lockin.R
        self.lockin.sensitivity = 10*self.lockin.R # lockin voltage should not increase by more than a factor of 10 during touchdown
        self.lockin.time_constant = 1/(5*self.z_piezo_freq) # time constant five times shorter than dwell time for measurement
        self.lockin.reserve = 'Low Noise'
        self.lockin.auto_phase()
        # self.check_balance() # do this in do function instead
        
            
    def configure_piezo(self):
        """ Set up z piezo parameters """
        self.z_piezo.in_channel = self.lockin.ch1_daq_input
        self.z_piezo_max_rate = 30 #V/s
        self.z_piezo_step = 4 # For full 120 V to -120 V sweep, this is 120 points
        self.z_piezo_freq = self.z_piezo_max_rate/self.z_piezo_max_rate
 
    def get_touchdown_voltage(self, i, plot=False):
        minfit = 5 # at minimum, fit 5 points from the end
        j = i-minfit
        k = j-minfit  # so we don't fit approach too close
        m_td, b_td, r, _, _ = line(self.V[j:i+1], self.C[j:i+1])
        m_app, b_app, r, _, _ = line(self.V[int(0.85*k):k+1], self.C[int(0.85*k):k+1]) # fit the last quarter of points
        V_td = (b_td - b_app)/(m_app - m_td)
        
        if plot:
            plt.clf()
            plt.plot(self.V[int(0.85*k):i+1], m_app*np.array(self.V[int(0.85*k):i+1])+b_app)
            plt.plot(self.V[j-2:i+1], m_td*np.array(self.V[j-2:i+1])+b_td) # 2 is arbitrary, just wanted some more points drawn
            plt.plot(self.V,self.C,'.')
            plt.title('V_td = %.2f V' %V_td)
            
            display.display(plt.gcf())
            display.clear_output(wait=True)
        return V_td
 
    def plot_cap(self, i):
        plt.clf()

        plt.plot(self.V, self.C, 'k.')
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')
        plt.xlim(-self.z_piezo.Vmax, self.z_piezo.Vmax)
        plt.ylim(-2,5)
                
        if i+1 >= self.numfit: # start fitting after min number of points
            Vfit = self.V[i+1-self.numfit:i+1] # take slice of last self.numfit points
            Cfit = self.C[i+1-self.numfit:i+1]
            slope, intercept, r, _, _ = line(Vfit, Cfit)
            plt.plot(Vfit, slope*np.array(Vfit)+intercept,'-r', lw=2)
            plt.draw()

        display.display(self.fig)
        display.clear_output(wait=True)