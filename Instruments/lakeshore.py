from .instrument import VISAInstrument
import numpy as np
import visa

class LakeshoreChannel(VISAInstrument):
    '''
    Channel objected for the LakeShore Model 372 AC Resistance bridge.
    The LakeShore372 class defined below contains up to 8 channel objects
    representing each of the input channels on the instrument.
    '''
    _label = 'LakeshoreChannel'
    _num = 0
    _strip = '\r'
    _insets = ['enabled', 'dwell', 'pause', 'curve_num', 'temp_coef']

    def __init__(self, visa_handle, num, label):
        '''
        Arguments:
            visa_handle: VISA handle created for the LakeShore372
            num: Channel number.
            label: Channel label.
        '''
        self._visa_handle = visa_handle
        self._num = num
        self._label = label

        # Properties for all the channel settings
        for i, var in enumerate(self._insets):
            setattr(LakeshoreChannel, var, property(
                fget = eval('lambda self: self._get_inset()[%i]' %i),
                fset = eval('lambda self, value: self._set_inset(%s = value)'
                %var)
            ))


    def __getstate__(self):
        self._save_dict = {
            'Channel number': self._num,
            'Channel label': self._label,
            'Channel enabled?': self.enabled,
            'Channel being scanned?': self.scanned,
            'power': self.P,
            'resistance': self.R,
            'temperature': self.T,
            'status': self.status,
            'dwell time': self.dwell,
            'pause': self.pause,
            'curve number': self.curve_num,
            'temperature coefficient 1pos, 2neg': self.temp_coef,
        }
        return self._save_dict


    def __setstate__(self, state):
        state['_num'] = state.pop('Channel number')
        state['_label'] = state.pop('Channel label')
        state['_enabled'] = state.pop('Channel enabled?')
        state['_scanned'] = state.pop('Channel being scanned?')
        state['_P'] = state.pop('power')
        state['_R'] = state.pop('resistance')
        state['_T'] = state.pop('temperature')
        state['_status'] = state.pop('status')
        state['_dwell'] = state.pop('dwell time')
        state['_pause'] = state.pop('pause')
        state['_curve_num'] = state.pop('curve number')
        state['_temp_coef'] = state.pop('temperature coefficient 1pos, 2neg')

        self.__dict__.update(state)


    def _get_inset(self):
        '''
        Returns all the parameters returned by the INSET? query.
        These are channel settings in an array:
            [enabled/disabled, dwell, pause, curve number, tempco]
        '''
        inset = self.ask('INSET? %i' %self._num)
        inset = [int(x) for x in inset.split(',')]
        inset[0] = bool(inset[0]) # make enabled True/False
        for i, var in enumerate(self._insets):
            setattr(self, '_'+var, inset[i])
        return inset


    def _set_inset(self, enabled = None, dwell = None, pause = None,
                    curve_num = None, temp_coef = None
        ):
        '''
        Set any number of channel settings uing the INSET command.
        For each keyword argument, None indicates not to change that setting.

        Parameters:
            enabled (bool): enable or disable the channel
            dwell (float): Dwell time (1-200 s)
            pause (float): Change pause time (3-200 s)
            curve_num (int 0-59): Which curve the channel uses. 0 = no curve.
            temp_coef (int): Temp. coefficient used if no curve; 1 = -, 2 = +
        '''
        inset = self._get_inset()
        args = [enabled, dwell, pause, curve_num, temp_coef]

        for i, arg in enumerate(args):
            if arg is None:
                args[i] = inset[i]

        cmd = 'INSET %i,%i,%i,%i,%i,%i' %(self._num, *args)
        self.write(cmd)


    @property
    def P(self):
        '''
        Get the power (W) of this input channel.
        '''
        if self.status == 'OK':
            self._P = float(self.ask('RDGPWR? %i' %self._num))
        else:
            self._P = np.nan
        return self._P

    @property
    def R(self):
        '''
        Get the resistance (R) of this input channel.
        '''
        if self.status == 'OK':
            self._R = float(self.ask('RDGR? %i' %self._num))
        else:
            self._R = np.nan
        return self._R

    @property
    def scanned(self):
        '''
        Is this particular channel being scanned?
        Returns True/False
        '''
        # SCAN? returns ##,#. The first number is channel being scanned
        scan = self.ask('SCAN?')
        scan = int(scan.split(',')[0])
        self._scanned = (scan == self._num) # True or False
        return self._scanned

    def scan(self, autoscan=True):
        '''
        Start scanning this channel.

        autoscan: whether to automatically loop through channels
        '''
        self.write('SCAN %i,%i' %(self._num, autoscan))

    @property
    def status(self):
        '''
        Get the status the input channel.
        Status messages are standard to LakeShore, except "OK" means there are
        no status messages.
        '''
        msgs = [
            'T. UNDER',
            'T. OVER',
            'R. UNDER',
            'R. OVER',
            'VDIF OVL',
            'VMIX OVL',
            'VCM OVL',
            'CS OVL'
        ]
        b = int(self.ask('RDGST? %i' %self._num)) # "ReaDinG STatus"

        status_message = ''
        binlist = [int(x) for x in '{:08b}'.format(b)] # to list of 1s and 0s
        for i, bit in enumerate(binlist):
            if bit:
                status_message += msgs[i] + '; ' # add status message
        if status_message == '':
            status_message = 'OK'
        self._status = status_message.rstrip('; ') # remove if unnecessary
        return self._status

    @property
    def T(self):
        '''
        Get the temperature (K) reading of input channels as a dictionary.
        '''
        if self.status == 'OK':
            self._T = float(self.ask('RDGK? %i' %self._num))
        else:
            self._T = np.nan
        return self._T


