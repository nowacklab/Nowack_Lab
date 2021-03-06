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

            self.setup_OL_detect()


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

    # @property
    # def TA_gain(self):
    #     '''
    #     Inflexible. Get transimpedance amplifier gain if set up for input 0
    #     '''
    #     param = '/%s/zctrls/0/tamp/0/currentgain' %self.device_id
    #     return self.get_setting(param)[0]


    def autorange(self, input_ch=0, sleep_time=5, force=False):
        '''
        force: force autorange even if no overload
        '''
        if self.get_OL(input_ch) or force:
            range1 = self.get_input_range(input_ch)
            self.daq.setInt('/%s/sigins/%i/autorange' %(self.device_id, input_ch), 1)  # autorange input
            time.sleep(.5)
            range2 = self.get_input_range(input_ch)
            if range1 == range2:
                return
            time.sleep(sleep_time-.5)  # wait for autoranging to complete


    def get(self, param):
        '''
        Get a parameter from the lockin.
        '''
        demod_num = (self.in_channel-1)*3

        return self.daq.getSample('/%s/demods/%i/sample' %(self.device_id, demod_num))[param]
        # self.in_channel


    def get_OL(self, input_ch=0):
        '''
        If input is overloading, returns True. See setup_OL_detect for description.
        '''
        dio = self.daq.getDIO('/%s/dios/%i/input' %(self.device_id, input_ch))['dio'][0]
        return dio == 0x0F


    def get_input_range(self, input_ch=0):
        return self.get_setting('/%s/sigins/%i/range' %(self.device_id, input_ch))


    def get_setting(self, param):
        '''
        Bypass the Zurich's annoying get protocol.
        '''
        return self.daq.get(param, True)[param]['value'][0]


    def setup_OL_detect(self):
        '''
        Use the threshold unit to send a binary 1 to digital input if detect an overload on the input.
        This is the only way I could figure out how to detect an overload.
        NOTE: This isn't perfect. If overloading only on the high side (for example), won't detect reliably
        '''
        try:
            # set zeroth TU to Input overload (V)
            self.daq.setInt('/dev3447/tu/thresholds/0/input', 53)
            # set up DIO to watch threshold outputs
            self.daq.setInt('/dev3447/dios/0/mode', 3)
        except:
            print('OL detect not set up.')

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


    def get_demod_continuous(self, freq=60e6, N=16384, demod=0):
        '''
        Returns arrays of time values, X components, and Y components.

        freq - sampling rate (Hz). Arbitrary value.
        N - length (pts). 2^14 = 16384 by default.
        demod - Demod number. 0 by default.
        '''
        h = self.daq.dataAcquisitionModule()
        h.set("dataAcquisitionModule/device", self.device_id)
        h.set("dataAcquisitionModule/type", 0) # continuous acquisition
        h.set("dataAcquisitionModule/grid/mode", 2) # linear interpolation between samples if sampling rate does not match
        h.set("dataAcquisitionModule/count", 1) # get all data in one shot
        h.set("dataAcquisitionModule/duration", N/freq) # acquisition time (seconds)
        h.set("dataAcquisitionModule/grid/cols", N) # number of points = sample rate * duration

        px = '/%s/demods/%i/sample.x' %(self.device_id, demod)
        py = '/%s/demods/%i/sample.y' %(self.device_id, demod)
        h.subscribe(px)
        h.subscribe(py)

        # Start recording data.
        h.execute()
        while not h.finished():
            time.sleep(.1)
        data = h.read(True)
        # Destroy the instance of the module.
        h.clear()

        clockbase = float(self.daq.getInt("/{}/clockbase".format(self.device_id)))
        timestamps = data[px][0]['timestamp'][0]
        ts = (timestamps-timestamps[0])/clockbase
        xs = data[px][0]['value'][0]
        ys = data[py][0]['value'][0]

        return ts, xs, ys

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
