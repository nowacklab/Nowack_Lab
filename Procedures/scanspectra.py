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
from ..Procedures import DaqSpectrum
from ..Utilities.utilities import AttrDict

class Scanspectra(Measurement):
    _daq_inputs = ['dc','cap','acx','acy'] # DAQ channel labels expected by this class
    instrument_list = ['piezos','montana','squidarray','preamp','lockin_squid','lockin_cap','atto','daq']

    Vavg = AttrDict({
        chan: np.nan for chan in _daq_inputs
    })

    V = np.array([])

    def __init__(self, instruments = {}, plane = None, span=[800,800],
                        center=[0,0], numpts=[20,20], scanheight=15,
                        monitor_time=1, sample_rate=10000, num_averages=1):
        super().__init__(instruments=instruments)

        self.monitor_time = monitor_time
        self.sample_rate = sample_rate
        self.span = span
        self.center = center
        self.numpts = numpts
        if plane is None:
            plane = Planefit()
        self.plane = plane

        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? \'q\' to quit.')
            if inp == 'q':
                raise Exception('Terminated by user')
        self.scanheight = scanheight

        x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(x, y)
        try:
            self.Z = self.plane.plane(self.X, self.Y) - self.scanheight
        except:
            print('plane not loaded... no idea where the surface is without a plane!')

        shape = self.X.shape + (int(sample_rate*monitor_time),) # 3rd dimension is number of samples long
        self.V = np.full(shape, np.nan)
        self.t = np.full(shape[2], np.nan)

        ## FFT takes a different number of points; see DaqSpectrum class
        shape = self.X.shape +  (int(sample_rate*monitor_time/2+1),)
        self.psd = np.full(shape, np.nan)
        self.f = np.full(shape[2], np.nan)

        for chan in self._daq_inputs:
            self.Vavg[chan] = np.full(self.X.shape, np.nan) #initialize arrays

        self.daqspectrum = DaqSpectrum(instruments, monitor_time, sample_rate, num_averages) # object that handles taking spectra


    def do(self):
        self.setup_preamp()

        for i in range(self.X.shape[0]):
            self.piezos.x.check_lim(self.X[i,:])
            self.piezos.y.check_lim(self.Y[i,:])
            self.piezos.z.check_lim(self.Z[i,:])

        for i in range(self.X.shape[0]):
            for j in range(self.Y.shape[1]):
                print(self.X[i,j], self.Y[i,j])
                self.piezos.V = {'x': self.X[i,j], 'y': self.Y[i,j], 'z': self.Z[i,j]}
                self.squidarray.reset()
                time.sleep(0.5)

#                 data = self.daq.monitor('dc', self.monitor_time, self.sample_rate)

#                 self.V[i,j] = data['dc']
#                 self.Vdc[i,j] = data['dc'].mean()

                self.psd[i,j] = self.daqspectrum.get_spectrum()
                self.V[i,j] = self.daqspectrum.V
                if np.isnan(self.t[0]): #we haven't recorded these yet
                    self.t = self.daqspectrum.t
                    self.f = self.daqspectrum.f

                # just single data points, like a single scan
                self.Vavg['dc'][i,j] = self.daqspectrum.V.mean()
                for chan in self._daq_inputs:
                    if chan != 'dc':
                        self.Vavg[chan][i,j] = self.daq.inputs[chan].V

        self.piezos.V = 0
        del self.daqspectrum


    def setup_preamp(self):
        self.preamp.gain = 1
        self.preamp.filter = (0, 100e3)
        self.preamp.dc_coupling()
        self.preamp.diff_input(False)
        self.preamp.filter_mode('low',12)
