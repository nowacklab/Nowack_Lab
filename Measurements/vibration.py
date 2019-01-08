import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time

from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict
from ..Procedures.daqspectrum import AnnotatedSpectrum


class Vibration(Measurement):
    """
    Record spectra for vibration analysis
    """

    instrument_list=['daq',
                     'lockin_cap',
                     'lockin_squid',
                     'preamp',
                     'squidarray',
                     'piezos'
                     ]

    def __init__(self, plane, CAP_I,
                 instruments={},
                 xs = [],
                 ys = [],
                 scanheight = 30,
                 measure_time=30,
                 measure_freq=256000,
                 averages=6
                ):
        """
        """
        super().__init__(instruments=instruments)

        for arg in ['plane',
                    'xs',
                    'ys',
                    'scanheight',
                    'measure_time',
                    'measure_freq',
                    'averages',
                    'CAP_I',
                    'instruments'
                   ]:
            setattr(self,arg,eval(arg))

    #def __getstate__(self):
    #    return {'gain': self.gain,
    #            
    #            }
        
    def do(self):
        """
        """
        self.freqs   = []
        self.psdaves = []
        self.filenames=[]
        self.positions=[]

        self.X,self.Y = np.meshgrid(self.xs,self.ys)
        self.Z        = self.plane.plane(self.X,self.Y)-self.scanheight
        self.dc       = np.zeros(self.Z.shape)
        self.cap      = np.zeros(self.Z.shape)
        self.indexes  = np.zeros(self.Z.shape)

        self.gain = self.preamp.gain
        
        y_index = 0
        x_index = 0
        lastfig = 0
        for y in self.ys:
            for x in self.xs:
                self.piezos.sweep(self.piezos.V, 
                        {'x':x, 
                         'y':y, 
                         'z':self.Z[y_index][x_index]
                         }
                )
                self.positions.append( 
                            [self.piezos.V['x'], 
                             self.piezos.V['y'], 
                             self.piezos.V['z']]
                )
                self.cap[y_index][x_index] = self.lockin_cap.R

                spectrum = AnnotatedSpectrum(self.CAP_I,
                        instruments=self.instruments,
                        measure_time = self.measure_time,
                        measure_freq = self.measure_freq,
                        averages     = self.averages
                )
                spectrum.squidspectra()
                spectrum.run()

                self.dc[y_index][x_index] = np.mean(spectrum.V)


                if lastfig != 0:
                    plt.close(lastfig)

                lastfig = spectrum.fig

                self.filenames.append(spectrum.filename)
                self.psdaves.append(spectrum.psdAve)
                self.indexes[y_index][x_index] = y_index*len(self.xs) + x_index

                if (x_index+y_index == 0):
                    self.freqs = spectrum.f
                    self.conversion = spectrum.conversion

                print("{0}/{1}: [x,y,z]=[{2:2.2f},{3:2.2f},{4:2.2f}]".format(
                        y_index*len(self.xs) + x_index,
                        len(self.xs)*len(self.ys),
                        *self.positions[-1]))

                x_index += 1
            x_index=0
            y_index += 1

        self.freqs = np.array(self.freqs)
        self.psdaves = np.array(self.psdaves)
        self.positions = np.array(self.positions)

        self.plot()
        


            
    def setup_plots(self):
        """
        """
        pass

    def plot(self):
        """
        """
        self.fig,self.ax = plt.subplots()
        image = self.ax.imshow(self.dc/self.gain*self.conversion,origin='lower',
                            extent=[self.X.min(), self.X.max(),
                                    self.Y.min(), self.Y.max()])
        cbar = plt.colorbar(image)
        cbar.set_label(r'dc ($\phi_0$)', rotation=270, labelpad=12)
        self.ax.set_xlabel('X position (V)')
        self.ax.set_ylabel('Y position (V)')

        self.fig.tight_layout()
        self.fig.canvas.draw()
        plt.show()

