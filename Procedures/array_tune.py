"""
# Limit the number of attempts @ each tuning step
# Figure out when resets are required
# Record traces when tuning is done
Add offset to lock point  (not just the mean)
"""
from matplotlib import pyplot as plt
import numpy as np
from ..Utilities.save import Measurement
from ..Procedures.daqspectrum import SQUIDSpectrum
from ..Procedures.mutual_inductance import MutualInductance2

class ArrayTune(Measurement):
    instrument_list = ["daq", "squidarray", "preamp"]
    _daq_inputs = ["saa", "test"]
    _daq_outputs = ["test"]
    def __init__(self,
                 instruments,
                 squid_bias,
                 squid_tol = 100e-3,
                 aflux_tol = 10e-3,
                 sflux_offset = 0.0,
                 aflux_offset = 0.0):
        """Given a lock SAA, tune the input SQUID and lock it.
        Args:
        instruments (dict): Dictionary of instruments
        squid_bias (float): Bias point for SQUID lock
        squid_tol (float): Allowed DC offset for the locked SQUID
        offset (float): Tune the lockpoint up/down on the SQUID characaristic.
        """
        super(ArrayTune, self).__init__(instruments=instruments)
        self.instruments = instruments
        self.squid_bias = squid_bias
        self.conversion = 10 # Conversion between mod current and voltage
        self.squid_tol = squid_tol
        self.aflux_tol = aflux_tol
        self.sflux_offset = sflux_offset
        self.aflux_offset = aflux_offset

    def acquire(self):
        """Ramp the modulation coil current and monitor the SAA response."""
        # Send TTL pulse on "test"
        data = {"test": 2*np.ones(2000)}
        # Record test
        ret = self.daq.send_receive(data, chan_in = ["saa", "test"],
                                    sample_rate=100000)
        # Zero the DAQ output
        self.daq.outputs["test"].V = 0
        return ret['t'], ret["test"], ret["saa"], 

    def tune_squid_setup(self):
        """Configure SAA for SQUID tuning."""
        self.squidarray.lock("Array")
        self.squidarray.S_flux_lim = 150
        self.squidarray.S_flux = 0
        self.squidarray.testInput = "S_flux"
        self.squidarray.testSignal = "On"
        self.squidarray.S_bias = self.squid_bias
        self.squidarray.sensitivity = "High"
        self.squidarray.reset()

    def tune_squid(self, attempts=5):
        """Tune the SQUID and adjust the DC SAA flux."""
        self.tune_squid_setup()
        self.char = self.acquire()
        error = np.mean(self.char[-1]) - self.aflux_offset
        if np.abs(error) < self.aflux_tol:
            return self.lock_squid()
        elif attempts == 0:
            print("could not tune array flux.")
            return False
        else:
            self.adjust("A_flux", error)
            return self.tune_squid(attempts = attempts-1)

    def lock_squid(self, attempts=5):
        """Lock the SQUID and adjust the DC SQUID flux."""
        self.squidarray.lock("Squid")
        self.squidarray.testSignal = "Off"
        self.squidarray.reset()
        ret = self.daq.monitor(["saa"], 0.01, sample_rate = 100000)
        error = np.mean(ret["saa"]) - self.sflux_offset
        print(error)
        if np.abs(error) < self.squid_tol:
            print("locked with {} attempts".format(5-attempts))
            return True
        elif attempts == 0:
            print("could not tune SQUID flux.")
            return False
        else:
            self.adjust("S_flux", error)
            return self.lock_squid(attempts - 1)

    def adjust(self, attr, error):
        """Adjust DC flux to center the trace @ 0 V."""
        value = getattr(self.squidarray, attr)
        if value + error * self.conversion < 0:
            # Force a jump by resetting
            setattr(self.squidarray, attr, value + 50)
        elif value + error * self.conversion > 150:
            setattr(self.squidarray, attr, 0)
        else:
            # Directly correct the offset
            setattr(self.squidarray, attr, value + self.conversion * error)
        self.squidarray.reset()

    def plot(self):
        fig, ax = plt.subplots(1,3,figsize=(12,4))
        # Plot the charactaristic
        ax[0].plot(self.char[1], self.char[2])
        ax[0].set_xlabel("Test Signal (V)")
        ax[0].set_ylabel("SAA Signal (V)", size="medium")

        # Plot the spectrum
        ax[2].loglog(self.spectrum.f,
                     self.spectrum.psdAve * self.spectrum.conversion)
        ax[2].set_xlabel("Frequency (Hz)")
        ax[2].set_title("PSD ($\mathrm{%s/\sqrt{Hz}}$)" % self.spectrum.units,
                        size="medium")
        
        # Plot the sweep
        self.sweep.ax = ax[1]
        self.sweep.plot()
        ax[1].set_ylabel("")
        ax[1].set_title("DC SQUID Signal ($\Phi_o$)",
                        size="medium")

    def run(self, save_appendedpath = ''):
        self.istuned = self.tune_squid()
        if self.istuned == False:
            return False
        self.preamp.filter = (1, 300000)
        self.squidarray.reset()
        self.spectrum = SQUIDSpectrum(self.instruments)
        self.spectrum.saa_status = self.squidarray.__dict__
        self.spectrum.run(save_appendedpath = save_appendedpath)
        plt.close()
        self.squidarray.sensitivity = "Medium"
        self.squidarray.reset()
        self.preamp.filter = (1, 300)
        self.preamp.gain = 1
        self.squidarray.reset()
        self.sweep = MutualInductance2(self.instruments,
                                       np.linspace(-1e-3, 1e-3, 1000),
                                       conversion = 1/1.44)
        self.sweep.saa_status = self.squidarray.__dict__
        self.sweep.run(save_appendedpath = save_appendedpath)
        plt.close()
        self.plot()
        return True
