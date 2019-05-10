import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time
from importlib import reload

import Nowack_Lab.Utilities.save
reload(Nowack_Lab.Utilities.save)
from Nowack_Lab.Utilities.save import Measurement

import Nowack_Lab.Utilities.utilities
reload(Nowack_Lab.Utilities.utilities)
from Nowack_Lab.Utilities.utilities import AttrDict
from Nowack_Lab.Utilities.utilities import f_of_fft

import Nowack_Lab.Procedures.daqspectrum
reload(Nowack_Lab.Procedures.daqspectrum)
from Nowack_Lab.Procedures.daqspectrum import AnnotatedSpectrum

import Nowack_Lab.Utilities.dataset
reload(Nowack_Lab.Utilities.dataset)
from Nowack_Lab.Utilities.dataset import Dataset

import Nowack_Lab.Utilities.datasaver
reload(Nowack_Lab.Utilities.datasaver)
from Nowack_Lab.Utilities.datasaver import Saver

import Nowack_Lab.Utilities.welch
reload(Nowack_Lab.Utilities.welch)
from Nowack_Lab.Utilities.welch import Welch


class Spectra_Image():
    '''
    Record spectra for vibration analysis, saving with alexsave
    '''

    instrument_list=['daq',
                     'lockin_cap',
                     'lockin_squid',
                     'preamp',
                     'squidarray',
                     'piezos'
                     ]


    def __init__(self, plane, 
                 instruments={},
                 xs = [],
                 ys = [],
                 scanheight = 30,
                 measure_time=5,
                 measure_freq=256000,
                 accel_chs=[],
                 accel_names=[],
                 fft_fspace=1,
                ):
        '''
        Params:
            plane (Planescan): plane to follow
            instruments (dict}: dictionary of instruments
            xs (ndarray): piezo x positions in volts
            ys (ndarray): piezo y positions in volts
            scanheight (float): scanheight in volts
            measure_time (float): measure time in seconds
            measure_freq (float): measure frequency in Hz
        '''


        self.daq = instruments['daq']
        self.preamp = instruments['preamp']
        self.saa = instruments['saa']
        self.lockin_cap = instruments['lockin_cap']
        self.piezos = instruments['piezos']

        self.plane = plane
        self.saver = Saver(name='Spectra_Image')

        self.compression = 'gzip'
        self.compression_opts=9
        self.chunks=True

        self.scanheight = scanheight
        self.measure_time = measure_time
        self.measure_freq = measure_freq

        self.accel_chs = accel_chs
        self.accel_names = accel_names

        self.xs = np.asarray(xs)
        self.ys = np.asarray(ys)

        if fft_fspace <= 1/measure_time:
            print('Error: fft_fspace too small for measure_time')
            fft_fspace = 2/measure_time

        spectralen = self.measure_freq * self.measure_time
        #f = f_of_fft(measure_time, measure_freq, fft_fspace)

        def emptydata(datalen=None):
            shape = (self.xs.shape[0],
                     self.ys.shape[0] 
                    )
            if datalen is not None:
                shape = shape + datalen

            return np.full(shape, np.nan)

        def makedim(name, extras=[]):
            self.saver.make_dim(name, 0, 'x', '/x/', 'X (V)')
            self.saver.make_dim(name, 1, 'y', '/y/', 'Y (V)')

            if extras is [] or extras is None:
                return
            i = 2

            for ex in extras:
                self.saver.make_dim(name, i, ex[0], ex[1], ex[2])
                i += 1

        # dimenions / coordinates
        self.saver.append('/x/', np.asarray(xs))
        self.saver.create_attr('/x/', 'units', 'Volts')

        self.saver.append('/y/', np.asarray(ys))
        self.saver.create_attr('/y/', 'units', 'Volts')

        self.saver.append('/t_spectra/', 
                          np.linspace(0, self.measure_freq, 
                                      spectralen)
                          )
        self.saver.create_attr('/t_spectra/', 'units', 'seconds')

        #self.saver.append('/f/', f)
        #self.saver.create_attr('/f/', 'units', 'Hz')

        self.saver.append('/pos_names/', ['X', 'Y', 'Z'])
        self.saver.create_attr('/pos_names/', 'units', 'Position Names')

        self.saver.append('/accel_names/', accel_names)
        self.saver.create_attr('/accel_names/', 'units', 'Accelerometer Names')

        # Data
        self.saver.append('/timetraces/', 
                         emptydata((spectralen,)),
                         chunks=self.chunks,
                         compression=self.compression,
                         compression_opts=self.compression_opts
                         )
        makedim('/timetraces/', [('t', '/t_spectra/', 'time (s)')])
        self.saver.create_attr('/timetraces/', 'units', 'Volts')

        #self.saver.append('/spectra/',
        #                 emptydata((f.shape[0],)),
        #                 chunks=self.chunks,
        #                 compression=self.compression,
        #                 compression_opts=self.compression_opts
        #                )
        #makedim('/spectra/', [('f', '/f/', 'Frequency (Hz)')])
        #self.saver.create_attr('/spectra/', 'units', r'V/$\sqrt{Hz\rm}$')

        self.saver.append('/accelerometer/', 
                         emptydata((len(accel_chs), spectralen,)),
                         chunks=self.chunks,
                         compression=self.compression,
                         compression_opts=self.compression_opts
                          )
        makedim('/accelerometer/', [('accel_names', '/accel_names/', 'name'),
                                    ('t', '/t_spectra/', 'time (s)')
                                   ]
               )
        self.saver.create_attr('/accelerometer/', 'units', 'Volts')

        self.saver.append('/capacitance/', emptydata(None))
        makedim('/capacitance/', None)
        self.saver.create_attr('/capacitance/', 'units', 'Volts') #hello

        self.saver.append('/truepositions/', emptydata((3,)))
        makedim('/truepositions/', [('pos_names', '/pos_names/', 'name')])
        self.saver.create_attr('/truepositions/', 'units', 'Volts')

        self.saver.append('/wasOL/', emptydata(None))
        makedim('/wasOL/', None)
        self.saver.create_attr('/wasOL/', 'units', 'boolean (0 False, 1 True)')

        self.saver.append('/spectra_starttimes/', emptydata(None))
        makedim('/spectra_starttimes/', None)
        self.saver.create_attr('/spectra_starttimes/', 'units', 'epoch time (seconds)')

        self.saver.create_attr_dict('/',
                {
                    'scanheight': self.scanheight,
                    'measure_time': self.measure_time,
                    'measure_freq': self.measure_freq,
                    'plane_loc': self.plane.filename,
                    'squidarray': self.saa.__getstate__(),
                    'gain': self.preamp.gain,
                })

    def run(self, fastaxis='x'):
        '''
        '''
        y_index = 0
        x_index = 0
        lastfig = 0

        if fastaxis=='x':
            inner = self.xs
            outer = self.ys

            fast_plane = lambda self, o, i: self.plane.plane(i, o)
            sweep_pz = lambda self, o, i, z: self.piezos.sweep(self.piezos.V,
                                                               {'x': i,
                                                                'y': o,
                                                                'z': z},
                                                               )
            makeslc = lambda o, i: (i, o)
        else:
            inner = self.ys
            outer = self.xs

            fast_plane = lambda self, o, i: self.plane.plane(o, i)
            sweep_pz = lambda self, o, i, z: self.piezos.sweep(self.piezos.V,
                                                               {'x': o,
                                                                'y': i,
                                                                'z': z},
                                                               )
            makeslc = lambda o, i: (o, i)

        o_i = 0 #outer index
        for o in outer:
            i_i = 0 #inner index
            for i in inner:
                z = fast_plane(self, o_i, i_i) - self.scanheight
                sweep_pz(self, o, i, z)

                self.saver.append('/truepositions/', 
                                  np.array([self.piezos.V['x'],
                                            self.piezos.V['y'],
                                            self.piezos.V['z']]),
                                  slc=makeslc(o_i, i_i))
                    
                self.saver.append('/capacitance/',
                                 self.lockin_cap.R,
                                 slc=makeslc(o_i, i_i))
                    
                # take and save time traces
                chs = ['dc', ] + self.accel_chs
                t = time.time()
                r = self.daq.monitor(chs, self.measure_time, 
                                     sample_rate=self.measure_freq)
                self.saver.append('/timetraces/', r['dc']/self.preamp.gain,
                                  slc=makeslc(o_i,i_i))
                for j in range(len(self.accel_chs)):
                    self.saver.append('/accelerometer/',
                                      r[self.accel_chs[j]]/100,
                                      slc=makeslc(o_i, i_i) + (j,)
                                      )
                self.saver.append('/wasOL/', self.preamp.is_OL(), 
                                  slc=makeslc(o_i, i_i))
                self.saver.append('/spectra_starttimes/', t, 
                                  slc=makeslc(o_i, i_i))
                i_i += 1
            o_i += 1
                

class Vibration(Measurement):
    '''
    Record spectra for vibration analysis
    '''

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
        '''
        '''
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
        '''
        '''
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
        '''
        '''
        pass

    def plot(self):
        '''
        '''
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


