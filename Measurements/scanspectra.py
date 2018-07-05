import numpy as np
from numpy.linalg import lstsq
from .planefit import Planefit
import time, os
from datetime import datetime
from scipy.interpolate import interp1d as interp
import matplotlib.pyplot as plt
from IPython import display
from numpy import ma
from ..Utilities.plotting import plot_mpl
from ..Instruments import piezos, montana, squidarray
from ..Utilities.save import Measurement
from ..Utilities import conversions
from ..Procedures.daqspectrum import SQUIDSpectrum
from ..Utilities.utilities import AttrDict

class Scanspectra(Measurement):
    _daq_inputs = ['dc'] # DAQ channel labels expected by this class
    instrument_list = ['piezos','montana','squidarray','preamp','lockin_squid','lockin_cap','atto','daq']

    Vavg = AttrDict({
        chan: np.nan for chan in _daq_inputs
    })

    V = np.array([])
    psdAve = np.array([])

    def __init__(self, instruments = {}, plane = None, span=[800,800],
                        center=[0,0], numpts=[20,20], scanheight=15,
                        monitor_time=1, sample_rate=10000, num_averages=1):
        super().__init__(instruments=instruments)
        self.instruments = instruments

        # Define variables specified in init
        self.monitor_time = monitor_time
        self.sample_rate = sample_rate
        self.num_averages = num_averages
        self.span = span
        self.center = center
        self.numpts = numpts
        self.plane = plane
        self.scanheight = scanheight

        # Create a grid of points where a spectrum is taken.
        x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(x, y)
        try:
            self.Z = self.plane.plane(self.X, self.Y) - self.scanheight
        except:
            print('plane not loaded... no idea where the surface is without a plane!')


    def do(self):
        self.setup_preamp()

        for i in range(self.X.shape[0]):
            self.piezos.x.check_lim(self.X[i,:])
            self.piezos.y.check_lim(self.Y[i,:])
            self.piezos.z.check_lim(self.Z[i,:])

        # Move to each point on the grid and take a spectrum
        for i in range(self.X.shape[0]):
            for j in range(self.Y.shape[1]):
                print(self.X[i,j], self.Y[i,j])
                self.piezos.V = {'x': self.X[i,j], 'y': self.Y[i,j], 'z': self.Z[i,j]}
                self.squidarray.reset()
                time.sleep(0.5)
                # Take the spectrum
                spectrum = SQUIDSpectrum(self.instruments,
                                         self.monitor_time,
                                         self.sample_rate,
                                         self.num_averages)
                spectrum.do()
                self.psdAve = np.append(self.psdAve, spectrum.psdAve)
                self.V = np.append(self.V, spectrum.V)
                plt.close()
        # All spectra are identical - save the frequencies and times only once
        self.f = spectrum.f
        self.t = spectrum.t

    def setup_preamp(self):
        self.preamp.dc_coupling()
        self.preamp.diff_input(False)
        self.preamp.filter_mode('low',12)

    def plot(self):
        self.fig, self.ax = plt.subplots(figsize=(6,6))
        freq_avg = np.mean(self.psdAve, axis=2)
        extent = [self.X.min(), self.X.max(), self.Y.min(), self.Y.max()]
        self.im = self.ax.imshow(freq_avg, extent=extent)
