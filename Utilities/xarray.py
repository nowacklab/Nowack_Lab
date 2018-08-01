import xarray as xr
from importlib import reload

class Import_As_Xarray:
    
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
                              }
                        )
        return ds




