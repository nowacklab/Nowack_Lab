from .instrument import VISAInstrument
import numpy as np

class LakeshoreChannel(VISAInstrument):
    '''
    Channel objected for the LakeShore Model 372 AC Resistance bridge.
    The LakeShore372 class defined below contains up to 8 channel objects
    representing each of the input channels on the instrument.
    '''
    _label = 'LakeshoreChannel'
    _num = 0
    _strip = '\r'

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

    @property
    def enabled(self):
        '''
        Is this particular channel enabled?
        Returns True/False
        '''
        # INSE? returns a bunch of stuff. The first number is 0/1 if (dis/en)abled
        inset = self.ask('INSET? %i' %self._num)
        self._enabled = bool(inset.split(',')[0])
        return self._enabled

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

    def __init__(self, host = '192.168.100.143', port=7777):
        self._init_visa('TCPIP::%s::%i::SOCKET' %(host, port), termination='\n')

        # Make channel objects
        for c, n in self._channel_names.items():
            setattr(self, 'chan%i' %c, LakeshoreChannel(self._visa_handle, c, n))

        # Set properties to get all params
        for v in ['P', 'R', 'T', 'status', 'scanned', 'enabled']:
            setattr(Lakeshore372, v,
                property(fget=eval("lambda self: self._get_param('%s')" %v))
            )

    def _get_param(self, param):
        '''
        Get a parameter from all channels, returned as a dictionary.
        '''
        setattr(self, '_' + param,
            {c: getattr(getattr(self, 'chan%i' %c), param)
                for c in self._channel_names}
        )
        return getattr(self, '_' + param)

    def scan(self, channel, autoscan=True):
        '''
        Start scanning a particular channel.

        channel: channel number to scan
        autoscan: whether to automatically loop through channels
        '''
        getattr(self, 'chan%i' %self._num).scan(autoscan)
