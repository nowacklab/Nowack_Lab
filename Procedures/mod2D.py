""" Procedure to take an mod 2D plot of IV's for a SQUID. By default, assumes SQUID -40 uA to 40 uA sweep (0.5 uA step) and mod -100 uA to 100 uA sweep (4 uA step), both over a 2kOhm bias resistor. Can change these values when prompted. """

from IPython import display
import matplotlib.pyplot as plt
import numpy as np
import time, os
from datetime import datetime
from . import squidIV
from ..Utilities.plotting import plot_mpl
from ..Utilities.save import Measurement, get_todays_data_path

class Mod2D(Measurement):
    notes = ''
    def __init__(self, instruments={}, squidout=None, squidin=None, modout=None, rate=900):
        '''
        Example: Mod2D({'daq': daq, 'preamp': preamp}, 'ao0','ai0','ao1', rate=900).
        To make an empty object, then just call Mod2D().
        You can do this if you want to plot previously collected data.
        '''
        super().__init__('mod2D')

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

    def __getstate__(self):
        self.save_dict.update({"timestamp": self.timestamp,
                              "IV": self.IV,
                              "Imodspan": self.Imodspan,
                              "Imodstep": self.Imodstep,
                              "V": self.V,
                              "notes": self.notes,
                              "Imod": self.Imod
                          })
        return self.save_dict


    def calc_ramp(self):
        self.numpts = int(self.Imodspan/self.Imodstep)
        self.Imod = np.linspace(-self.Imodspan/2, self.Imodspan/2, self.numpts) # Squid current
        self.V = np.full((self.numpts, self.IV.numpts), np.nan)


    def do(self):
        self.calc_ramp() #easy way to clear self.V
        self.IV.V = self.IV.V*0

        self.param_prompt() # Check parameters

        for i in range(len(self.Imod)):
            self.IV.Imod = self.Imod[i]
            self.IV.do_IV()
            self.plot()
            self.axIV.clear()
            self.IV.plot(self.axIV)
            self.V[:][i] = self.IV.V
            self.fig.canvas.draw() #draws the plot; needed for %matplotlib notebook
        self.IV.daq.zero() # zero everything

        self.notes = input('Notes for this mod2D (q to quit without saving): ')
        if self.notes != 'q':
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

    def plot(self):
        '''
        Plot the 2D mod image
        '''
        if not hasattr(self, 'im'):
            self.setup_plot()
        plot_mpl.update2D(self.im, self.V)


    def save(self, savefig=True):
        '''
        Saves the mod2d object to json.
        Also saves the figure as a pdf, if wanted.
        '''

        self.tojson(get_todays_data_path(), self.filename)

        if savefig:
            self.fig.savefig(os.path.join(get_todays_data_path(), self.filename+'.pdf'), bbox_inches='tight')


    def setup_plot(self):
        '''
        Set up the figure. 2D mod image and last IV trace.
        '''
        self.fig, (self.axIV, self.ax2D) = plt.subplots(2,1,figsize=(7,7),gridspec_kw = {'height_ratios':[1, 3]})
        self.fig.suptitle(self.filename+'\n'+self.notes)
        ## Set up 2D plot
        self.im = plot_mpl.plot2D(self.ax2D,
                                self.IV.I*1e6,
                                self.Imod*1e6,
                                self.V,
                                xlabel=r'$I_{\rm{bias}} = V_{\rm{bias}}/R_{\rm{bias}}$ ($\mu \rm A$)',
                                ylabel = r'$I_{\rm{mod}} = V_{\rm{mod}}/R_{\rm{mod}}$ ($\mu \rm A$)',
                                clabel = r'$V_{\rm{squid}}$ $(\rm V)$',
                                fontsize=20
                            )
