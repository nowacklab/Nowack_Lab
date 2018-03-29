import re, time, numpy as np, matplotlib.pyplot as plt
from ..Utilities.save import Measurement

class DAQ_IV(Measurement):
    _daq_inputs = ['V1'] # e.g. V1, V2, ... provide an arbitrary number
    _daq_outputs = ['out']
    instrument_list = ['daq','ppms']

    def __init__(self, instruments={}, Vstart = -1, Vend = 1, Vstep=.01, Rbias=1e3, rate=9, bipolar=False):
        '''
        Vstart: Starting voltage (V)
        Vend: Ending voltage (V)
        Vstep: Step size (V)
        Rbias: size of bias resistor (Ohm). Assuming Ibias = Vout/Rbias
        rate: measurement rate (Hz)
        bipolar: sweep up and then back down?
        '''
        self.daq = instruments['daq']
        self.setup_inputs()

        super().__init__(instruments=instruments)

        self.Vstart = Vstart
        self.Vend = Vend
        self.Vstep = Vstep
        self.Rbias = Rbias

        self.rate = rate # Hz # measurement rate of the daq
        self.bipolar = bipolar

        self.V = {i: np.array([]) for i in self._daq_inputs}
        self.Vout = np.array([])

        print('Ibias from %.4f to %.4f mA' %(Vstart/Rbias*1e3, Vend/Rbias*1e3))

    def do(self):
        self.numpts = round(abs(self.Vend-self.Vstart)/self.Vstep)+1
        self.Vout = np.linspace(self.Vstart, self.Vend, self.numpts)

        self.daq.sweep({'out': 0},
           {'out': self.Vout[0]},
           chan_in=self._daq_inputs,
           sample_rate=self.rate,
           numsteps=int(self.numpts/2)
        )

        output_data, received = self.daq.sweep({'out': self.Vout[0]},
                                       {'out': self.Vout[-1]},
                                       chan_in=self._daq_inputs,
                                       sample_rate=self.rate,
                                       numsteps=self.numpts
                                   )

        for inp in self._daq_inputs:
            self.V[inp] = np.array(received[inp])


        self.plot()

        if not self.bipolar:

            self.daq.sweep({'out': self.Vout[-1]},
               {'out': 0},
               chan_in=self._daq_inputs,
               sample_rate=self.rate,
               numsteps=int(self.numpts/2)
            )
        else: # if bipolar
            output_data, received = self.daq.sweep({'out': self.Vout[-1]},
                                           {'out': self.Vout[0]},
                                           chan_in=self._daq_inputs,
                                           sample_rate=self.rate,
                                           numsteps=self.numpts
                                       )

            for inp in self._daq_inputs:
                self.Vout = np.append(self.Vout, self.Vout[::-1])
                self.V[inp] = np.append(self.V[inp], np.array(received[inp]))

            self.plot()

            self.daq.sweep({'out': self.Vout[0]},
               {'out': 0},
               chan_in=self._daq_inputs,
               sample_rate=self.rate,
               numsteps=int(self.numpts/2)
            )

    def plot(self):
        super().plot()

        for inp, line in self.lines.items():
            line.set_xdata(self.Vout/self.Rbias*1e3)
            line.set_ydata(self.V[inp]*1e3)

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def plot_diff(self, i, j):
        '''
        Plot the difference between two voltage channel numbers i,j
        '''
        fig, ax = plt.subplots()
        ax.set_xlabel('V_{out}/R_{bias} (mA)', fontsize=20)
        ax.set_ylabel('Voltage difference %i-%i (mV)' %(i,j), fontsize=20)
        ax.plot(self.Vout/self.Rbias*1e3, (self.V['V%i' %i] - self.V['V%i' %j])*1e3)

    def setup_inputs(self):
        '''
        Search for inputs named 'V*', where * is an integer used to label pin numbers.
        self._daq_inputs will be modified to be a list of these inputs.
        '''
        self._daq_inputs = []
        for label, inp in self.daq.inputs.items():
            if re.match('^V[0-9]+$', label):
                self._daq_inputs.append(label)

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('V_{out}/R_{bias} (mA)', fontsize=20)
        self.ax.set_ylabel('Voltage (mV)', fontsize=20)

        ## plot all the resistances
        self.lines = {}
        for inp in self._daq_inputs:
            line = self.ax.plot(self.Vout/self.Rbias*1e3, self.V[inp]*1e3)
            self.lines[inp] = line[0]

        l = self.ax.legend([i for i in self._daq_inputs], loc='best')
        self.ax.set_title(self.filename)
