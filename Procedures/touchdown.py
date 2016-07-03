from IPython import display
from scipy.stats import linregress
from scipy.optimize import curve_fit
import time
import matplotlib.pyplot as plt
import numpy as np
from msvcrt import getch

class Touchdown():
    def __init__(self, instruments, cap_input, planescan=False):    
        self.touchdown = False
        self.V_to_C = 2530e3 # 2530 pF/V * (1e3 fF/pF), calibrated 20160423 by BTS, see ipython notebook
        self.attosteps = 200 #number of attocube steps between sweeps
        self.numfit = 10       # number of points to fit line to while collecting data  
        self.numextra = 3
                
        self.piezos = instruments['piezos']
        self.atto = instruments['atto']
        self.lockin = instruments['lockin']
        self.daq = instruments['daq']
        self.montana = instruments['montana']
                
        self.lockin.ch1_daq_input = 'ai%s' %cap_input
        
        if self.montana.temperature['platform'] < 10:
            self.low_temp = True
        else:
            self.low_temp = False
        
        self.planescan = planescan
        
        self.configure_attocube()
        self.configure_piezo() # Need this to set up time constant of lockin properly
        self.configure_lockin()
        
        self.V = [] # Piezo voltage
        self.C = [] # Capacitance
        self.C0 = None # Cap offset
        self.extra = 0 # Extra points to add to fit after TD detected
        self.V_td = -1000.0
                
        self.fig = plt.figure()
        self.ax = plt.gca()
        display.clear_output()
        
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_td'
        if self.planescan:
            self.filename = self.filename + '_planescan'
        
    def check_balance(self):
        V_unbalanced = 10e-6 # We can balance better than 10 uV

        if self.lockin.R > V_unbalanced:
            raise Exception('Balance the capacitance bridge!')
       
    def do(self):        
        V_td = None
        attosteps = self.attosteps # This is how many steps the attocubes will move if no touchdown detected.
        if self.planescan:
            attosteps = None # don't move the attocubes if doing a planescan - remember, 0 is continuous!
        
        ## voltage sweep is from -Vmax to Vmax, step size determined in configure_piezo. 4 V looks good.
        numsteps = int(2*self.piezos.Vmax['z']/self.z_piezo_step)
        self.V = np.linspace(-self.piezos.Vmax['z'], self.piezos.Vmax['z'], numsteps)
        
        self.check_balance() # Make sure capacitance bridge is well-balanced
         
        while not self.touchdown: # loop will move up attocubes every time

            self.C = [None]*numsteps # Capacitance (fF)
            self.C0 = None # Cap offset... will take on value of the first point
            self.extra = 0 # Counter to keep track of extra points after touchdown (for fitting the line)
            
            for i in range(numsteps): # Loop over each piezo voltage
                self.piezos.V = {'z': self.V[i]} # Set the current voltage
                
                ## Get capacitance
                Vcap = getattr(self.daq, self.lockin.ch1_daq_input) # Read the voltage from the daq
                Vcap = self.lockin.convert_output(Vcap) # convert to a lockin voltage
                Cap = Vcap*self.V_to_C # convert to true capacitance (fF)
                
                if self.C0 == None: 
                    time.sleep(1) # wait for stabilization, was getting weird first values
                    self.C0 = Cap # Sets the offset datum   
                self.C[i] = Cap - self.C0 # remove offset
                
                if i >= self.numfit: # start fitting the line after min number of points have come in
                    self.check_touchdown(i)
                self.plot_cap(i)
                    
                if self.touchdown:
                    if self.extra < self.numextra: # take three extra points for fit
                        self.extra = self.extra + 1 
                        if i == numsteps - 1:
                            self.touchdown = False # special case; there was a bug where if last extra point was last point taken, touchdown would be detected as true
                            
                    else:    
                        V_td = self.get_touchdown_voltage(i, plot=False)   
                        if not self.planescan: # Don't want to move attocubes during planescan
                            # For central touchdown of plane, we want to get the touchdown voltage near the center of the piezo's positive voltage range.
                            if V_td > 0.65*self.piezos.Vmax['z']:
                                self.touchdown = False
                                attosteps = self.attosteps/8 #make sure we don't crash! Don't keep on updating attosteps, otherwise it will go to zero eventually, and that means continuous!!!
                            elif V_td < 0.35*self.piezos.Vmax['z']:
                                self.touchdown = False
                                attosteps = -self.attosteps/8 #move the other direction to bring V_td closer to midway #make sure we don't crash! Don't keep on updating attosteps, otherwise it will go to zero eventually, and that means continuous!!!
                        elif V_td < 0: # This is obviously a false touchdown; for planescan only
                            self.touchdown=False 
                        elif self.extra == self.numextra: # last extra step
                            rsquared = self.line_corr_coef(self.V[i-self.numextra:i+1], self.C[i-self.numextra:i+1]) #check fit of last few points
                            if rsquared < 0.90:
                                self.touchdown=False # false touchdown
                        break
            
            if self.extra != self.numextra: # did not take enough extra steps, TD is at end of range
                self.touchdown = False 
            
              ## This following code probably only for super extremely tilted samples... may not need to worry about this
            # if planescan:
                # if V_td == None:
                    # raise Exception('Need to adjust attocubes, piezo couldn\'t make it to the plane or touchdown has already happened!') # only check once, or else attocubes are aligned!
                  
            self.piezos.V = {'z': 0} # bring the piezo back to zero
                
            ## Move the attocubes; either we're too far away for a touchdown or TD voltage not centered    
            if not self.touchdown: 
                self.piezos.V = {'z': -self.piezos.Vmax['z']} # before moving attocubes, make sure we're far away from the sample!
                self.atto.up({'z': attosteps}) 
                time.sleep(2) # was getting weird capacitance values immediately after moving; wait a bit
        
        # Didn't work
        # except KeyboardInterrupt:
            # self.piezos.V = {'z': 0, 'y': 0, 'x': 0}
            # self.atto.mode = ['gnd', 'gnd', 'gnd']
            # self.lockin.amplitude = 0
            # print('Piezos zeroed, attocubes grounded, lockin off')
        
        V_td = self.get_touchdown_voltage(i, plot=True) # we didn't plot the intersecting lines before, so let's do that now.
        # self.lockin.amplitude = 0  # turn off the lockin          
                                 
        self.V_td = V_td   
        self.save() 

        return V_td

        
    def check_touchdown(self, i): 
        #last_std = np.std(self.C[i-int(self.numfit):i]) # looks at standard deviation of last self.numfit points up to i
        std = np.std(self.C[1:i]) # standard deviation of all points so far
        deviation = abs(self.C[i] - np.mean(self.C[i+1-int(self.numfit):i+1])) # deviation of the ith point from average of last self.numfit points, including i
              
        if deviation > 4*std and abs(self.C[i]-self.C[i-1]) > 0.4: # Touchdown if further than 4 standard deviations away and capacitance change between last two points above 0.4 fF.. will also account for dip
            self.touchdown = True
            
    def configure_attocube(self):
        """ Set up z attocube """
        self.atto.freq = {'z': 200}
    
    def configure_lockin(self):
        """ Set up lockin amplifier for capacitance detection """
        self.lockin.amplitude = 1
        self.lockin.frequency = 24989 # prime number ^_^
        self.lockin.set_out(1, 'R') # Possibly X is better?
        self.lockin.set_out(2, 'theta') # not used, but may be good to see
        self.lockin.sensitivity = 50e-6 # set this relatively high to make sure get good reading of lockin.R
        self.lockin.sensitivity = 20*self.lockin.R # lockin voltage should not increase by more than a factor of 10 during touchdown
        self.lockin.time_constant = 1/(5*self.z_piezo_freq) # time constant five times shorter than dwell time for measurement
        self.lockin.reserve = 'Low Noise'
        self.lockin.auto_phase()        
            
    def configure_piezo(self):
        """ Set up z piezo parameters """
        # As of 5/3/2016, only z_piezo_step is used, and the daq sends points one at a time as fast as possible. But this seems fast enough. Might as well just hard-code a time constant.
        self.z_piezo_max_rate = 30 #V/s
        self.z_piezo_step = 2 # 1V at RT, 2V at low T works? # For full 120 V to -120 V sweep, 1 V step is 480 points
        self.z_piezo_freq = self.z_piezo_max_rate/self.z_piezo_max_rate
 
    def line(self, x, y):
        """ Fits a line given x data, y data. Not sure if curve_fit or linregress is better, or if there is no difference. """
        # m, b, r, _, _ = linregress(x,y)
        # return m,b
        def f(x, m, b):
            return m*x + b
        popt, _ = curve_fit(f, x, y)
        return popt[0], popt[1] # m, b
 
    def line_corr_coef(self, x,y):
        m, b, r, _, _ = linregress(x,y)
        return r**2
 
    def get_touchdown_voltage(self, i, plot=False):
        minfit = self.numextra # at minimum, fit 3 points from the end
        j = i-minfit # lower index of touchdown line
        k = j-minfit  # upper index of approach line, a little buffer added to avoid fitting actual touchdown points
        m_td, b_td = self.line(self.V[j:i+1], self.C[j:i+1])
        m_app, b_app = self.line(self.V[int(0.5*k):k+1], self.C[int(0.5*k):k+1]) # fit the last half of points
        V_td = (b_td - b_app)/(m_app - m_td) # intersection of two lines. Remember high school algebra?
        
        if plot:
            orange = '#F18C22'
            blue = '#47C3D3'
            
            plt.clf()
            plt.plot(self.V[j-2:i+1], m_td*np.array(self.V[j-2:i+1])+b_td, blue, lw=2) # 2 is arbitrary, just wanted some more points drawn
            plt.plot(self.V,self.C,'.k') 
            plt.plot(self.V[int(0.5*k):i+1], m_app*np.array(self.V[int(0.5*k):i+1])+b_app, orange, lw=2)
            
            plt.title('%s\nTouchdown at %.2f V' %(self.filename, V_td), fontsize=20)
            plt.xlabel('Piezo voltage (V)', fontsize=20)
            plt.ylabel(r'$C - C_{\sf balance}$ (fF)', fontsize=20)
            plt.xlim(-self.piezos.Vmax['z'], self.piezos.Vmax['z'])
            
            display.display(plt.gcf())
            display.clear_output(wait=True)
        return V_td
 
    def plot_cap(self, i):
        plt.clf()

        plt.plot(self.V, self.C, 'k.')
        if self.touchdown:
            plt.title('Touchdown detected!')
        plt.xlabel('Piezo voltage (V)')
        plt.ylabel(r'$C - C_{balance}$ (fF)')
        plt.xlim(-self.piezos.Vmax['z'], self.piezos.Vmax['z'])
        plt.ylim(-1,5)
                
        if i+1 >= self.numfit: # start fitting after min number of points
            Vfit = self.V[i+1-self.numfit:i+1] # take slice of last self.numfit points
            Cfit = self.C[i+1-self.numfit:i+1]
            #slope, intercept = self.line(Vfit, Cfit)
            # plt.plot(Vfit, slope*np.array(Vfit)+intercept,'-r', lw=2)
            plt.plot(Vfit, Cfit, 'r.') # just overlays red markers for last numfit points, recycled old code
            plt.draw()

        display.display(self.fig)
        display.clear_output(wait=True)
        
    def save(self):
        home = os.path.expanduser("~")
        data_folder = home + 'Dropbox (Nowack lab)\\TeamData\\Montana\\Touchdowns\\'

        filename = data_folder + self.filename
        with open(filename+'.txt', 'w') as f:
            f.write('V_td = %f\n' %self.V_td)
            f.write('V_to_C conversion in fF/V = %f\n' %self.V_to_C)
            f.write('Lockin parameters\n')
            f.write(self.lockin.get_all())
            f.write('\n')
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('V (V)\tC (fF)\n')
            for i in range(len(self.V)):
                if self.C[i] != None:
                    f.write('%f' %self.V[i] + ',' + '%f' %self.C[i] + '\n')
        
        plt.savefig(filename+'.pdf', bbox_inches='tight')
        
        