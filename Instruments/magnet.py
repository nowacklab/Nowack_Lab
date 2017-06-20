import visa, time, numpy as np, re
from .instrument import Instrument

_BMAX = {'x': 1, 'y': 1, 'z': 6} # T
_IMAX = {'x': 50.73, 'y': 50.63, 'z': 50.76} # A
_COILCONST = {'x': 0.01971, 'y': 0.01975, 'z': 0.1182} # T/A
_IRAMPMAX = {'x': 0.067, 'y': 0.0579, 'z': 0.0357} # A/s
_BRAMPMAX = {i: _IRAMPMAX[i]*_COILCONST[i] for i in ['x','y','z']} # T/s
_VMAX = {var: 2.2 for var in ('x','y','z')} # V #FIXME?
_STATES = {
    1: "RAMPING",
    2: "HOLDING",
    3: "PAUSED",
    4: "Ramping in MANUAL UP",
    5: "Ramping in MANUAL DOWN",
    6: "ZEROING CURRENT in progress",
    7: "QUENCH!!!",
    8: "AT ZERO CURRENT",
    9: "Heating Persistent Switch",
    10: "Cooling Persistent Switch"
}

class AMI430(Instrument):
    '''
    Control for the American Magnetics AMI430 Power Supply.
    The coil constant allows translation of current to field.
    For simplicity, we do not provide setters for current parameters.
    A current setpoint may be set in the same way as a field setpoint, with
    FIELD -> CURR. See Manual for more information. The field and current
    readings/setpoints are always related by the coil constant.
    '''
    _label = 'ami430'
    _Bmax = 6
    _Imax = 50.63
    _params = ['B', 'Bset', 'Brate', 'I', 'Iset', 'Irate', 'Isupply',
                    'p_switch']

    def __init__(self, axis = 'z'):
        resource_name = "TCPIP::ami430_%saxis.nowacklab.edu::7180::SOCKET" %axis
        self.axis = axis
        self._resource = resource_name
        self._init_visa()

    def __getstate__(self):
        '''
        Set up save dictionary.
        '''
        self._save_dict = {param:getattr(self, param) for param in self._params}
        return self._save_dict

    def __setstate__(self, state):
        '''
        Load private variables for properties
        '''

        for param in self._params:
            state['_'+param] = state.pop(param)

        self.__dict__.update(state)

    def _init_visa(self):
        '''
        Initialize the visa handle.
        '''
        self._visa_handle = visa.ResourceManager().open_resource(self._resource)
        self._visa_handle.read_termination = '\n'
        # Receive welcome and connect messages.
        self._visa_handle.read()
        self._visa_handle.read()

    @property
    def B(self):
        '''
        Read the field in Tesla.
        '''
        self._B = self.ask('FIELD:MAG?')/10 # kG to T
        return self._B

    @B.setter
    def B(self, value):
        '''
        Set the field setpoint in Tesla.
        '''
        self.write('CONF:FIELD TARG %g' %value*10) # T to kG

    @property
    def Bset(self):
        '''
        Get the field setpoint.
        '''
        self._Bset = self.ask('FIELD:TARG?')/10 # kG to T
        return self._Bset

    @property
    def Brate(self):
        '''
        Get the field ramp rate (T/s)
        '''
        self._Brate = self.ask('RAMP:RATE:FIELD:1?')
        return self._Brate

    @Brate.setter
    def Brate(self, value):
        '''
        Set the field ramp rate (T/s)
        '''
        self.write('CONF:RAMP:RATE:FIELD 1,%g' %value*10) # T/s to kG/s

    @property
    def I(self):
        '''
        Read the current in Amperes.
        '''
        self._I =self.ask('CURR:MAG?')
        return self._I

    @property
    def Iset(self):
        '''
        Get the current setpoint.
        '''
        self._Iset = self.ask('CURR:TARG?')
        return self._Iset

    @property
    def Irate(self):
        '''
        Get the current ramp rate (A/s)
        '''
        self._Irate = self.ask('RAMP:RATE:CURR:1?')
        return self._Irate

    @property
    def Isupply(self):
        '''
        Get the power supply current (A)
        '''
        self._Isupply = self.ask('CURR:SUPP?')
        return self._Isupply

    @property
    def p_switch(self):
        '''
        Is persistent switch enabled? True/False
        '''
        self._p_switch = bool(self.ask('PSwitch?'))
        return self._p_switch

    @p_switch.setter
    def p_switch(self, value):
        '''
        Enable (True) or disable (False) persistent switch
        '''
        self.write('PSwitch %i' %value)

    @property
    def status(self):
        '''
        Get the present status of the system.
        '''
        state = self.ask('STATE?')
        self._status = _STATES[state]
        return self._status

    def pause(self):
        '''
        Pause the ramping of the magnetic field.
        '''
        self.write('PAUSE')

    def ramp_to_field(self, B, rate=None):
        '''
        Heat up persistent switch and ramp the field with set ramp rate.
        rate in T/s. None = max.
        '''
        self.p_switch = True
        self.B = B
        if rate is None:
            rate = _BRAMPMAX[self.axis]
        self.Brate = rate
        self.wait()
        self.start_ramp()

    def shutdown(self, ramp_rate=None):
        '''
        Turn on persistent switch, ramp to zero, turn off persistent switch.
        ramp_rate in T/s. None = max.
        '''
        self.p_switch = True
        self.wait()
        self.Brate = ramp_rate
        self.zero()
        self.wait()
        self.p_switch = False

    def start_ramp(self):
        '''
        Start ramping to the target field.
        '''
        self.write('RAMP')

    def wait(self, timeout=800, interval=0.1):
        '''
        Wait for holding.
        '''
        tstart = time.time()
        while self.status not in ('HOLDING', 'PAUSED', 'AT ZERO CURRENT'):
            time.sleep(interval)
            if time.time()-tstart > timeout:
                raise Exception('Timed out waiting for holding.')

    def zero(self):
        '''
        Ramp field to zero at the ramp rate presently set.
        '''
        self.write('ZERO')



class Magnet(Instrument):
    def __init__(self):
        self.x = AMI430('x')
        self.y = AMI430('y')
        self.z = AMI430('z')
