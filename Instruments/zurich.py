# Copyright 2016 Zurich Instruments AG

import time, numpy as np
from .instrument import Instrument
import zhinst.ziPython as ziP
import zhinst.utils as utils

class gateVoltageError(Exception):
    pass

class HF2LI(Instrument):
    '''
    Creates a Zurich HF2Li object, to control a zurich lock in amplifier
    '''

    _label = 'Zurich HF2LI'
    device_id = None

    def __init__(self, server_address = 'localhost', server_port = 8005 ,
                    device_serial = '', in_channel = None, meas_type='V'):
            '''
            Creates the HF2LI object. By choosing server address, can connection
            to HF2LI on remote (local network) computer.
            Arguments:
            server_address (str,optional) = Private IPV4 address of the computer
                                hosting the zurich. Defults to 'localhost',
                                the computer the python kernel is running on.
            server_port (int, optional) = Port of Zurich HF2LI. For local is
                                always 8005 (default), usually 8006 for remote.
            device_serial (str, optional) = Serial number of prefered zurich
                                hf2li. If empty string or does not exist,
                                uses first avaliable ZI.
            in_channel: if None, will use both inputs (TODO). Else, choose input 1
                                or 2.
            meas_type: 'I' or 'V'. Choose whether this channel measures current
                                (via transimpedance amplifier) or voltage.
            '''

            super().__init__()

            self.daq = ziP.ziDAQServer(server_address, server_port)
            deviceList = utils.devices(self.daq)

            # Find device
            if device_serial in deviceList:
                self.device_id = device_serial
            elif device_serial != '':
                print('Requested device not found.')
            if self.device_id is None:
                self.device_id = utils.autoDetect(self.daq)  # first available
            print('Using Zurich HF2LI with serial %s' % self.device_id)

            if in_channel is None:
                raise Exception()
            self.in_channel = in_channel
            self.meas_type = meas_type

            # This code wouild disable all outputs and demods
            # general_setting = [['/%s/demods/*/enable' % self.device_id, 0],
            #        ['/%s/demods/*/trigger' % self.device_id, 0],
            #        ['/%s/sigouts/*/enables/*' % self.device_id, 0],
            #        ['/%s/scopes/*/enable' % self.device_id, 0]]
            #
            # self.daq.set(general_setting)
            # self.daq.sync()

            # self.configure()
            # print('Must now reenable data transfer and output in Zurich software. Check setup again.')

    def __getstate__(self):
        self._save_dict = {'device_id': self.device_id,
                          'X': self.X,
                          'Y': self.Y,
                          'zurich_dict': self.daq.get('/', True) #  all settings
                          }
        return self._save_dict


    def __setstate__(self, state):
        state['_X'] = state.pop('X')
        state['_Y'] = state.pop('Y')

        self.__dict__.update(state)

    def configure(self):
        pass
#         '''
#         configure the instrument for this experiment. The following
#         channels and indices work on all device configurations. The values
#         below may be changed if the instrument has multiple input/output
#         channels and/or either the Multifrequency or Multidemodulator
#         options installed.
#         '''
#         out_channel = outputchan - 1
#         in_channel = inputchan - 1
#         demod_index = 0
#         osc_index = outputchan-1
#         demod_rate = 10e3
#         out_mix_ch = int(self.daq.listNodes('/%s/sigouts/%d/amplitudes/'
#                                         % (self.device_id, out_channel),0)[0])
#         if couple == 'ac':
#             acUse = 1
#         else:
#             acUse = 0
#         exp_setting = [
# ['/%s/sigins/%d/ac'             % (self.device_id, self.in_channel), 0],
# ['/%s/sigins/%d/range'          % (self.device_id, self.in_channel), 2],
# ['/%s/demods/%d/enable'         % (self.device_id, demod_index), 1],
# ['/%s/demods/%d/rate'           % (self.device_id, demod_index), demod_rate],
# ['/%s/demods/%d/adcselect'      % (self.device_id, demod_index), self.in_channel],
# ['/%s/demods/%d/order'          % (self.device_id, demod_index), 4],
# ['/%s/demods/%d/timeconstant'   % (self.device_id, demod_index),
#                                                                 time_constant],
# ['/%s/demods/%d/oscselect'      % (self.device_id, demod_index), osc_index],
# ['/%s/demods/%d/harmonic'       % (self.device_id, demod_index), 1],
# ['/%s/sigouts/%d/on'            % (self.device_id, out_channel), 1],
# ['/%s/sigouts/%d/enables/%d'    % (self.device_id, out_channel, out_mix_ch),
#                                                                             1],
# ['/%s/sigouts/%d/range'         % (self.device_id, out_channel),  1],
# ['/%s/sigouts/%d/amplitudes/%d' % (self.device_id, out_channel, out_mix_ch),
#                                                                     amplitude],
# ['/%s/sigins/%d/diff'           % (self.device_id, self.in_channel), 0],
# ['/%s/sigouts/%d/add'           % (self.device_id, out_channel), 0],
#                        ]
#
#         self.daq.set(exp_setting)

    @property
    def X(self):
        self._X = float(self.get('x'))
        if self.meas_type == 'I':
            self._X /= self.TA_gain
        if self._X == 0:
            self._X = 1e-34 # so we don't have zeros
        return self._X


    @property
    def Y(self):
        self._Y = float(self.get('y'))
        if self.meas_type == 'I':
            self._Y /= self.TA_gain
        if self._Y == 0:
            self._Y = 1e-34 # so we don't have zeros
        return self._Y

    @property
    def TA_gain(self):
        '''
        Inflexible. Get transimpedance amplifier gain if set up for input 0
        '''
        param = '/%s/zctrls/0/tamp/0/currentgain' %self.device_id
        return self.get_setting(param)[0]


    def get(self, param):
        '''
        Get a parameter from the lockin.
        '''
        demod_num = (self.in_channel-1)*3

        return self.daq.getSample('/%s/demods/%i/sample' %(self.device_id, demod_num))[param]
        # self.in_channel

    def get_setting(self, param):
        '''
        Bypass the Zurich's annoying get protocol.
        '''
        return self.daq.get(param, True)[param]
