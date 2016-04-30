from IPython import display
from scipy.stats import linregress as line
import time
import matplotlib.pyplot as plt
import numpy as np
from msvcrt import getch


class Touchdown():
    def __init__(self, z_piezo, atto, lockin, daq, cap_input, low_temp = False):    
        self.touchdown = False
        self.V_to_C = 2530e3 # 2530 pF/V * (1e3 fF/pF), calibrated 20160423 by BTS, see ipython notebook
        self.attosteps = 100 #number of attocube steps between sweeps
        self.numpts = 10 # number of points to sweep at a time
        
        self.z_piezo = z_piezo
        self.atto = atto
        self.lockin = lockin
        self.daq = daq
        
        self.lockin.ch1_daq_input = cap_input
                
        # isLowTemp = input('Testing at low temperature? [y/(n)]')
        # if isLowTemp in ('y', 'Y'):
            # self.low_temp = True
        # else:
            # self.low_temp = False
        self.low_temp = low_temp
        
        self.configure_attocube()
        self.configure_lockin()
        self.configure_piezo()
        
        self.Vpiezo_full = []
        self.cap_full = []
        self.rsquared = []

        self.fig = plt.figure()
        self.ax = plt.gca()
        display.clear_output()
        
    def do(self, planescan=False):
        tot_attosteps = -self.attosteps # so that will be zero at the beginning
        V_td = None

        attosteps = self.attosteps
        if planescan:
            attosteps = 0 # don't move the attocubes if doing a planescan
        
        while not self.touchdown:
            refresh_C0 = True

            if tot_attosteps >= 0: # don't move the first time
                self.atto.up([attosteps, None, None]) 
            
            tot_attosteps = tot_attosteps + attosteps
            
            plt.clf()
            if not planescan:
                plt.title('Attocube has moved %i steps.' %tot_attosteps)
            self.check_balance()
            
            self.Vpiezo_full = []
            self.cap_full = []
            self.rsquared = []

            numsteps = int(self.z_piezo.Vmax/self.z_piezo_step/self.numpts) # sweep in groups of self.numpts points
            for i in range(numsteps): 
                piezo_sweep_voltage, cap_voltage, t = self.z_piezo.split_sweep(-self.z_piezo.Vmax, self.z_piezo.Vmax, self.z_piezo_step, self.z_piezo_freq, i, numsteps)
                if refresh_C0:
                    self.C0 = self.lockin.convert_output(np.mean(cap_voltage))*self.V_to_C # sketchy way of getting zero point for capacitance
                    refresh_C0 = False
                self.plot_cap(piezo_sweep_voltage, cap_voltage)
                
                # This section commented for low temp testing manually
                """
                if self.rsquared[i] > 0.9:
                    if i==0: # this means that touchdown has already happened
                        break
                    self.touchdown = True
                    V_td = self.get_touchdown_voltage(plot=False) # just want to check value, don't plot until good TD!
                    if V_td > 0.6*self.z_piezo.Vmax:
                        self.touchdown = False
                        refresh_C0 = True
                        attosteps = self.attosteps/4 #make sure we don't crash! Don't keep on updating attosteps, otherwise it will go to zero eventually, and that means continuous!!!
                    elif V_td < 0.4*self.z_piezo.Vmax:
                        self.touchdown = False
                        refresh_C0 = True
                        attosteps = -self.attosteps/4 #move the other direction to bring V_td closer to midway #make sure we don't crash! Don't keep on updating attosteps, otherwise it will go to zero eventually, and that means continuous!!!
                    break
                    """
            
            # monitor_cap('ai2', 20)
            self.z_piezo.V = -self.z_piezo.Vmax       
                    
                    
            # time.sleep(5)
            # inp = input('Touchdown good(enter), bad (no) or move up or down? (u/d)')
            # if inp == '':
                # self.touchdown = True
                # V_td = self.manual_touchdown_voltage(plot = True)        
            # elif inp == 'u':
                # attosteps = self.attosteps/4
            # elif inp == 'd':
                # attosteps = -self.attosteps/4
                    
            self.touchdown = True
            V_td = self.manual_touchdown_voltage(plot = True)            

            
            if planescan:
                if V_td == None:
                    raise Exception('Need to adjust attocubes, piezo couldn\'t make it to the plane or touchdown has already happened!') # only check once, or else attocubes are aligned!
                else:
                    break
            
            first_iteration=False
        

        # self.get_touchdown_voltage(plot=True) # just for the plot
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
        self.lockin.sensitivity = 50e-6 # set this relatively high to make sure get good reading of lockin.R
        self.lockin.sensitivity = 10*self.lockin.R # lockin voltage should not increase by more than a factor of 10 during touchdown
        self.lockin.time_constant = 10e-3
        self.lockin.reserve = 'Low Noise'
        self.lockin.auto_phase()
        # self.check_balance() # do this in do function instead
        
            
    def configure_piezo(self):
        """ Set up z piezo parameters """
        self.z_piezo.in_channel = self.lockin.ch1_daq_input

        
        self.z_piezo_freq = 1/(5*self.lockin.time_constant) # measurement dwell time is 5 times longer than lockin time constant
        self.z_piezo_max_rate = 30 #V/s
        self.z_piezo_step = self.z_piezo_max_rate/self.z_piezo_freq
    
    def get_touchdown_voltage(self, plot=True):
        
        V = self.Vpiezo_full
        C = self.cap_full
        
        end = len(V)
        ## Old code: used to fit from the end, now just doing constant 10 points      
        # i=end+1-5 # fit at least 5 points; the +1 is perhaps counterintuitive, but it works
               
        # r2_thresh = 0.98
        # r2 = 1
        
        # while r2 > r2_thresh: # start fitting points from highest piezo voltage, add points until line fit becomes too bad
            # i = i - 1
            # m_td, b_td, r, _, _ = line(V[i:end], C[i:end])
            # r2 = r**2
        
        i = end-self.numpts # takes the data from the sweep that detected a TD
        m_td, b_td, r, _, _ = line(V[i:end], C[i:end])
        
        j = i-int(self.numpts/2) # safely away from TD points 
        m_approach, b_approach, _, _, _ = line(V[int(3*j/4):j], C[int(3*j/4):j]) # only fits the 1/4 of points up to supposed td point
        V_td = (b_td - b_approach)/(m_approach - m_td)

        if plot:
            plt.figure()
            plt.plot(V, m_approach*np.array(V)+b_approach - C[0])
            plt.plot(V[end-int(1.5*self.numpts):end], m_td*np.array(V[end-int(1.5*self.numpts):end])+b_td - C[0]) # last 1.5*self.numpts points, or else line goes off the chart!
            plt.plot(V,C - C[0],'.')
            plt.xlabel('Piezo voltage (V)')
            plt.ylabel(r'$C - C_{balance}$ (fF)')
            plt.title('V_td = %.2f V' %V_td)
            
            display.display(plt.gcf())
            display.clear_output(wait=True)
                    
        return V_td
    
    def manual_touchdown_voltage(self, plot=True):
        
        pts_end = 50
        # pts_end = int(input('points from end?'))
        #pts_begin = input('points from beginning?')
        
        V = self.Vpiezo_full
        C = self.cap_full
        
        end = len(V)
        
        i = end-pts_end # takes the data from the sweep that detected a TD
        m_td, b_td, r, _, _ = line(V[i:end], C[i:end])
        
        j = i-int(self.numpts/2) # safely away from TD points 
        m_approach, b_approach, _, _, _ = line(V[int(3*j/4):j], C[int(3*j/4):j]) # only fits the 1/4 of points up to supposed td point
        V_td = (b_td - b_approach)/(m_approach - m_td)

        if plot:
            plt.figure()
            plt.plot(V, m_approach*np.array(V)+b_approach - C[0])
            plt.plot(V[end-int(1.5*self.numpts):end], m_td*np.array(V[end-int(1.5*self.numpts):end])+b_td - C[0]) # last 1.5*self.numpts points, or else line goes off the chart!
            plt.plot(V,C - C[0],'.')
            plt.xlabel('Piezo voltage (V)')
            plt.ylabel(r'$C - C_{balance}$ (fF)')
            plt.title('V_td = %.2f V' %V_td)
            
            display.display(plt.gcf())
            display.clear_output(wait=True)
                    
        return V_td

    def plot_cap(self, Vpiezo, Vcap):
        Vcap = self.lockin.convert_output(Vcap) # convert to actual lockin voltage
        C = [v*self.V_to_C for v in Vcap] # convert to capacitance

        # plt.figure(self.fig.number)
        plt.plot(Vpiezo, C-self.C0, 'k.')
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')
        plt.xlim(-self.z_piezo.Vmax, self.z_piezo.Vmax)
        plt.ylim(-3,10)
        
        slope, intercept, r, _, _ = line(Vpiezo, C)
        plt.plot(Vpiezo, slope*np.array(Vpiezo)+intercept-self.C0 ,'-r')
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
    
