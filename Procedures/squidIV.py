""" Procedure to take an IV curve for a SQUID. By default, assumes -100 uA to 100 uA sweep (0.5 uA step) over a 2kOhm bias resistor and zero mod current. Can change these values when prompted. """

# TO DO:    - Try sweep vs individual points
#           - Build in acceleration to daq sweep to and from zero?
#           - Do up and down sweeps?

from IPython import display
import matplotlib.pyplot as plt
import numpy as np
import time

class SquidIV():
    def __init__(self, instruments, squidout, squidin, modout=None, rate=90):   
        """ Example: SquidIV({'daq': daq, 'preamp': preamp}, 0, 0, 1, 90) """
    
        self.daq = instruments['daq']
        self.preamp = instruments['preamp']
        self.montana = instruments['montana']
        
        self.squidout = 'ao%s' %squidout
        self.squidin = 'ai%s' %squidin
        self.daq.add_input(self.squidin) # make sure to monitor this channel with the daq
        self.modout = 'ao%s' %modout
        
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_IV'
        self.notes = ''

        self.rate = rate # Hz # measurement rate of the daq
        self.preamp.gain = 500 
        self.preamp.filter_mode('low',6)
        self.preamp.filter = (0, rate) # Hz  
        self.preamp.dc_coupling()
        self.preamp.diff_input()
        
        self.Rbias = 2e3 # Ohm # 1k cold bias resistors on the SQUID testing PCB
        self.Rbias_mod = 2e3 # Ohm # 1k cold bias resistors on the SQUID testing PCB
        self.Imod = 0 # A # constant mod current
        
        self.Irampspan = 200e-6 # A # Will sweep from -Irampspan/2 to +Irampspan/2
        self.Irampstep = 0.5e-6 # A # Step size
        
        self.calc_ramp()
        self.V = [] # Measured voltage
        
        display.clear_output()
        

        
    def calc_ramp(self):
        self.numpts = int(self.Irampspan/self.Irampstep)        
        self.I = np.linspace(-self.Irampspan/2, self.Irampspan/2, self.numpts) # Squid current
        self.Vbias = self.I*self.Rbias # SQUID bias voltage
                       
    def do(self):
        self.param_prompt() # Check parameters
        
        self.do_IV()
        self.daq.zero() # zero everything
        
        self.fig, self.ax = plt.subplots()
        self.plot()
        self.fig.canvas.draw() #draws the plot; needed for %matplotlib notebook

        inp = input('Press enter to save data, type redo to redo, type anything else to quit. ')
        if inp == '':
            self.save()
        elif inp == 'redo':
            display.clear_output()
            self.do()
               
        # if self.modout != None:
            # setattr(self.daq, self.modout, 0) # Zero mod current
                   
    def do_IV(self):
        """ Wrote this for mod2D so it doesn't plot """
        if self.modout != None:
            setattr(self.daq, self.modout, self.Imod*self.Rbias_mod) # Set mod current
        
        # Collect data
        Vout, Vin, time = self.daq.sweep(self.squidout, self.Vbias[0], self.Vbias[-1], freq=self.rate, numsteps=self.numpts)
        self.V = np.array(Vin[self.squidin])/self.preamp.gain
                   
    def param_prompt(self):
        """ Check and confirm values of parameters """
        correct = False
        while not correct:
            for param in ['rate', 'Rbias', 'Rbias_mod', 'Imod', 'Irampspan', 'Irampstep']:
                print(param, ':', getattr(self, param))
            for paramamp in ['gain','filter']:
                print('preamp', paramamp, ':', getattr(self.preamp, paramamp))

            if self.rate >= self.preamp.filter[1]:
                print("You're filtering out your signal... fix the preamp cutoff\n")
            if self.Irampspan > 200e-6:
                print("You want the SQUID biased above 100 uA?... don't kill the SQUID!\n")
            
            try:
                inp = input('Are these parameters correct?\n Enter a command to change parameters, or press enter to continue (e.g. preamp.gain = 100): \n')
                if inp == '':
                    correct = True
                else:
                    exec('self.'+inp)
                    self.calc_ramp() # recalculate daq output
                    display.clear_output()
            except:
                display.clear_output()
                print('Invalid command\n')

                
        self.notes = input('Notes for this IV: ')
        if self.notes == 'quit':
            raise Exception('Quit by user')
         
    def plot(self, ax=None):
        if ax == None:
            ax = self.ax
        
        ax.plot(self.I*1e6, self.V, 'k-')
        ax.set_title(self.filename+'\n'+self.notes) # NEED DESCRIPTIVE TITLE
        ax.set_xlabel(r'$I_{\rm{bias}} = V_{\rm{bias}}/R_{\rm{bias}}$ ($\mu \rm A$)', fontsize=20)
        ax.set_ylabel(r'$V_{\rm{squid}}$ (V)', fontsize=20)
        ax.ticklabel_format(style='sci', axis='y', scilimits=(-3,3))
        return ax
                        
    def save(self):
        data_folder = 'C:\\Users\\Hemlock\\Dropbox (Nowack lab)\\TeamData\\Montana\\squid_testing\\IV\\'

        filename = data_folder + self.filename
        with open(filename+'.txt', 'w') as f:
            f.write(self.notes+'\n')
            f.write('Montana info: \n'+self.montana.log()+'\n')
            for param in ['rate', 'Rbias', 'Rbias_mod', 'Imod', 'Irampspan', 'Irampstep']:
                f.write(param + ': ' + str(getattr(self, param)) + '\n')
            for paramamp in ['gain','filter']:
                f.write('preamp ' + paramamp + ': ' + str(getattr(self.preamp, paramamp)) + '\n') 
            f.write('I (A),V (V)\n')
            for i in range(len(self.V)):
                f.write('%f' %self.I[i] + ',' + '%f' %self.V[i] + '\n')

        plt.savefig(filename+'.pdf')