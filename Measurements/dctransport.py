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

class RvsT_Montana_Keithley(Measurement):
    instrument_list = ['montana', 'keithley']
    something = 'T'
    something_units = 'K'

    def __init__(self, instruments = {}, Ibias=100, Tend = 4.5, delay=5, numavg=5):
        '''
        Measurement will test voltage at +Ibias and -Ibias uA (changing instantaneously!)
        Keithley in 4-wire mode.
        Ibias: current bias (uA).
        Tend: target temperature (when to stop taking data)
        delay: time between measurements (seconds)
        numavg: number of averages
        '''
        super().__init__(instruments=instruments)

        self.Ibias = Ibias*1e-6
        self.Tend = Tend
        self.delay = delay
        self.numavg = numavg

        self.Vp = np.array([])
        self.Vz = np.array([])
        self.Vn = np.array([])
        self.Ra = np.array([]) # (Vp-Vz)/I
        self.Rb = np.array([]) # (Vz-Vn)/I
        self.Rc = np.array([]) # (Vp-Vn)/(2I)
        self.T = np.array([])



    def do(self, plot=True):
        while self.montana.temperature['platform'] > self.Tend:
            time.sleep(self.delay)

            self.T = np.append(self.T, self.montana.temperature['platform'])

            self.keithley.Iout = 0
            self.Vz = np.append(self.Vz, self.get_avg_voltage())

            self.keithley.Iout = self.Ibias
            self.Vp = np.append(self.Vp, self.get_avg_voltage())

            self.keithley.Iout = -self.Ibias
            self.Vn = np.append(self.Vn, self.get_avg_voltage())

            self.keithley.Iout = 0

            self.Ra = np.append(self.Ra, (self.Vp[-1] - self.Vz[-1])/self.Ibias)
            self.Rb = np.append(self.Rb, (self.Vz[-1] - self.Vn[-1])/self.Ibias)
            self.Rc = np.append(self.Rc, (self.Vp[-1] - self.Vn[-1])/self.Ibias/2)

            self.plot()

    def get_avg_voltage(self):
        V = 0
        for i in range(self.numavg):
            V += self.keithley.V
        return V / self.numavg


    def plot_update(self):
        self.la.set_xdata(self.T)
        self.lb.set_xdata(self.T)
        self.lc.set_xdata(self.T)
        self.la.set_ydata(self.Ra)
        self.lb.set_ydata(self.Rb)
        self.lc.set_ydata(self.Rc)

        self.ax.relim()
        self.ax.autoscale_view()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.la = self.ax.plot(self.T, self.Ra, label = '+')[0]
        self.lb = self.ax.plot(self.T, self.Rb, label = '-')[0]
        self.lc = self.ax.plot(self.T, self.Rc, label = 'full')[0]
        self.ax.set_xlabel('Temperature (K)')
        self.ax.set_ylabel('Resistance (Ohm)')

        l = self.ax.legend(loc='best')
