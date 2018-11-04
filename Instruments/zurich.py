# Copyright 2016 Zurich Instruments AG

import time, numpy as np
from .instrument import Instrument
try:
    import zhinst.ziPython as ziP
    import zhinst.utils as utils
except:
    print('zhinst not imported in zurich.py!')


class Zurich(Instrument):
    '''
    Creates a Zurich base class object, to control a Zurich Instruments lockin
    '''

    _label = 'Zurich'
    device_id = None

    def __init__(self, device_serial, in_channel = 1, meas_type='V'):
            '''
            Creates the Zurich object.
            Arguments:
            device_serial (int): Serial number of Zurich instrument
            in_channel: if None, will use both inputs (TODO).
                            Else, choose input 1 or 2.
            meas_type: 'I' or 'V'. Choose whether this channel measures current
                                (via transimpedance amplifier) or voltage.
            '''

            super().__init__()

            api_level = 5  # API level 5 necessary for MFLI scope
            self.daq, self.device_id, self.props = utils.create_api_session(
                'dev%i' % device_serial, api_level
            )

            if in_channel is None:
                raise Exception()
            self.in_channel = in_channel
            self.meas_type = meas_type


    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        self._save_dict = {'device_id': self.device_id,
                          'X': self.X,
                          'Y': self.Y,
                          'zurich_dict': self.daq.get('/', True) #  all settings
                          }
        return self._save_dict


    def __setstate__(self, state):
        keys = [
            ('_X', 'X'),
            ('_Y', 'Y'),
        ]

        for new, old in keys:
            try:
                state[new] = state.pop(old)
            except:
                pass

        self.__dict__.update(state)
        self._loaded = True


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


    def autorange(self, input_ch=0, sleep_time=5):
        self.daq.setInt('/%s/sigins/%i/autorange' %(self.device_id, input_ch), 1)  # autorange input
        time.sleep(sleep_time)  # wait for autoranging to complete


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


class HF2LI(Zurich):
    _label = 'Zurich HF2LI'


class MFLI(Zurich):
    _label = 'Zurich MFLI'
    freq_opts = [60e6, 30e6, 15e6, 7.5e6, 3.75e6, 1.88e6, 938e3, 469e3, 234e3,
        117e3, 58.6e3, 29.3e3, 14.6e3, 7.32e3, 3.66e3, 1.83e3, 916]

    '''
    MFLI - additional functionality for scope that may be different from HF2LI
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.scope = self.daq.scopeModule()
        self.scope.subscribe('/%s/scopes/0/wave' %self.device_id)

    def _setup_scope(self, freq=60e6, N=16384, input_ch=0):
        '''
        Parameters:
        freq - sampling rate (Hz). Must be in MFLI.freq_opts.
        N - Length (pts).  2^14 = 16384 by default.
        input_ch - Input channel. 0 = "Signal Input 1"; 9 = "Aux Input 2"
        '''
        scope = self.scope
        daq = self.daq

        if freq not in self.freq_opts:
            raise Exception('Frequency must be in: %s' %self.freq_opts)

        f = self.freq_opts.index(freq)

        scope.set('scopeModule/mode', 1)  # See p 49 Programming Manual:
        scope.set('scopeModule/averager/weight', 1)  # number of averages

        daq.setInt('/%s/scopes/0/time' %self.device_id, f)
        daq.setInt('/%s/scopes/0/length' %self.device_id, N)  # number of points

        daq.sync()

        daq.setInt('/%s/scopes/0/single' %self.device_id, 1)
        daq.setInt('/%s/scopes/0/channel' %self.device_id, 1)
        daq.setInt('/%s/scopes/0/channels/0/inputselect' %self.device_id, input_ch)
        daq.setInt('/dev3447/scopes/0/channels/0/bwlimit', 1)
        # To average rather than decimate signal acquired at max sampling rate
        # This avoids aliasing

        daq.sync()

        scope.set('scopeModule/clearhistory', 1)



    def get_scope_trace(self, freq=60e6, N=16384, input_ch=0):
        '''
        Returns a tuple (array of time values, array of scope input values)
        Parameters:
        freq - sampling rate (Hz). Must be in MFLI.freq_opts.
        N - Length (pts).  2^14 = 16384 by default.
        input_ch - Input channel. 0 = "Signal Input 1"; 9 = "Aux Input 2"
        '''
        self._setup_scope(freq, N, input_ch)

        scope = self.scope
        daq = self.daq

        try:  # In a try block so scope.finish() runs in finally
            daq.setInt('/%s/scopes/0/enable' %self.device_id, 1)
            daq.sync()

            scope.execute()

            while scope.progress() < 1:
                time.sleep(0.01)

            daq.setInt('/%s/scopes/0/enable' %self.device_id, 0)
            rawdata=scope.read()
        finally:
            scope.finish()

        data = rawdata[self.device_id]['scopes']['0']['wave'][0][0]

        data_array = data['wave'][0].reshape(N)

        chscl = data['channelscaling'][0]
        if chscl != 1:
            print('Warning: channel scaling is %f. \
                You are probably using mode "0"' %chscl)
            data_array *= chscl

        dt = data['dt']

        time_array = np.linspace(0, dt*N, N)

        return time_array, data_array