class Lakeshore372(VISAInstrument):
    '''
    Driver to communicate with LakeShore Model 372 AC Resistance Bridge & Temperature Controller for the BlueFors dilution refrigerator
    '''
    _label = 'Lakeshore Model 372'
    _strip = '\r'
    _channel_names = {
        1: '50K',
        2: '4K',
        3: 'Magnet',
        5: 'Still',
        6: 'MXC',
        7: 'User1',
        8: 'User2'
    }

    def __init__(self, host = '192.168.100.143', usb=False, com=72, baud_rate=57600, port=7777):
        if usb:
            self._init_visa("COM{}".format(com))
            self._visa_handle.parity=visa.constants.Parity(1) # odd parity
            self._visa_handle.data_bits = 7
            self._visa_handle.baud_rate = 57600
        else:
            self._init_visa('TCPIP::%s::%i::SOCKET' %(host, port), termination='\n')
        #self._init_visa("COM{}".format(host))

        # Make channel objects
        for c, n in self._channel_names.items():
            setattr(self, 'chan%i' %c, LakeshoreChannel(self._visa_handle, c, n))

        # Set properties to get/set all params
        params = ['P', 'R', 'T', 'status', 'scanned', *self.chan1._insets]
        for p in params:
            setattr(self, '_' + p, {}) # empty dictionary for later
            setattr(Lakeshore372, p,
                property(fget = eval("lambda self: self._get_param('%s')" %p),
                    fset = eval('lambda self, v: self._set_param("%s", v)' %p)
                )
            )

    def __getstate__(self):
        self._save_dict = {
            'chan%i' %i: getattr(self, 'chan%i' %i)
            for i in self._channel_names.keys()
        }

        return self._save_dict


    def _get_param(self, param):
        '''
        Get a parameter from all channels, returned as a dictionary.
        '''
        setattr(self, '_' + param,
            {c: getattr(getattr(self, 'chan%i' %c), param)
                for c in self._channel_names}
        )
        return getattr(self, '_' + param)

    def _set_param(self, param, d):
        '''
        Set the same parameter for all channels with a dictionary
        '''
        for c in d.keys():
            getattr(self, '_' + param)[c] = d[c]
            setattr(getattr(self, 'chan%i' %c), param, d[c])


    def enable_all(self):
        '''
        Enable all channels.
        '''
        enabled_now = self.enabled
        self.enabled = {c: True for c in self._channel_names.keys()
                if enabled_now[c] is False # to speed things up
            }


    def enable_only(self, channel):
        '''
        Enable only the designated channel.
        All other channels will be disabled.

        channel: the channel number to be enabled.
        '''
        d = {c: False for c in self._channel_names.keys()}
        d[channel] = True
        self.enabled = d


    def scan(self, channel, autoscan=True):
        '''
        Start scanning a particular channel.

        channel: channel number to scan
        autoscan: whether to automatically loop through channels
        '''
        getattr(self, 'chan%i' %self._num).scan(autoscan)

    @property
    def pid_setpoint(self):
        '''
        Get setpoint for PID
        '''
        return float(self.ask('SETP? 0')) #0 is sample heater

    @pid_setpoint.setter
    def pid_setpoint(self, setpoint):
        '''
        Set setpoint for PID.  Should be float.  In preferred units
        of the setpoint.  Kelvin, unless changed
        '''
        self.write('SETP 0,{0}'.format(float(setpoint)))

    _MODE_LOOKUP = {
            0: 'Off',
            1: 'Monitor Out',
            2: 'Manual',
            3: 'Zone',
            4: 'Still',
            5: 'PID',
            6: 'Warm up'
    }

    @property
    def sample_heater(self):
        s = self.ask('OUTMODE? 0').split(',')
        return self._MODE_LOOKUP[int(s[0])]

    @sample_heater.setter
    def sample_heater(self, s):
        mode = -1 
        try:
            mode = int(s)
        except:
            l    = self._MODE_LOOKUP.items()
            for key, value in l:
                if s.lower() == value.lower():
                    mode = key
        if mode == -1:
            print("Invalid mode: {0}".format(s))
            print("Mode must be in a key or value in _MODE_LOOKUP:")
            print(self._MODE_LOOKUP)
            return 

        settings = self.ask("OUTMODE? 0").split(',')
        self.write("OUTMODE 0,{0},{1},{2},{3},{4},{5}".format(
                    mode,
                    settings[1],
                    settings[2],
                    settings[3],
                    settings[4],
                    settings[5]
                   ))
        return
    @property
    def sample_heater_ch(self):
        return int(self.ask('OUTMODE? 0').split(',')[1])

    @sample_heater_ch.setter
    def sample_heater_ch(self, ch):
        if type(ch) == int and ch>=1 and ch<=16:
            settings = self.ask("OUTMODE? 0").split(',')
            self.write("OUTMODE 0,{0},{1},{2},{3},{4},{5}".format(
                        settings[0],
                        ch,
                        settings[2],
                        settings[3],
                        settings[4],
                        settings[5]
                      )
            )
        else:
            print("Invalid channel: {0}".format(ch))

    _RANGE_LOOKUP = {
            0: 'Off',
            1: '31.6 uA',
            2: '100 uA',
            3: '316 uA',
            4: '1.00 mA',
            5: '3.16 mA',
            6: '10.0 mA',
            7: '31.6 mA',
            8: '100 mA'
    }
    @property
    def heater_range(self):
        s = self.ask('RANGE? 0').split(',')
        return self._RANGE_LOOKUP[int(s[0])]

    @heater_range.setter
    def heater_range(self, s):
        mode = -1 
        try:
            mode = int(s)
        except:
            l    = self._RANGE_LOOKUP.items()
            for key, value in l:
                if s.lower() == value.lower():
                    mode = key
        if mode == -1:
            print("Invalid range: {0}".format(s))
            print("Range must be in a key or value in _RANGE_LOOKUP:")
            print(self._RANGE_LOOKUP)
            return 

        self.write("RANGE 0,{0}".format(mode))
        return

    @property
    def ramp(self):
        """Ramp rate for temperature control."""
        return self.ask("RAMP? 0").splot(",")


    @ramp.setter
    def ramp(self, rate):
        """Set the ramp rate."""
        data = "RAMP0,1,{}[term]".format(rate)
        self.write(data)
