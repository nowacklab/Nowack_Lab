import xarray as xr
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
    def notNone(a, b, c):
        if a is None and b is None:
            return c
        elif a is None:
            return b
        return a

