from ..Utilities.save import Measurement
from matplotlib import pyplot as plt
import numpy as np
import time

def compute_I(I1, I2, step):
    num_steps = int(abs(I1 - I2) / step)
    return np.linspace(I1, I2, num_steps)


class Keithley_Sweep(Measurement):
    """Take IVs with DAQ +Preamp and Keithley2400 as source"""
    instrument_list = ['daq', 'preamp', 'lakeshore', 'keithley']
    _daq_inputs = ['dc']
    def __init__(self, instruments, I_start, I_end, step, rate):
        super().__init__(instruments=instruments)
        for arg in ['I_start',
                    'I_end',
                    'step',
                    'rate']:
            setattr(self, arg, eval(arg))
        self.V =   {"start": [],
                    "sweep": [],
                    "end" : []}
        self.I = {"start": [],
                    "sweep": [],
                    "end": []}


    def do(self):
        """
        """
        self.Istart_sweep = compute_I(self.keithley.I, self.I_start, self.step)
        self.Isweep = compute_I(self.I_start, self.I_end, self.step)
        self.Iend_sweep = compute_I(self.I_end, 0, self.step)

        # Sweep current to starting position
        self.sweep(self.Istart_sweep, "start")

        # Sweep from start to end
        self.sweep(self.Isweep, "sweep")

        # Sweep back to I = 0
        self.sweep(self.Iend_sweep, "end")

        # Convert data to np arrays
        for key in self.V.keys():
            self.V[key] = np.array(self.V[key])
            self.I[key] = np.array(self.I[key])
    def sweep(self, Is, key):
        """
        Sweep the keithley over a range of currents while recording the inputs 
        on the DAQ
        """
        for I in Is:
            self.keithley.Iout = I
            time.sleep(self.step/self.rate)
            self.V[key].append(self.daq.inputs['dc'].V / self.preamp.gain)
            self.I[key].append(self.keithley.I)

    def plot(self):
        """
        """
        fig, ax = plt.subplots()
        for key in ["start", "sweep", "end"]:
            ax.plot(self.I[key], self.V[key])
        ax.set_title(self.timestamp, size="medium")
        ax.set_xlabel("Current (A)")
        ax.set_ylabel("Voltage (V)")




class DAQ_Sweep(Measurement):
    """Take IVs with the DAQ

    Sweeps out a bias current while monitoring the voltage over as sample. Sweep
    current down to I_start, sweeep up to I_end and then sweep the bias back to 
    0

    TODO
    startup effects / waiting before collecting data
    checking if we start @ 0 bias

    """
    instrument_list = ['daq', 'preamp', 'lakeshore']
    _daq_inputs = ['voltage']
    _daq_outputs = ['bias']
    _max_step = 0.1e-6 # Amp
    def __init__(self, instruments, I_start, I_end, Rbias, rate, numpts):
        super().__init__(instruments=instruments)
        for arg in ['I_start',
                    'I_end',
                    'Rbias',
                    'rate',
                    'numpts']:
            setattr(self, arg, eval(arg))
        self.Is = np.linspace(I_start, I_end, numpts)
        self.wait = 1/rate
        self.Vs = []

    def do(self):
        """
        """
        # Sweep DAQ output to 0
        _ = self.daq.sweep({'bias': self.daq.outputs['bias'].V},
                            {'bias': 0},
                            chan_in = None,
                            sample_rate = 1000,
                            numsteps = 1000)

        # Sweep DAQ to start of sweep
        self.data1, self.received1 = self.daq.sweep({'bias': 0},
                                                    {'bias': self.I_start * self.Rbias},
                                                    chan_in = self._daq_inputs,
                                                    sample_rate = 1000,
                                                    numsteps = 1000)
        time.sleep(1.)

        for I in self.Is:
            # Adjust the DAQ voltage to the next point
            _, _ = self.daq.sweep({"bias": self.daq.outputs["bias"].V},
                                  {"bias": I * self.Rbias},
                                  sample_rate = 1000,
                                  numsteps = 1000)
            time.sleep(self.wait)
            ret = self.daq.monitor(["voltage"],
                                   duration = 1,
                                   sample_rate = 1000)
            self.Vs.append(np.mean(ret["voltage"])/self.preamp.gain)
            

        # Sweep DAQ back to 0
        self.data3, self.received3 = self.daq.sweep({'bias': self.I_end * self.Rbias},
                                                    {'bias': 0},
                                                    chan_in = self._daq_inputs,
                                                    sample_rate = 1000,
                                                    numsteps = 1000)
        

        self.gain = self.preamp.gain
        #self.T = self.lakeshore.T




