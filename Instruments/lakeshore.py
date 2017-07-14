from .instrument import VISAInstrument

class Lakeshore372(VISAInstrument):
    '''
    Driver to communicate with LakeShore Model 372 AC Resistance Bridge & 
    Temperature Controller for the BlueFors dilution refrigerator
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

    def getchsettings(self):
        '''
        Gets all channel settings
        
        returns dictionary, key is channel number, value is 
        array as in get_channel
        '''
        cmd = "INSET?"
        def insetfunct (s):
            return [int(x) for x in s.split(',')]

        return self._loop_over_chans(cmd, insetfunct)

    def setchsettings(self, chsettings):
        '''
        sets all channel settings

        arguments
            chsettings: (dict) {1: [ <off/on>,<dwell>,<pause>,
                                    <curve number>,<tempco> ],
                                    ... 
                               }
        returns
            none
        '''
        for i in chsettings.keys():
            self.set_channel(i, *chsettings[i])


    def disable_others(self,channel):
        '''
        Disables all other channels except given channel
        
        arguments
            channel: (int) channel number to enable

        returns
            none
        '''
        for i in self._channel_names.keys():
            if (i == channel):
                continue;
            chsetting = self.get_channel(i)
            self.set_channel(i,0,
                                chsetting[1],
                                chsetting[2],
                                chsetting[3],
                                chsetting[4])
    def enable_all(self):
        '''
        Enable all channels

        arguements
            none

        returns
            none
        '''
        for i in self._channel_names.keys():
            chsetting = self.get_channel(i)
            self.set_channel(i,1,
                                chsetting[1],
                                chsetting[2],
                                chsetting[3],
                                chsetting[4])
    def disable_ch(self, channel):
        self._offon_ch(channel, 0)

    def enable_ch(self, channel):
        self._offon_ch(channel, 1)

    def _offon_ch(self, channel, offon):
        a = self.get_channel(channel);
        a[0] = offon;
        self.set_channel(channel, *a)



    def set_channel(self, channel, 
                   offon=1, dwell=30, pause=10, curvenumber=0, tempco=1):
        '''
        Sets channel parameters

        arguments:
            channel    : channel number, 1-16, 0 is all channels
            offon      : channel is disabled or enabled.  0=disabled, 1=enabled
            dwell      : autoscan dwell time, 1-200s
            pause      : pause time, 3-200 s
            curvenumber: which curve, 0=nocurve, 1-59 standard/user curves
            tempco     : temperature coefficient for temperature control if no
                         curve is selected: 1=negative, 2=positive
        '''
        self.write("INSET {0},{1},{2},{3},{4},{5}".format(
                    channel, offon, dwell, pause, curvenumber, tempco))

    def get_channel(self, channel):
        '''
        Gets the channel parameter

        arguments:
            channel: int, channel number

        returns:
            [ <off/on>,<dwell>,<pause>,<curve number>,<tempco> ]

            see set_channel for details
        '''
        s = self.ask("INSET? {0}".format(channel))
        a = [int(x) for x in s.split(',')]
        return a


    def _loop_over_chans(self, cmd, conversion_type):
        d = {}
        for chan in self._channel_names.keys():
            d[chan] = conversion_type(self.ask('%s %i' %(cmd, chan)))
        return d
