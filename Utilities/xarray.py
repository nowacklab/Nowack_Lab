import xarray as xr
import numpy as np
from importlib import reload

class Xarray:
    
    @staticmethod
    def scanplane(fullpath):
        '''
        Warnings:
        ~~~~~~~~~
          - this might not work for fast_y.  The x,y might be flipped
        '''
        # load the scanplane
        import Nowack_Lab.Procedures.scanplane
        reload(Nowack_Lab.Procedures.scanplane)
        from Nowack_Lab.Procedures.scanplane import Scanplane
        sp = Scanplane.load(fullpath)

        sp_x = sp.X[0,:]
        sp_y = sp.Y[:,0]

        dc = xr.DataArray(sp.V['dc'], dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='dc SQUID data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })
        acx = xr.DataArray(sp.V['acx'], dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='AC x SQUID data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })
        acy = xr.DataArray(sp.V['acy'], dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='AC y SQUID data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })
        cap = xr.DataArray(sp.V['cap'], dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='Capacitance data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })
        z   = xr.DataArray(sp.Z, dims=['y','x'], coords={'y':sp_y, 'x':sp_x},
                          name='Z height data (V)', 
                          attrs={'data units':'Volts',
                                'coords units': 'Volts'
                                })

        squidarray = Xarray.notNone(sp.squidarray, 
                                    sp.plane.instruments['squidarray'], None)
        preamp = Xarray.notNone(sp.preamp, sp.plane.instruments['preamp'], None)
        lockin_current = Xarray.notNone(sp.lockin_current, 
                                        sp.plane.instruments['lockin_current'], None)
        lockin_squid = Xarray.notNone(sp.lockin_squid, 
                                        sp.plane.instruments['lockin_squid'], None)
        lockin_cap = Xarray.notNone(sp.lockin_cap, 
                                        sp.plane.instruments['lockin_cap'], None)
        
        
        #make dataset 
        ds = xr.Dataset({'dc': dc, 'acx':acx, 'acy': acy, 'cap': cap, 'z': z},
                        attrs={'filename': sp.filename,
                              'scan_rate': sp.scan_rate,
                              'scan_height': sp.scanheight,
                              'time_elapsed_s': sp.time_elapsed_s,
                              'timestamp': sp.timestamp,
                              'interrupt': sp.interrupt,
                              'fast_axis': sp.fast_axis,
                              'center': sp.center,
                              'squidarray': squidarray,
                              'preamp': preamp,
                              'lockin_current': lockin_current,
                              'lockin_squid': lockin_squid,
                              'lockin_cap': lockin_cap
                              }
                        )
        return ds

    @staticmethod
    def scanspectra(fullpath, transposed=False):
        '''
        '''

        # load the scanspectra
        import Nowack_Lab.Procedures.scanspectra
        reload(Nowack_Lab.Procedures.scanspectra)
        from Nowack_Lab.Procedures.scanspectra import Scanspectra
        sp = Scanspectra.load(fullpath)

        sp_x = sp.X[0,:]
        sp_y = sp.Y[:,0]

        dims = ['y', 'x', 't'] if transposed else ['x', 'y', 't']

        V = xr.DataArray(sp.V, dims=dims, 
                             coords={'x':sp_x, 'y':sp_y, 't':sp.t},
                             name='Voltage Time traces (V)',
                             attrs={'data units': 'Volts',
                                    'x units': 'Volts',
                                    'y units': 'Volts',
                                    't units': 'Seconds',
                                    }
                             )

        dims = ['y', 'x', 'f'] if transposed else ['x', 'y', 'f']

        psdAve = xr.DataArray(sp.psdAve, dims=dims, 
                             coords={'x':sp_x, 'y':sp_y, 'f':sp.f},
                             name='Voltage Time traces (V)',
                             attrs={'data units': 'Volts',
                                    'x units': 'Volts',
                                    'y units': 'Volts',
                                    'f units': 'Hz',
                                    }
                             )

        dims = ['y', 'x'] if transposed else ['x', 'y']
        Z = xr.DataArray(sp.Z, dims=dims, 
                         coords={'x':sp_x, 'y':sp_y},
                         name='Z position (V)',
                         attrs={'data units': 'Volts',
                             'x units': 'Volts',
                             'y units': 'Volts',
                             }
                         )
        squidarray = Xarray.notNone(sp.squidarray, 
                                    sp.plane.instruments['squidarray'],
                                    sp.instruments['squidarray'])
        preamp = Xarray.notNone(sp.preamp, sp.plane.instruments['preamp'],
                                sp.instruments['preamp'])
        #lockin_current = Xarray.notNone(sp.lockin_current, 
        #                                sp.plane.instruments['lockin_current'],
        #                                sp.instruments['lockin_current'])
        #lockin_squid = Xarray.notNone(sp.lockin_squid, 
        #                                sp.plane.instruments['lockin_squid'],
        #                                sp.instruments['lockin_squid'])
        #lockin_cap = Xarray.notNone(sp.lockin_cap, 
        #                                sp.plane.instruments['lockin_cap'],
        #                                sp.instruments['lockin_cap'])

        # make dataset
        ds = xr.Dataset({'V': V, 'psdAve':psdAve, 'z': Z, },
                        attrs={'filename': sp.filename,
                               'monitor_time': sp.monitor_time,
                               'num_averages': sp.num_averages,
                               'numpts': sp.numpts,
                               'sample_rate': sp.sample_rate,
                               'scanheight': sp.scanheight,
                               'timestamp': sp.timestamp,
                               'time_elapsed_s': sp.time_elapsed_s,
                               'squidarray': squidarray,
                              'preamp': preamp,
        #                      'lockin_current': lockin_current,
        #                      'lockin_squid': lockin_squid,
        #                      'lockin_cap': lockin_cap
                              }
                        )
        return ds

    @staticmethod
    def arraytunebatch1(fullpath):
        '''
        this will probably change considerably if/when we rework 
        arraytunebatch
        '''
        import Nowack_Lab.Procedures.array_tune
        reload(Nowack_Lab.Procedures.array_tune)
        from Nowack_Lab.Procedures.array_tune import ArrayTuneBatch
        atb = ArrayTuneBatch.load(fullpath)

        sflux = atb.sflux
        sbias = atb.sbias
        aflux = atb.aflux

        dims = ['sbias', 'aflux', 'sflux']

        char_saasig = xr.DataArray(atb.char_saasig, 
                                       dims= dims + ['t'],
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 },
                                       name='SAA signal for characteristic (Volts)',
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )

        char_testsig = xr.DataArray(atb.char_testsig, 
                                       dims= dims + ['t'],
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 },
                                       name='Test signal for characteristic (Volts)',
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        spectrum_mean = xr.DataArray(atb.spectrum_mean[...,0], 
                                       dims= dims,
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 },
                          name='Mean w.r.t frequency of Noise Spectrum (phi_0)',
                                       attrs={'data units': 'phi_0',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        spectrum_std = xr.DataArray(atb.spectrum_std[...,0], 
                                       dims= dims,
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 },
            name='Standard deviation w.r.t frequency of Noise Spectrum (phi_0)',
                                       attrs={'data units': 'phi_0',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        spectrum_psd = xr.DataArray(atb.spectrum_psd, 
                                       dims= dims + ['frequency'],
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                 'frequency': atb.spectrum_f,
                                                 },
                          name='Mean w.r.t frequency of Noise Spectrum (phi_0)',
                                       attrs={'data units': 'phi_0',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              'frequency':   'Hz',
                                              },
                                       )
        filenames = np.full(atb.filenameindex.shape, 
                            max(atb.arraytunefilenames, key=len)
                           )
        shape = filenames.shape
        for i in range(filenames.flatten().shape[0]):
            index = np.unravel_index(i, shape)
            if np.isnan(atb.filenameindex[index]):
                filenames[index] = 'N/A: Did Not Lock'
                continue
            filenames[index] = atb.arraytunefilenames[int(atb.filenameindex[index])]

        atfilenames = xr.DataArray(filenames[...,0],
                                        dims = dims,
                                       coords = {'sbias': sbias,
                                                 'aflux': aflux,
                                                 'sflux': sflux,
                                                },
                                       name='Array Tune filenames (string)',
                                       attrs={'data units': 'string',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        char_lockpt_mean = xr.DataArray(atb.char_stats[...,0], 
                                     dims=dims,
                                     coords = {'sbias': sbias,
                                               'aflux': aflux,
                                               'sflux': sflux,
                                              },
                                     name=('Squid Characteristic statistics: ' + 
                                           'average of the value near the lockpoint ' +
                                           '(Volts)'),
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        char_lockpt_grad = xr.DataArray(atb.char_stats[...,1], 
                                     dims=dims,
                                     coords = {'sbias': sbias,
                                               'aflux': aflux,
                                               'sflux': sflux,
                                              },
                           name=('Squid Characteristic statistics: ' + 
                                 'average of the gradient near the lockpoint ' +
                                 '(Volts)'),
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        char_lockpt_err = xr.DataArray(atb.char_stats[...,2], 
                                     dims=dims,
                                     coords = {'sbias': sbias,
                                               'aflux': aflux,
                                               'sflux': sflux,
                                              },
                                     name=('Squid Characteristic statistics: ' + 
                                           'average of the error in the fit near ' + 
                                           'the lockpoint (Volts)'),
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        char_lockpt_good = xr.DataArray(atb.char_stats[...,3], 
                                     dims=dims,
                                     coords = {'sbias': sbias,
                                               'aflux': aflux,
                                               'sflux': sflux,
                                              },
                                     name=('Squid Characteristic statistics: ' + 
                                           'average of the gradient/error near ' + 
                                           'the lockpoint (Volts)'),
                                       attrs={'data units': 'Volts',
                                              'sbias units': 'Micro Amps',
                                              'aflux units': 'Micro Amps',
                                              'sflux units': 'Micro Amps',
                                              },
                                       )
        # make dataset
        ds = xr.Dataset({'char_saasig': char_saasig, 
                         'char_testsig': char_testsig,
                         'spectrum_mean': spectrum_mean,
                         'spectrum_std': spectrum_std,
                         'spectrum_psd': spectrum_psd,
                         'arraytune_filenames': atfilenames,
                         'char_lockpt_mean': char_lockpt_mean,
                         'char_lockpt_grad': char_lockpt_grad,
                         'char_lockpt_err': char_lockpt_err,
                         'char_lockpt_good': char_lockpt_good,
                        },
                        attrs={'filename': atb.filename,
                               'timestamp': atb.timestamp,
                               'time_elapsed_s': atb.time_elapsed_s,
                               'conversion': atb.conversion,
                              }
                        )
        return ds
        
    @staticmethod
    def bestlockpoint(fullpath):
        import Nowack_Lab.Procedures.array_tune
        reload(Nowack_Lab.Procedures.array_tune)
        from Nowack_Lab.Procedures.array_tune import BestLockPoint
        blp = BestLockPoint.load(fullpath)

        dims = ['sbias']
        sbias = blp.sbiasList
        time = blp.bestloc_raw_time[0] # all times are the same
        
        char_timesort = xr.DataArray(np.dstack([blp.bestloc_raw_test, 
                                                blp.bestloc_raw_saa]), 
                                  dims=dims + ['time', 'params_timesort'],
                                  coords={'sbias': sbias,
                                          'time' : time,
                                          'params_timesort': ['test', 'saa']},
                                  name='{Test, SAA} Signal sorted by time (V)',
                                  attrs={'data units': 'Volts',
                                         'sbias units': 'Micro Amps',
                                         'time units' : 'Seconds'
                                        },
                                  )
        sbiasfull = np.tile(sbias, (2560,1)).T

        char_testsort = xr.DataArray(np.dstack([blp.bestloc_testsort_saa,
                                                blp.bestloc_mean,
                                                blp.bestloc_grad,
                                                blp.bestloc_err,
                                                blp.bestloc_absgrad_over_err]),
                                  dims=dims + ['test_i', 'params_testsort'],
                                  coords={'sbias': sbias,
                                          'params_testsort': ['saa', 'smoothed',
                                                     'gradient', 'error', 
                                                     'gradient/error'],
                                          'test_V': (('sbias', 'test_i'), 
                                                    blp.bestloc_testsort_test),
                                          'sbias_full': (('sbias', 'test_i'), 
                                                         sbiasfull),
                                          },
                                  name='Signals sorted by test signal (V)',
                                  attrs={'data units': 'Volts',
                                         'sbias units': 'Micro Amps',
                                         'test meaning': 'Test Signal in Volts',
                                         'saa meaning': 'SAA Signal in Volts',
                                         'smoothed meaning': 
                                            'Smoothed SAA Signal in Volts',
                                         'gradient meaning': 
                                            'Gradient of smoothed SAA Signal in Volts',
                                         'error meaning': 
                                            '(smoothed - saa) signal in Volts',
                                         'gradient/error meaning':
                                            'gradient / error signal in Volts'
                                        },
                                  )
        ds = xr.Dataset({'char_timesort':char_timesort,
                         'char_testsort':char_testsort,
                         },
                         attrs={'filename':  blp.filename,
                                'timestamp': blp.timestamp,
                                'monitortime': blp.monitortime,
                                'preamp': blp.preamp,
                                'samplerate': blp.samplerate,
                                'squidarray': blp.squidarray,
                                'testinputconv': blp.testinputconv,
                                }
                         )
        return ds
                                

        

    @staticmethod
    def notNone(a, b, c):
        if a is None and b is None:
            return c
        elif a is None:
            return b
        return a

