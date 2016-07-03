""" Procedure to take an mod 2D plot of IV's for a SQUID. By default, assumes SQUID -40 uA to 40 uA sweep (0.5 uA step) and mod -100 uA to 100 uA sweep (4 uA step), both over a 2kOhm bias resistor. Can change these values when prompted. """

from IPython import display
import matplotlib.pyplot as plt
import numpy as np
import time
from . import squidIV

class Mod2D():
    def __init__(self, instruments, squidout, squidin, modout, rate=900):   
        """ Example: Mod2D({'daq': daq, 'preamp': preamp}, 'ao0','ai0','ao1', rate=900) """
    
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_mod2D'
        self.notes = ''

        self.IV = squidIV.SquidIV(instruments, squidout, squidin, modout, rate=rate)
        
        self.IV.Rbias = 2e3 # Ohm # 1k cold bias resistors on the SQUID testing PCB
        self.IV.Rbias_mod = 2e3 # Ohm # 1k cold bias resistors on the SQUID testing PCB
        self.IV.Irampspan = 120e-6 # A # Will sweep from -Irampspan/2 to +Irampspan/2
        self.IV.Irampstep = 0.5e-6 # A # Step size

        self.Imodspan = 200e-6
        self.Imodstep = 4e-6
        
        self.IV.calc_ramp()
        self.calc_ramp()
       
        display.clear_output()
        
        
    def calc_ramp(self):
        self.numpts = int(self.Imodspan/self.Imodstep)        
        self.Imod = np.linspace(-self.Imodspan/2, self.Imodspan/2, self.numpts) # Squid current
        self.V = np.array([[float('nan')]*self.IV.numpts]*self.numpts) # num points in IV by num points in mod sweep
        
    def do(self): 
        self.calc_ramp() #easy way to clear self.V
        self.IV.V = self.IV.V*0
        
        self.param_prompt() # Check parameters
        self.setup_plot()

        for i in range(len(self.Imod)):
            self.IV.Imod = self.Imod[i]
            self.IV.do_IV()
            self.axIV.clear()
            self.IV.plot(self.axIV)
            self.V[:][i] = self.IV.V
            self.plot()
            self.fig.canvas.draw() #draws the plot; needed for %matplotlib notebook
        self.IV.daq.zero() # zero everything

            
        inp = input('Press enter to save data, type anything else to quit. ')
        if inp == '':
            self.save()
        
    def param_prompt(self):
        """ Check and confirm values of parameters """
        correct = False
        while not correct:
            for param in ['rate', 'Rbias', 'Rbias_mod', 'Irampspan', 'Irampstep']:
                print('IV', param, ':', getattr(self.IV, param))
            for parammod in ['Imodspan','Imodstep']:
                print(parammod, ':', getattr(self, parammod))
            for paramamp in ['gain','filter']:
                print('IV preamp', paramamp, ':', getattr(self.IV.preamp, paramamp))

            if self.IV.rate > self.IV.preamp.filter[1]:
                print("You're filtering out your signal... fix the preamp cutoff\n")
            if self.IV.Irampspan > 200e-6:
                print("You want the SQUID biased above 100 uA?... don't kill the SQUID!\n")
            if self.Imodspan > 300e-6:
                print("You want the SQUID mod biased above 150 uA?... don't kill the SQUID!\n")
            
            try:
                inp = input('Are these parameters correct? Enter a command to change parameters, or press enter to continue (e.g. IV.preamp.gain = 100): ')
                if inp == '':
                    correct = True
                else:
                    exec('self.'+inp)
                    self.IV.calc_ramp()
                    self.calc_ramp() # recalculate daq output
                    display.clear_output()
            except:
                display.clear_output()
                print('Invalid command\n')

        self.notes = input('Notes for this mod2D: ')
        if self.notes == 'quit':
            raise Exception('Quit by user')
        self.IV.notes = self.notes # or else it will complain when plotting :(
         
    def plot(self):

        Vm = np.ma.masked_where(np.isnan(self.V),self.V) #hides data not yet collected
        self.im.set_array(Vm) #updates plot data
        
        self.cb.set_clim(Vm.min(), Vm.max())
        self.cb.draw_all()
        
        #display.display(self.fig)
        #display.clear_output(wait=True)

        
    def save(self):
        home = os.path.expanduser("~")  
        data_folder = home+'Dropbox (Nowack lab)\\TeamData\\Montana\\squid_testing\\mod2D\\'

        filename = data_folder + self.filename
        with open(filename+'.txt', 'w') as f:
            f.write(self.notes+'\n')
            f.write('Montana info: \n'+self.IV.montana.log()+'\n')
            for param in ['rate', 'Rbias', 'Rbias_mod', 'Irampspan', 'Irampstep']:
                f.write('IV' + param + ': ' + str(getattr(self.IV, param)) + '\n')
            for parammod in ['Imodspan','Imodstep']:
                f.write(parammod + ': ' + str(getattr(self, parammod)) + '\n')
            for paramamp in ['gain','filter']:
                f.write('IV preamp ' + paramamp + ': ' + str(getattr(self.IV.preamp, paramamp)) + '\n') 
           
            f.write('Isquid (V),Imod (V),Vsquid (V)\n')
            for i in range(self.numpts): 
                for j in range(self.IV.numpts):
                    if self.V[i][j] != None:
                        f.write('%f' %self.IV.I[j] + ',' + '%f' %self.Imod[i] + ',' + '%f' %self.V[i][j] + '\n')
        
        plt.figure(self.fig.number)
        plt.savefig(filename+'.pdf')
        
    def setup_plot(self):
        self.fig, (self.axIV, self.ax2D) = plt.subplots(2,1,figsize=(7,7),gridspec_kw = {'height_ratios':[1, 3]})
        
        # Set up 2D plot
        Vm = np.ma.masked_where(np.isnan(self.V),self.V) #hides data not yet collected
        self.im = self.ax2D.imshow(Vm,cmap='RdBu', interpolation='none',aspect='auto', extent = [min(self.IV.I*1e6), max(self.IV.I*1e6), min(self.Imod*1e6), max(self.Imod*1e6)])
        self.ax2D.set_title(self.filename+'\n'+self.notes) 
        self.ax2D.set_xlabel(r'$I_{\rm{bias}} = V_{\rm{bias}}/R_{\rm{bias}}$ ($\mu \rm A$)', fontsize=20)
        self.ax2D.set_ylabel(r'$I_{\rm{mod}} = V_{\rm{mod}}/R_{\rm{mod}}$ ($\mu \rm A$)', fontsize=20)
        self.cb = self.fig.colorbar(self.im, ax = self.ax2D)
        self.cb.set_label(label = r'$V_{\rm{squid}}$ $(\rm V)$', fontsize=20)
        self.cb.formatter.set_powerlimits((-2, 2))
