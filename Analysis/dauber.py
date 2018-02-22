'''
Functions to make plots from http://aip.scitation.org/doi/10.1063/1.4919897
Plotting Hall voltage and sensitivity versus gate voltage (density)
'''
import matplotlib.pyplot as plt

class DauberPlots():

    def __init__(self, Vg, Vxx, VHneg, VHzero, VHpos, Idrainneg, Idrainzero, Idrainpos, B, Vbias):
        '''
        Vg: array of gate voltages (V)
        Vxx: array of longitudinal voltage values at zero field (V)
        VHneg: array of Hall voltages at negative field (V)
        VHzero: array of Hall voltages at zero field (V)
        VHpos: array of Hall voltages at positive field (V)
        Idrainneg: array of drain current values at negative field (A)
        Idrainzero: array of drain current values at zero field (A)
        Idrainpos: array of drain current values at positive field (A)
        B: max/min field (T)
        Vbias: bias voltage (mV)
        '''
        self.__dict__.update(locals()) # cute way to set attributes from arguments
        del self.self # but includes self, get rid of this!


    def dauber1d(self):
        '''
        Conductance versus gate voltage
        '''
        fig, ax = plt.subplots()
        ax.plot(self.Vg, self.Idrainzero/self.Vxx*1000)
        ax.set_xlabel('Vg (V)')
        ax.set_ylabel('Conductivity (mS)');

    def dauber2a(self):
        '''
        Hall voltage versus density at three fields: -B, 0, B
        '''

        fig, ax = plt.subplots()

        ax.plot(self.Vg, self.VHneg*1000, label='-%i mT' %(self.B*1000))
        ax.plot(self.Vg, self.VHzero*1000, label='0 mT')
        ax.plot(self.Vg, self.VHpos*1000, label='%i mT' %(self.B*1000))
        ax.set_xlabel('Vg (V)')
        ax.set_ylabel('Hall voltage (mV)');
        # ax.set_xlim(-10,10)
        # ax.set_ylim(-.2,.2)
        ax.text(0.98, 0.98,'V$_{bias}$ = %s mV' %self.Vbias,
             horizontalalignment='right',
             verticalalignment='top',
             transform = ax.transAxes)
        ax.legend(loc='lower right')

    def dauber2b(self):
        '''
        Voltage sensitivity versus gate voltage.
        Zero-field trace subtracted for symmetrization.

        S_V = 1/Vb * abs(B/VH)
        '''
        Vpos = self.VHpos - self.VHzero
        Vneg = self.VHneg - self.VHzero

        fig, ax = plt.subplots()
        ax.plot(self.Vg, 1/(self.Vbias*1e-3*abs(self.B/Vpos)), label = '+B')
        ax.plot(self.Vg, 1/(self.Vbias*1e-3*abs(self.B/Vneg)), label = '-B')

        ax.set_xlabel('Vg (V)')
        ax.set_ylabel('S$_V$ (V/VT)');

        ax.legend(loc='lower right')

    def dauber2c(self):
        '''
        Current sensitivity versus gate voltage.
        Zero-field trace subtracted for symmetrization.

        S_V = 1/Id * abs(B/VH)
        '''
        Vpos = self.VHpos - self.VHzero
        Vneg = self.VHneg - self.VHzero

        fig, ax = plt.subplots()
        ax.plot(self.Vg, 1/(self.Idrainpos*abs(self.B/Vpos)), label = '+B')
        ax.plot(self.Vg, 1/(self.Idrainneg*abs(self.B/Vneg)), label = '-B')

        ax.set_xlabel('Vg (V)')
        ax.set_ylabel('S$_I$ (V/AT)');

        ax.legend(loc='lower right')
