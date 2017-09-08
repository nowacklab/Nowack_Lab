import visa, time, numpy as np, re
from .instrument import Instrument, VISAInstrument

# Parameters for the 6-1-1 vector magnet on the Bluefors system
_BMAX = {'x': 1, 'y': 1, 'z': 6} # T
_IMAX = {'x': 50.73, 'y': 50.63, 'z': 50.76} # A
_COILCONST = {'x': 0.01971, 'y': 0.01975, 'z': 0.1182} # T/A
_IRATEMAX = {'x': 0.067*60, 'y': 0.0579*60, 'z': 0.0357*60} # A/min
_BRATEMAX = {i: _IRATEMAX[i]*_COILCONST[i] for i in ['x','y','z']} # T/min
_VMAX = {var: 2.2 for var in ('x','y','z')} # V #FIXME?


class AMI430(VISAInstrument):
    '''
    Control for the American Magnetics AMI430 Power Supply.
    The coil constant allows translation of current to field.
    For simplicity, we do not provide setters for current parameters.
    A current setpoint may be set in the same way as a field setpoint, with
    FIELD -> CURR. See Manual for more information. The field and current
    readings/setpoints are always related by the coil constant.
    '''
    _label = 'ami430'
    _params = ['B', 'Bset', 'Brate', 'I', 'Iset', 'Irate', 'Isupply',
                    'p_switch']
    _Bmax = 1  # T
    _Imax = 50.63  # A
    _coilconst = .1182  # T/A
    _Iratemax = .0357*60  # A/min
    _Bratemax = _coilconst*_Iratemax
    _Vmax = 2.2

    def __init__(self, resource=None, axis = 'z'):
        if resource is None:
            resource = 'TCPIP::ami430_%saxis.nowacklab.edu::7180::SOCKET' %axis
        self._resource = resource
        self._init_visa(resource)

        self.write('CONF:FIELD:UNITS 1') # ensure units are in Tesla

        self.axis = axis

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

    def _init_visa(self, resource):
        '''
        Initialize the visa handle.
        '''
        super()._init_visa(resource, termination = '\r\n')
        # Receive welcome and connect messages.
        self._visa_handle.read()
        self._visa_handle.read()

    @property
    def B(self):
        '''
        Read the field in Tesla.
        '''
        self._B = float(self.ask('FIELD:MAG?'))
        return self._B

    @B.setter
    def B(self, value):
        '''
        Set the field setpoint in Tesla.
        '''
        self.Bset = value

    @property
    def Bset(self):
        '''
        Get the field setpoint.
        '''
        self._Bset = float(self.ask('FIELD:TARG?'))
        return self._Bset

    @Bset.setter
    def Bset(self, value):
        '''
        Set the field setpoint in Tesla.
        '''
        if abs(value) > self._Bmax:
            print('Warning! %g T setpoint too high! Setpoint set to %g T.'
                                            %(value, self._Bmax*np.sign(value)))
            value = self._Bmax*np.sign(value)
        self.write('CONF:FIELD TARG %g' %value)

    @property
    def Brate(self):
        '''
        Get the field ramp rate (T/min)
        '''
        s = self.ask('RAMP:RATE:FIELD:1?') # returns 'Brate,Bmax'
        s = s.split(',') # now we have ['Brate','Bmax']
        self._Brate = float(s[0])
        return self._Brate

    @Brate.setter
    def Brate(self, value):
        '''
        Set the field ramp rate (T/min)
        '''
        if value > self._Bratemax:
            print('Warning! %g T/min ramp rate too high! Rate set to %g T/min.'
                                                    %(value, self._Bratemax))
            value = self._Bratemax
        self.write('CONF:RAMP:RATE:FIELD 1,%g,%g' %(value, self._Bmax))

    @property
    def I(self):
        '''
        Read the current in Amperes.
        '''
        self._I = float(self.ask('CURR:MAG?'))
        return self._I

    @property
    def Iset(self):
        '''
        Get the current setpoint.
        '''
        self._Iset = float(self.ask('CURR:TARG?'))
        return self._Iset

    @property
    def Irate(self):
        '''
        Get the current ramp rate (A/s)
        '''
        s = self.ask('RAMP:RATE:CURR:1?') # returns 'Irate,Imax'
        s = s.split(',') # now we have ['Irate','Imax']
        self._Irate = float(s[0])
        return self._Irate

    @Irate.setter
    def Irate(self, value):
        '''
        Set the current ramp rate (A/s)
        '''
        if value > self._Iratemax:
            print('Warning! %g A/s ramp rate too high! Rate set to %g A/s.'
                                                    %(value, self._Iratemax))
            value = self._Iratemax
        self.write('CONF:RAMP:RATE:CURR 1,%g,%g' %(value, self._Imax))

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
        states = {
            1: 'RAMPING',
            2: 'HOLDING',
            3: 'PAUSED',
            4: 'Ramping in MANUAL UP',
            5: 'Ramping in MANUAL DOWN',
            6: 'ZEROING CURRENT in progress',
            7: 'QUENCH!!!',
            8: 'AT ZERO CURRENT',
            9: 'Heating Persistent Switch',
            10: 'Cooling Persistent Switch'
        }

        state_num = int(self.ask('STATE?'))
        self._status = states[state_num]
        return self._status

    def pause(self):
        '''
        Pause the ramping of the magnetic field.
        '''
        self.write('PAUSE')

    def ramp_to_field(self, B, wait=False, rate=None):
        '''
        Heat up persistent switch and ramp the field with set ramp rate.
        rate in T/min. None = use rate already set.
        '''
        self.p_switch = True
        self.B = B
        if rate is not None:
            self.Brate = rate
        print('Waiting to heat persistent switch')
        while self.status == 'Heating Persistent Switch':
            time.sleep(1)
        print('Done waiting to heat persistent switch')
        self.start_ramp()
        if wait:
            self.wait()

    def shutdown(self, ramp_rate=None):
        '''
        Turn on persistent switch, ramp to zero, turn off persistent switch.
        ramp_rate in T/min. None = use rate already set.
        '''
        self.p_switch = True
        self.wait()
        if rate is not None:
            self.Brate = rate
        self.zero()
        self.wait()
        self.p_switch = False

    def start_ramp(self):
        '''
        Start ramping to the target field.
        '''
        self.write('RAMP')

    def wait(self, timeout=1800, interval=0.1):
        '''
        Wait for holding.
        '''
        print('Magnet waiting for holding.')
        tstart = time.time()
        while self.status not in ('HOLDING', 'PAUSED', 'AT ZERO CURRENT'):
            time.sleep(interval)
            if time.time()-tstart > timeout:
                raise Exception('Timed out waiting for holding.')
        print('Done waiting.')

    def zero(self):
        '''
        Ramp field to zero at the ramp rate presently set.
        '''
        self.write('ZERO')