class DAQ_Transport(Measurement):
    """Take IVs with the DAQ

    Sweeps out a bias current while monitoring the voltage over as sample. Sweep
    current down to I_start, sweeep up to I_end and then sweep the bias back to 
    0

    TODO
    startup effects / waiting before collecting data
    checking if we start @ 0 bias

    """
    instrument_list = ['daq', 'preamp', 'lakeshore']
    _daq_inputs = ['voltage']
    _daq_outputs = ['bias']
    _max_step = 0.1e-6 # Amp
    def __init__(self, instruments, I_start, I_end, Rbias, rate, numpts):
        super().__init__(instruments=instruments)
        for arg in ['I_start',
                    'I_end',
                    'Rbias',
                    'rate',
                    'numpts']:
            setattr(self, arg, eval(arg))

    def do(self):
        """
        """
        # Sweep DAQ output to 0
        _ = self.daq.sweep({'bias': self.daq.outputs['bias'].V},
                            {'bias': 0},
                            chan_in = None,
                            sample_rate = 100,
                            numsteps = int(self.numpts))

        # Sweep DAQ to start of sweep
        self.data1, self.received1 = self.daq.sweep({'bias': 0},
                                            {'bias': self.I_start * self.Rbias},
                                            chan_in = self._daq_inputs,
                                            sample_rate = self.rate,
                                            numsteps = int(self.numpts/2))

        # Sweep DAQ to end of sweep
        self.data2, self.received2 = self.daq.sweep({'bias': self.I_start * self.Rbias},
                                            {'bias': self.I_end * self.Rbias},
                                            chan_in = self._daq_inputs,
                                            sample_rate = self.rate,
                                            numsteps = self.numpts)

        # Sweep DAQ back to 0
        self.data3, self.received3 = self.daq.sweep({'bias': self.I_end * self.Rbias},
                                            {'bias': 0},
                                            chan_in = self._daq_inputs,
                                            sample_rate = self.rate,
                                            numsteps = int(self.numpts/2))
        

        self.gain1 = self.preamp.gain
        #self.T = self.lakeshore.T


    def fit(self):
        """Fit the long portion of the sweep."""
        fit, res, *other = np.polyfit(self.data2['bias']/self.Rbias,
                                      self.received2['voltage']/self.gain1,
                                      deg=1,
                                      full=True)
        self.res = res
        self.R = fit[0]

    def plot(self):
        """
        """
        fig, ax = plt.subplots()
        ax.plot(self.data1['bias']/self.Rbias, self.received1['voltage']/self.preamp.gain, ".")
        ax.plot(self.data2['bias']/self.Rbias, self.received2['voltage']/self.preamp.gain, ".")
        ax.plot(self.data3['bias']/self.Rbias, self.received3['voltage']/self.preamp.gain, ".")
        ax.set_xlabel("Bias Current (A)")
        ax.set_ylabel("Voltage (V)")

    def plot_both(self, gain2):
        """
        """
        fig, ax = plt.subplots(1,2,figsize=(8,4))
        ax[0].plot(self.data1['bias']/self.Rbias, self.received1['voltage']/self.preamp.gain, ".")
        ax[0].plot(self.data2['bias']/self.Rbias, self.received2['voltage']/self.preamp.gain, ".")
        ax[0].plot(self.data3['bias']/self.Rbias, self.received3['voltage']/self.preamp.gain, ".")
        ax[0].set_xlabel("Current (A)")
        ax[0].set_ylabel("Voltage (V)")
        ax[0].set_title(self.timestamp, size="medium")

        ax[1].plot(self.data1['bias']/self.Rbias, self.received1['voltage2']/gain2)
        ax[1].plot(self.data2['bias']/self.Rbias, self.received2['voltage2']/gain2)
        ax[1].plot(self.data3['bias']/self.Rbias, self.received3['voltage2']/gain2)

