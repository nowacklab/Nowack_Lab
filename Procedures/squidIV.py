""" Procedure to take an IV curve for a SQUID. By default, assumes -100 uA to 100 uA sweep (0.5 uA step) over a 2kOhm bias resistor and zero mod current. Can change these values when prompted. """

# TO DO:    - Try sweep vs individual points
#           - Build in acceleration to daq sweep to and from zero?
#           - Do up and down sweeps?

from IPython import display
import matplotlib.pyplot as plt
import numpy as np
import time, os
from datetime import datetime
from ..Utilities import dummy
from ..Instruments import nidaq, preamp
from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict


class SquidIV(Measurement):
    _chan_labels = ['squidout', 'modout', 'squidin', 'currentin']
    instrument_list = ['daq','preamp','montana','preamp_I']

    V = np.array([0]*2) # to make plotting happy with no real data
    I = np.array([0]*2)

    notes = ''

    def __init__(self, instruments={}, rate=9):
        '''
        Example: SquidIV({'daq': daq, 'preamp': preamp}, 0, 0, None, 90)
        To make an empty object, then just call SquidIV(). You can do this if you want to plot previously collected data.
        '''
        super().__init__()

        self.two_preamps = False

        self._load_instruments(instruments)

        if self.preamp_I is not None:
            self.two_preamps = True

        try:
            for pa in [self.preamp, self.preamp_I]:
                pa.gain = 5000
                pa.filter_mode('low',6)
                pa.filter = (0, rate) # Hz
                pa.dc_coupling()
                pa.diff_input()
            self.preamp_I.gain = 50 # was overloading
        except:
            pass # if we have no instruments, or maybe just one preamp

        self.rate = rate # Hz # measurement rate of the daq

        self.Rbias = 2000
        self.Rmeas = 0 # Ohm # determined by squid testing box
        self.Rbias_mod = 2e3 # Ohm # Inside SQUID testing box
        self.Imod = 0 # A # constant mod current

        self.Irampcenter = 0
        self.Irampspan = 200e-6 # A # Will sweep from -Irampspan/2 to +Irampspan/2
        self.Irampstep = 0.5e-6 # A # Step size

        self.calc_ramp()

        display.clear_output()


    def calc_ramp(self):
        self.numpts = int(self.Irampspan/self.Irampstep)
        Ibias = np.linspace(self.Irampcenter-self.Irampspan/2, self.Irampcenter+self.Irampspan/2, self.numpts) # Desired current ramp
        self.Vbias = Ibias*(self.Rbias+self.Rmeas) # SQUID bias voltage


    def do(self):
        self.param_prompt() # Check parameters

        self.do_IV()
        self.daq.zero() # zero everything

        self.setup_plots()
        self.plot(dvdi = False)
        self.fig.canvas.draw() #draws the plot; needed for %matplotlib notebook

        self.notes = input('Notes for this IV (r to redo, q to quit): ')
        if self.notes == 'r':
            self.notes = ''
            display.clear_output()
            self.do()
        elif self.notes != 'q':
            self.ax.set_title(self.filename+'\n'+self.notes)
            self.save()


    def do_IV(self):
        """ Wrote this for mod2D so it doesn't plot """
        self.daq.outputs['modout'].V = self.Imod*self.Rbias_mod # Set mod current
        # Collect data
        in_chans = ['squidin','currentin']
        output_data, received = self.daq.sweep({'squidout': self.Vbias[0]},
                                               {'squidout': self.Vbias[-1]},
                                               chan_in=in_chans,
                                               sample_rate=self.rate,
                                               numsteps=self.numpts
                                           )
        self.V = np.array(received['squidin'])/self.preamp.gain
        if self.two_preamps:
            self.I = np.array(received['currentin'])/self.preamp_I.gain/self.Rmeas # Measure current from series resistor
        else:
            self.I = self.Vbias/(self.Rbias + self.Rmeas) # estimate current by assuming Rbias >> Rsquid

    def param_prompt(self):
        """ Check and confirm values of parameters """
        correct = False
        while not correct:
            for param in ['rate', 'Rbias', 'Rmeas', 'Rbias_mod', 'Imod', 'Irampspan', 'Irampcenter', 'Irampstep']:
                print(param, ':', getattr(self, param))
            for paramamp in ['gain','filter']:
                print('preamp', paramamp, ':', getattr(self.preamp, paramamp))
                if self.two_preamps:
                    print('preamp_I', paramamp, ':', getattr(self.preamp_I, paramamp))

            if self.rate >= self.preamp.filter[1]:
                print("You're filtering out your signal... fix the preamp cutoff\n")
            if self.two_preamps:
                if self.rate >= self.preamp_I.filter[1]:
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

    def plot(self, ax=None, ax2=None, dvdi = True):
        if ax == None: # if plotting on Mod2D's axis
            super().plot()
            ax = self.ax
            ax2 = ax.twinx()

        ax.plot(self.I*1e6, self.V, 'k-')
        ax.set_title(self.filename+'\n'+self.notes) # NEED DESCRIPTIVE TITLE
        if self.two_preamps:
            ax.set_xlabel(r'$I_{\rm{bias}} = V_{\rm{meas}}/R_{\rm{meas}}$ ($\mu \rm A$)', fontsize=20)
        else:
            ax.set_xlabel(r'$I_{\rm{bias}} = V_{\rm{bias}}/R_{\rm{bias}}$ ($\mu \rm A$)', fontsize=20)
        ax.set_ylabel(r'$V_{\rm{squid}}$ (V)', fontsize=20)
        ax.ticklabel_format(style='sci', axis='y', scilimits=(-3,3))

        ## To plot dVdI
        if (dvdi == True):
            if ax2 is not None:
                dx = np.diff(self.I)[0]*3 # all differences are the same, so take the 0th. Made this 3 times larger to accentuate peaks
                dvdi = np.gradient(self.V, dx)
                ax2.plot(self.I*1e6, dvdi, 'r-')
                ax2.set_ylabel(r'$dV_{squid}/dI_{bias}$ (Ohm)', fontsize=20, color='r')
                for tl in ax2.get_yticklabels():
                    tl.set_color('r')

        if self.fig is not None:
            self.fig.tight_layout()
        return ax


    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