class AMI420(AMI430):
    '''
    Control for the American Magnetics AMI420 Power Supply.
    Modified AMI430 driver. This is configured for Phil system in the Parpia lab
    '''
    _label = 'ami420'
    _params = ['B', 'Bset', 'Brate', 'I', 'Iset', 'Irate', 'p_switch']

    _Bmax = 6  # T
    _Imax = 46  # A
    _coilconst = .1331  # T/A
    _Iratemax = .0751*60  # A/min
    _Bratemax = _coilconst*_Iratemax
    _Vmax = 1

    def __init__(self, gpib_address=22):
        self._resource = 'GPIB::%02i::INSTR' %gpib_address
        VISAInstrument._init_visa(self, self._resource)

    @property
    def Bset(self):
        '''
        Get the field setpoint.
        '''
        self._Bset = float(self.ask('FIELD:PROG?'))
        return self._Bset

    @Bset.setter
    def Bset(self, value):
        '''
        Set the field setpoint in Tesla.
        '''
        raise Exeception('not working')
        if abs(value) > self._Bmax:
            print('Warning! %g T setpoint too high! Setpoint set to %g T.'
                                            %(value, self._Bmax*np.sign(value)))
            value = self._Bmax*np.sign(value)
        self.write('CONF:FIELD PROG %g' %value)

    @property
    def Iset(self):
        '''
        Get the current setpoint.
        '''
        self._Iset = float(self.ask('CURR:PROG?'))
        return self._Iset

    @property
    def Brate(self):
        '''
        Get the field ramp rate (T/min)
        '''
        self._Brate = float(self.ask('RAMP:RATE:FIELD?') )
        return self._Brate

    @Brate.setter
    def Brate(self, value):
        '''
        Set the field ramp rate (T/min)
        '''
        if value > self._Bratemax:
            print('Warning! %g T/min ramp rate too high! Rate set to %g T/min.'
                                                    %(value, self._Bratemax))
            value = self._Bratemax
        self.write('CONF:RAMP:RATE:FIELD %g' %value)

    @property
    def Irate(self):
        '''
        Get the current ramp rate (A/s)
        '''
        self._Irate = float(self.ask('RAMP:RATE:CURR?') )
        return self._Irate

    @Irate.setter
    def Irate(self, value):
        '''
        Set the current ramp rate (A/s)
        '''
        if value > self._Iratemax:
            print('Warning! %g A/s ramp rate too high! Rate set to %g A/s.'
                                                    %(value, self._Iratemax))
            value = self._Iratemax
        self.write('CONF:RAMP:RATE:CURR %g' %value)


    @property
    def Isupply(self):
        pass

    @property
    def status(self):
        '''
        Get the present status of the system.
        '''
        states = {
            1: 'RAMPING',
            2: 'HOLDING',
            3: 'PAUSED',
            4: 'Ramping in MANUAL UP',
            5: 'Ramping in MANUAL DOWN',
            6: 'ZEROING CURRENT in progress',
            7: 'QUENCH!!!',
            8: 'Heating Persistent Switch',
            9: 'At zero current'
        }

        state_num = int(self.ask('STATE?'))
        self._status = states[state_num]
        return self._status


