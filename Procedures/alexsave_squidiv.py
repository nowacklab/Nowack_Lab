import numpy as np
import matplotlib.pyplot as plt 
import time
from importlib import reload

import Nowack_Lab.Utilities.datasaver
reload(Nowack_Lab.Utilities.datasaver)
from Nowack_Lab.Utilities.datasaver import Saver

import Nowack_Lab.Utilities.alexsave_david_meas
reload(Nowack_Lab.Utilities.alexsave_david_meas)
from Nowack_Lab.Utilities.alexsave_david_meas import Preamp_Util

class SQUID_testing():
    _daq_inputs = ['iv']
    _daq_outputs = ['iv', 'fc', 'mod']

    def __init__(self, 
                 instruments,
                 iv_R = 2,
                 mod_R = 2,
                 fc_R = 2,
                 sample_rate=10000
                 ):
        self.daq = instruments['daq']
        Preamp_Util.init(instruments)

        self.iv_ctr = 0
        self.mod_fastmod_ctr = 0
        self.mod_fastiv_ctr = 0
        self.fc_fastmod_ctr = 0
        self.fc_fastfc_ctr = 0

        self.defaults = {'iv_R':iv_R,
                         'mod_R':mod_R,
                         'fc_R':fc_R,
                         'sample_rate':sample_rate
                         }
        self.basenames = []
        self.notesindex = []

        self.saver = Saver(name='SQUID_testing_suit')

    def add_post_notes(self, index, note):
        '''
        add note to the indexth set of data taken
        Best use: index < 0, index=-1 for the previous dataset
        '''
        self.saver.create_attr(self.basename[index], 
                               'note_{0}'.format(self.notesindex[index]),
                               note)
        self.notesindex[index] += 1

    def _three_param_sweep(self,
                           i0s = [],
                           i1s = [],
                           i2s = [],
                           r0  = 2,
                           r1  = 2,
                           r2  = 2,
                           o0  = 'fc',
                           o1  = 'mod',
                           o2  = 'iv',
                           i0  = 'iv',
                           sample_rate=None,
                           basename='/3_param_sweep_000',
                           pre_notes=''):

        if sample_rate == None:
            sample_rate = self.defaults['sample_rate']

        _i0s = np.asarray(i0s)
        _i1s = np.asarray(i1s)
        _i2s = np.asarray(i2s)
        v0s = _i0s*r0
        v1s = _i1s*r1
        v2s = _i2s*r2
        datasetname = basename + '_V'
        self.basenames.append(name)
        self.notesindex.append(0)

        i0_name = basename + '_' + o0 + '_i'
        i1_name = basename + '_' + o1 + '_i'
        i2_name = basename + '_' + o2 + '_i'
        v0src_name = basename + '_' + o0 + '_vsrc'
        v1src_name = basename + '_' + o1 + '_vsrc'
        v2src_name = basename + '_' + o2 + '_vsrc'
        v0meas_name = basename + '_' + o0 + '_meas'
        v1meas_name = basename + '_' + o1 + '_meas'
        v2meas_name = basename + '_' + o2 + '_meas' 
        # dimensions / coordinates
        self.saver.append(i0_name, _i0s,
        self.create_attr(i0_name, 'units', 'Amps')
        self.saver.append(i1_name, _i1s,
        self.create_attr(i1_name, 'units', 'Amps')
        self.saver.append(i2_name, _i2s,
        self.create_attr(i2_name, 'units', 'Amps')
        self.saver.append(basename + '_direction', ['incr', 'decr'])
        self.saver.append(basename + '_data_names', 
                ['time', o0+'_Vsrc', o1+'_Vsrc', o2+'_Vsrc', i0+'_Vmeas'])

        self.saver.append(datasetname, np.full( 
                              (v0s.shape[0],
                               v1s.shape[1],
                               v2s.shape[2],
                               2, # 0 sweep up, 1 sweep down
                               5, # 0 time, 1 v0, 2 v1, 3 v2, 4 meas v0
                               ), np.nan))
        self.saver.make_dim(datasetname, 0, i0_name[1:], i0_name, 
                            'current on {0} (Amps)'.format(o0))
        self.saver.make_dim(datasetname, 1, i1_name[1:], i1_name, 
                            'current on {0} (Amps)'.format(o1))
        self.saver.make_dim(datasetname 2, i2_name[1:], i2_name, 
                            'current on {0} (Amps)'.format(o2))
        self.saver.make_dim(datasetname, 3, 
                            basename[1:] + '_direction', 
                            basename + '_direction',
                            'direction of sweep')
        self.saver.make_dim(datasetname, 4,
                            basename[1:] + '_data_names', 
                            basename + '_data_names',
                            'names of data fields')
        self.saver.create_attr(datasetname, 'pre_notes', pre_notes)
        self.saver.create_attr_dict(datasetname, 
                {o0 + '_R': r0,
                 o1 + '_R': r1,
                 o2 + '_R': r2,
                 'sample_rate': sample_rate
                 })

        self._sweep_to_val_safe(o0, v0s[i], int(v0s.shape[0]/2), 
                                sample_rate)
        for i in range(v0s.shape[0]):
            self._sweep_to_val_safe(o0, v0s[i], 1, sample_rate)
            self._sweep_to_val_safe(o1, v1s[0], v1s.shape[2]/2, sample_rate)

            for j in range(v1s.shape[0]):
                self._sweep_to_val_safe(o1, v1s[j], 1, sample_rate)

                self._sweep_to_val_safe(o2, v2s[0], v2s.shape[0]/2, 
                                        sample_rate)
                u_time = time.time()
                u_src, u_meas = self.daq.sweep(
                        Vstart={o2: v2s[ 0]},
                        Vend  ={o2: v2s[-1]},
                        chan_in=[i0],
                        sample_rate=sample_rate,
                        numsteps=v2s.shape[0]
                        )
                d_time = time.time()
                d_src, d_meas = self.daq.sweep(
                        Vstart={o2: v2s[-1]},
                        Vend  ={o2: v2s[ 0]},
                        chan_in=[i0],
                        sample_rate=sample_rate,
                        numsteps=v2s.shape[0]
                        )
                self._sweep_to_val_safe(o2, 0, v2s.shape[0]/2, 
                                        sample_rate)

                slc_len = v2s.shape[0]
                ones = np.ones(slc_len)
                v0 = self.daq.outputs[o0].V
                v1 = self.daq.outputs[o1].V

                self.saver.append(datasetname, u_meas['t']+u_time, slc=(i,j,slice(slc_len),0,0))
                self.saver.append(datasetname, v0*ones,
                                slc=(i,j,slice(slc_len),0,1))
                self.saver.append(datasetname, v1*ones,
                                slc=(i,j,slice(slc_len),0,2))
                self.saver.append(datasetname, u_src[o2], 
                                slc=(i,j,slice(slc_len),0,3))
                self.saver.append(datasetname, 
                                u_meas[i0]/self.preamp.gain, 
                                slc=(i,j,slice(slc_len),0,4))

                self.saver.append(datasetname, d_meas['t']+d_time, 
                                slc=(i,j,slice(slc_len),1,0))
                self.saver.append(datasetname, v0*ones,
                                slc=(i,j,slice(slc_len),1,1))
                self.saver.append(datasetname, v1*ones,
                                slc=(i,j,slice(slc_len),1,2))
                self.saver.append(datasetname, d_src[o2], 
                                slc=(i,j,slice(slc_len),1,3))
                self.saver.append(datasetname, 
                                d_meas[i0]/self.preamp.gain, 
                                slc=(i,j,slice(slc_len),1,4))
             
            self._sweep_to_val_safe(o1, 0, v1s.shape[0]/2, sample_rate)
         
        self._sweep_to_val_safe(o0, 0, v0s.shape[0]/2, sample_rate)



        self.saver.create_attr_dict(datasetname, self._get_preamp_dict(),
                                    prefix='instr_preamp_')
    
    def iv(self,
           iv_Is  = [],
           iv_R   = None,
           sample_rate=None,
           mod_current=0,
           fc_current=0,
           pre_notes=''):
        '''
        Run IV measurement
        
        Params:
        ~~~~~~~
        iv_Is (ndarray):           array of desired iv currents in Amps
        iv_R (float):              resistance in ohms of the IV bias line
        mod_R (float):             resistance in ohms of the mod bias line
        fc_R (float):              resistance in ohms of the fc bias line
        sample_rate (int or None): sample rate of DAQ.  If None, default
        mod_current (float):       current in Amps to bias the mod line
        fc_current (float):        current in Amps to bias the mod line
        pre_notes (string):        any notes about this iv?
        '''
        basename = '/iv_{0:03d}'.format(self.mod_fastmod_ctr)

        if iv_R == None:
            iv_R = self.defaults['iv_R']
        if mod_R == None:
            mod_R = self.defaults['mod_R']
        if fc_R == None:
            fc_R = self.defaults['fc_R']

        self._three_param_sweep(i0s=np.array([fc_current]),
                                i1s=np.array([mod_current]),
                                i2s=iv_Is,
                                r0=fc_R,
                                r1=mod_R,
                                r1=iv_R,
                                o0='fc',
                                o1='mod',
                                o2='iv',
                                i0='iv',
                                sample_rate=sample_rate,
                                basename=basename,
                                pre_notes=pre_notes)
        self.iv_ctr += 1

    def mod_fastmod(self,
                    iv_Is  = [],
                    mod_Is = [],
                    iv_R   = None,
                    mod_R  = None,
                    fc_R  = None,
                    sample_rate=None,
                    fc_current=0,
                    pre_notes=''):
        '''
        Run mod, fast mod measurement.  Sweeps the mod fast
        
        Params:
        ~~~~~~~
        iv_Is (ndarray):           array of desired iv currents in Amps
        mod_Is (ndarray):          array of desired mod currents in Amps
        iv_R (float):              resistance in ohms of the IV bias line
        mod_R (float):             resistance in ohms of the mod bias line
        fc_R (float):              resistance in ohms of the fc bias line
        sample_rate (int or None): sample rate of DAQ.  If None, default
        fc_current (float):        current in Amps to bias the mod line
        pre_notes (string):        any notes about this iv?
        '''
        basename = '/mod_fastmod_{0:03d}'.format(self.mod_fastmod_ctr)

        if iv_R == None:
            iv_R = self.defaults['iv_R']
        if mod_R == None:
            mod_R = self.defaults['mod_R']
        if fc_R == None:
            fc_R = self.defaults['fc_R']

        self._three_param_sweep(i0s=np.array([fc_current]),
                                i1s=iv_Is,
                                i2s=mod_Is,
                                r0=fc_R,
                                r1=iv_R,
                                r2=mod_R,
                                o0='fc',
                                o1='iv',
                                o2='mod',
                                i0='iv',
                                sample_rate=sample_rate,
                                basename=basename,
                                pre_notes=pre_notes)
        self.mod_fastmod_ctr += 1

    def mod_fastiv(self,
                    iv_Is  = [],
                    mod_Is = [],
                    iv_R   = None,
                    mod_R  = None,
                    fc_R  = None,
                    sample_rate=None,
                    fc_current=0,
                    pre_notes=''):
        '''
        Run mod, fast iv measurement.  Sweeps the iv fast
        
        Params:
        ~~~~~~~
        iv_Is (ndarray):           array of desired iv currents in Amps
        mod_Is (ndarray):          array of desired mod currents in Amps
        iv_R (float):              resistance in ohms of the IV bias line
        mod_R (float):             resistance in ohms of the mod bias line
        fc_R (float):              resistance in ohms of the fc bias line
        sample_rate (int or None): sample rate of DAQ.  If None, default
        fc_current (float):        current in Amps to bias the mod line
        pre_notes (string):        any notes about this iv?
        '''
        basename = '/mod_fastiv_{0:03d}'.format(self.mod_fastiv_ctr)

        if iv_R == None:
            iv_R = self.defaults['iv_R']
        if mod_R == None:
            mod_R = self.defaults['mod_R']
        if fc_R == None:
            fc_R = self.defaults['fc_R']

        self._three_param_sweep(i0s=np.array([fc_current]),
                                i1s=mod_Is,
                                i2s=iv_Is,
                                r0=fc_R,
                                r1=mod_R,
                                r2=iv_R,
                                o0='fc',
                                o1='mod',
                                o2='iv',
                                i0='iv',
                                sample_rate=sample_rate,
                                basename=basename,
                                pre_notes=pre_notes)
        self.mod_fastiv_ctr += 1

    def fc_fastmod(self,
                    mod_Is = [],
                    fc_Is  = [],
                    iv_R   = None,
                    mod_R  = None,
                    fc_R  = None,
                    sample_rate=None,
                    iv_current=10e-6,
                    pre_notes=''):
        '''
        Run field coil, fast mod measurement.  Sweeps the mod fast
        
        Params:
        ~~~~~~~
        mod_Is (ndarray):          array of desired fc currents in Amps
        fc_Is (ndarray):           array of desired mod currents in Amps
        iv_R (float):              resistance in ohms of the IV bias line
        mod_R (float):             resistance in ohms of the mod bias line
        fc_R (float):              resistance in ohms of the fc bias line
        sample_rate (int or None): sample rate of DAQ.  If None, default
        iv_current (float):        current in Amps to bias the iv line
        pre_notes (string):        any notes about this iv?
        '''
        basename = '/fc_fastmod_{0:03d}'.format(self.fc_fastmod_ctr)

        if iv_R == None:
            iv_R = self.defaults['iv_R']
        if mod_R == None:
            mod_R = self.defaults['mod_R']
        if fc_R == None:
            fc_R = self.defaults['fc_R']

        self._three_param_sweep(i0s=np.array([fc_current]),
                                i1s=fc_Is,
                                i2s=mod_Is,
                                r0=iv_R,
                                r1=fc_R,
                                r2=mod_R,
                                o0='iv',
                                o1='fc',
                                o2='mod',
                                i0='iv',
                                sample_rate=sample_rate,
                                basename=basename,
                                pre_notes=pre_notes)
        self.fc_fastmod_ctr += 1

    def fc_fastfc(self,
                    mod_Is = [],
                    fc_Is  = [],
                    iv_R   = None,
                    mod_R  = None,
                    fc_R  = None,
                    sample_rate=None,
                    iv_current=10e-6,
                    pre_notes=''):
        '''
        Run field coil, fast field coil measurement.  Sweeps the fc fast
        
        Params:
        ~~~~~~~
        mod_Is (ndarray):          array of desired fc currents in Amps
        fc_Is (ndarray):           array of desired mod currents in Amps
        iv_R (float):              resistance in ohms of the IV bias line
        mod_R (float):             resistance in ohms of the mod bias line
        fc_R (float):              resistance in ohms of the fc bias line
        sample_rate (int or None): sample rate of DAQ.  If None, default
        iv_current (float):        current in Amps to bias the iv line
        pre_notes (string):        any notes about this iv?
        '''
        basename = '/fc_fastmod_{0:03d}'.format(self.fc_fastmod_ctr)

        if iv_R == None:
            iv_R = self.defaults['iv_R']
        if mod_R == None:
            mod_R = self.defaults['mod_R']
        if fc_R == None:
            fc_R = self.defaults['fc_R']

        self._three_param_sweep(i0s=np.array([fc_current]),
                                i1s=mod_Is,
                                i2s=fc_Is,
                                r0=iv_R,
                                r1=mod_R,
                                r2=fc_R,
                                o0='iv',
                                o1='mod',
                                o2='fc',
                                i0='iv',
                                sample_rate=sample_rate,

    def _sweep_to_val_safe(self, outputname, val, numsteps, rate):
        _,_ = self.daq.singlesweep(outputname, 
                                   val,
                                   numsteps=int(numsteps),
                                   sample_rate=rate)
