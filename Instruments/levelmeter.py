import time
from .instrument import VISAInstrument

class AMI1700(VISAInstrument):
    '''
    AMI Model 1700 Helium level meter
    '''
    _level = None
    def __init__(self, ip='10.84.231.40', port=7180):
        '''
        Arguments:
        ip - IP address (static)
        port - 7180 is specified by AMI
        '''
        resource = 'TCPIP::%s::%s::SOCKET' %(ip, port)
        self._init_visa(resource, termination='\r\n')


    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        self._save_dict = {
            '_level': self.level()
        }
        return self._save_dict


    def continuous(self):
        '''
        Continuously measure the helium level.
        '''
        self.query('MEAS:HE:CONT')
        time_limit = float(self.query('HE:TIME?'))
        print('Continously measuring helium level for the next %i minutes.' %time_limit)

    def continuous_time_limit(self, time_lim_minutes):
        '''
        Set the continuous sampling time limit (minutes)
        '''
        raise Exception('Command does not work.')
        self.query('CONF:HE:TIME %i' %time_lim_minutes)

    def level(self):
        '''
        Returns the last measured Helium level (%)
        '''
        self._level = float(self.query('MEAS:HE:LEV?'))
        return self._level

    def sample(self):
        '''
        Sample the current helium level and hold.
        Can be used to update the current measurement or to abort continous sampling.
        '''
        self.query('MEAS:HE:SAMP')
        print('Measuring helium level...')
        time.sleep(5)
        return self.level()