class Magnet(AMI430):
    _attrs = ('x', 'y', 'z', '_attrs') # attributes to get/set normally
    _active_axis = None

    def __init__(self, active_axis='z'):
        '''
        Creates objects for controlling each axis independently.
        For safety, mark one axis as active and run from this object.
        This object also enables a vector field, max 1 T.
        '''
        for i in ('x','y','z'):
            try:
                axis = setattr(self, i, AMI430(i))

                axis._Bmax = _BMAX[axis]
                axis._Imax = _IMAX[axis]
                axis._coilconst = _COILCONST[axis]
                axis._Iratemax = _IRATEMAX[axis]
                axis._Bratemax = _BRATEMAX[axis]
                axis._Vmax = _VMAX[axis]

            except:
                setattr(self, i, None)
                print('%s axis magnet not connected!' %i)
        self.set_active_axis(active_axis)

    def __del__(self):
        '''
        Destroy the object and close the visa handle for each axis.
        '''
        for i in ('x','y','z'):
            if getattr(self, i) is not None:
                getattr(self, i).close()

    def __getattr__(self, attr):
        '''
        Custom getattr to run commands from the object corresponding to the
        active axis.
        '''
        if attr in self._attrs:
            return self.__dict__[attr] # avoid using getattr
        axis_obj = self.__dict__[self._active_axis]
        return getattr(axis_obj, attr)

    def __setattr__(self, attr, value):
        '''
        Custom setattr to run commands from the object corresponding to the
        active axis.
        '''
        if attr == '_active_axis':
            raise Exception('Change active axis useing set_active_axis!')
        if attr in self._attrs:
            self.__dict__[attr] = value # avoid using setattr
            return
        axis_obj = self.__dict__[self._active_axis]
        return setattr(axis_obj, attr, value)

    def set_active_axis(self, axis):
        '''
        Set the active axis.
        All commands from this object will control that axis only.
        '''
        if self._active_axis is not None:
            if self.B != 0:
                raise Exception('Must zero field before switching active axis!')
        self.__dict__['_active_axis'] = axis

    def vector(self, Bx, By, Bz):
        '''
        Program a sweep to a vector field
        '''
        pass #TODO
