from .instrument import VISAInstrument

class Lakeshore372(VISAInstrument):
    '''
    Driver to communicate with LakeShore Model 372 AC Resistance Bridge & Temperature Controller for the BlueFors dilution refrigerator
    '''
    _label = 'Lakeshore Model 372'
    _strip = '\r'
    _P = {}
    _R = {}
    _status = {}
    _T = {}

    def __init__(self, host = '192.168.100.143', port=7777):
        self._init_visa('TCPIP::%s::%i::SOCKET' %(host, port), termination='\n')
        self._channel_names = {
            1: '50K',
            2: '4K',
            3: 'Magnet',
            5: 'Still',
            6: 'MXC',
            7: 'User1',
            8: 'User2'
        }

    @property
    def P(self):
        '''
        Get the power (W) of input channels as a dictionary.
        '''
        self._P = self._loop_over_chans('RDGPWR?', float)# "ReaDinG PoWeR"
        return self._P


    @property
    def R(self):
        '''
        Get the resistance (Ohm) of input channels as a dictionary.
        '''
        self._R = self._loop_over_chans('RDGR?', float)# "ReaDinG Resistance"
        return self._R

    @property
    def status(self):
        '''
        Get the status of all input channels.
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

        b = self._loop_over_chans('RDGST?', int) # "ReaDinG STatus"
        # Loop over channels and add status messages according to the status byte.
        for chan in self._channel_names.keys():
            status_message = ''
            binlist = [int(x) for x in '{:08b}'.format(b[chan])] # to list of 1s and 0s
            for i, bit in enumerate(binlist):
                if bit:
                    status_message += msgs[i] + '; ' # add status message
            if status_message == '':
                status_message = 'OK'
            self._status[chan] = status_message.rstrip('; ') # remove if unnecessary
        return self._status

    @property
    def T(self):
        '''
        Get the temperature (K) reading of input channels as a dictionary.
        '''
        self._T = self._loop_over_chans('RDGK?', float)# "ReaDinG Kelvin"
        return self._T

    def _loop_over_chans(self, cmd, conversion_type):
        d = {}
        for chan in self._channel_names.keys():
            d[chan] = conversion_type(self.ask('%s %i' %(cmd, chan)))
        return d
