import visa
import atexit
import time
import telnetlib
import re
try:
    from PyANC350.pyanc350v4 import Positioner as ANC350Pos
except:
    print('PyANC350 not installed!')
from .instrument import Instrument

''' *** Use the Attocube class, definition is at the bottom *** '''
'''
Careful! Can only initialize one attocube Object at a time.
'''

class ANC350(Instrument):
    '''
    For remote operation of the Attocubes with the ANC350.
    Control each attocube using the "Positioner" object created.
    e.g. atto.x.V = 50
         atto.x.pos = 4000
         atto.x.move(100)
         atto.x.step(-100)
    '''
    _label = 'atto'
    _stages = ['x','y','z'] # order of axis controllers
    _pos_lims = [20000, 20000, 20000] # um (temporary until LUT calibrated)
    _instances = []

    def __init__(self, montana=None):
        '''
        Pass montana = montana.Montana().
        This will check the temperature to see if it is safe to go to 60 V.
        Else, we stay at 45 V.
        '''

        ## Use self._instances to keep track of instances of the attocube class
        ## This is necessary to delete the ANC before we make a new one.
        if len(self._instances) > 0:
            for i in self._instances:
                i.__del__() # call the __del__ method of the old instance when creating a new instance
            self._instances = []

        self.anc = ANC350Pos()

        V_lim = 70 # room temperature
        if montana:
            if montana.temperature['platform'] < 30:
                V_lim = 60 # low temperature requires more voltage to step
        else:
            print('Voltage limited to {0} V, no communication with Montana!'.format(V_lim))

        for (i,s) in enumerate(self._stages):
            setattr(self, s, Positioner(self.anc, i, V_lim=V_lim, pos_lim=self._pos_lims[i], label=s)) # makes positioners x, y, and z
            getattr(self,s).check_voltage()

        self._instances.append(self) # Add a reference to this object to the


    def __del__(self):
        try:
            if hasattr(self, 'anc'):
                if self.anc is not None:
                    print('Disconnecting ANC')
                    self.anc.disconnect()
                    del self.anc
        except:
            pass

    def __getstate__(self):
        self._save_dict = {
            'x attocube': self.x.__getstate__(),
            'y attocube': self.y.__getstate__(),
            'z attocube': self.z.__getstate__(),
        }
        return self._save_dict


    def __setstate__(self, state):
        state['x'] = state.pop('x attocube')
        state['y'] = state.pop('y attocube')
        state['z'] = state.pop('z attocube')
        self.__dict__.update(state)
        # self.anc = ANC350Pos()
        # for (i,s) in enumerate(self._stages):
        #     s = getattr(self,s)
        #     setattr(s, 'anc', self.anc) # give each positioner the ANC object


class Positioner(Instrument):
    def __init__(self, anc, num, V_lim=70, pos_lim=20000, pos_tolerance=1, label=None):
        '''
        Creates an Attocube positioner object.
        anc = A PyANC350v4.Positioner object that communciates with the ANC350
        num = Axis index. Axis numbers labeled on the ANC are num + 1
        V = stepping voltage (45 V is fine at 300 K)
        freq = stepping frequency (Hz)
        V_lim = stepping voltage limit (70 V is max for the instrument)
        label = 'x', 'y', or 'z'
        '''
        self.anc = anc
        self.num = num
        self.label = label

        self.V_lim = V_lim # voltage limit; should really set lower than this.
        self.pos_lim = pos_lim # position limit (um); target position should not exceed this value
        self.pos_tolerance = pos_tolerance # tolerance (um) that determines when target position is reached

        self.V = V_lim
        self.freq
        self.C # should run this now to collect capacitances for logging purposes.
        self.pos


    def __getstate__(self):
        self._save_dict = {
            'capacitance': self._C,
            'position tolerance': self._pos_tolerance,
            'V_lim': self.V_lim,
            'pos_lim': self.pos_lim,
            'num': self.num,
            'label': self.label
        }
        try:
            self._save_dict.update({
                    'stepping voltage': self.V,
                    'stepping frequency': self.freq,
                    'position': self.pos,
                    })
        except Exception as e: # If ANC disconnected, e.g.
            print(e)
            self._save_dict.update({
                    'stepping voltage': self._V,
                    'stepping frequency': self._freq,
                    'position': self._pos,
                    })
        return self._save_dict


    def __setstate__(self, state):
        state['_V'] = state.pop('stepping voltage')
        state['_freq'] = state.pop('stepping frequency')
        state['_C'] = state.pop('capacitance')
        state['_pos'] = state.pop('position')
        state['_pos_tolerance'] = state.pop('position tolerance')

        self.__dict__.update(state)


    @property
    def C(self):
        '''
        Measure capacitance of positioner
        '''
        time.sleep(0.1) # capacitance was locking up, maybe this helps?
        print('Measuring capacitance of positioner %s...' %self.label)
        try:
            self._C = self.anc.measureCapacitance(self.num)
        except:
            self._C = self.anc.measureCapacitance(self.num) # sometimes measuring capactiance seizes up...
        print('...done.')
        return self._C

    @property
    def V(self):
        '''
        Measure or set stepping voltage of positioner
        '''
        self._V  = self.anc.getAmplitude(self.num)
        return self._V

    @V.setter
    def V(self, v):
        if v > self.V_lim:
            raise Exception('voltage out of range, max %f V' %self.V_lim)
        elif v < 0:
            raise Exception('voltage out of range, min 0 V')
        self.anc.setAmplitude(self.num, v)
        self._V = v

    @property
    def freq(self):
        '''
        Measure or set stepping frequency of positioner
        '''
        self._freq = self.anc.getFrequency(self.num)
        return self._freq

    @freq.setter
    def freq(self, f):
        if f < 0:
            raise Exception('NO')
        self.anc.setFrequency(self.num, f)
        self._freq = f

    @property
    def pos(self):
        '''
        Measures or sets the position of the positioner (in um)
        '''
        self._pos = round(self.anc.getPosition(self.num)*1e6, 2) # convert m to um
        return self._pos

    @pos.setter
    def pos(self, new_pos):
        self.check_voltage()

        if new_pos > self.pos_lim or new_pos < 0:
            raise Exception('Position %f um out of range for positioner %s!' %(dist, self.label))

        start_pos = self.pos
        self.anc.setTargetPosition(self.num, new_pos/1e6) # convert um to m
        self.anc.setAxisOutput(self.num, enable=1, autoDisable=0)
        self.anc.startAutoMove(self.num, enable=1, relative=0)
        while abs(self.pos - new_pos) > self.pos_tolerance: # all in um
            pass # wait for the position to come within the tolerance
        time.sleep(1) # wait for position measurement to settle
        while abs(self.pos - new_pos) > self.pos_tolerance: # all in um
            pass  # wait again for position to come closer to tolerance
        time.sleep(5)
        self.anc.startAutoMove(self.num, enable=0, relative=0)
        # self.anc.setAxisOutput(self.num, enable=0, autoDisable=0)
        self._pos = new_pos

    @property
    def pos_tolerance(self):
        '''
        Measure or set position tolerance of positioner. Actually does write a value, but this code doesn't use that feature of the controller.
        '''

        return self._pos_tolerance

    @pos_tolerance.setter
    def pos_tolerance(self, value):
        self.anc.setTargetRange(self.num, value)
        self._pos_tolerance = value

    def check_voltage(self):
        '''
        Makes sure stepping voltage is lower than the limit
        '''
        if self.V > self.V_lim:
            self.V = self.V_lim
            print("Axis %s voltage was too high, set to %f" %(self.label, self.V_lim))

    def move(self, dist):
        '''
        Moves positioner a specified distance (um).
        Distance can be positive or negative.
        e.g. atto.move(-100)
        '''
        new_pos = dist + self.pos
        if new_pos > self.pos_lim or new_pos < 0:
            raise Exception('Moving %f m would make positioner %s out of range!' %(dist, self.label))
        self.pos = new_pos

    def step(self, numsteps):
        '''
        Moves a desired number of steps (can be positive or negative)
        e.g. atto.z.step(-100)
        '''
        self.check_voltage()

        if numsteps < 0:
            backward = 1
        else:
            backward = 0
        self.anc.setAxisOutput(self.num, enable=1, autoDisable=0)
        time.sleep(0.5) # wait for output to turn on

        if numsteps == 0:
            print('That won\'t get you anywhere...')

        self.anc.startContinuousMove(self.num, start=1, backward=backward)
        time.sleep(abs(numsteps)/self.freq)
        self.anc.startContinuousMove(self.num, start=0, backward=backward)


    def update_anc(self):
        '''
        Saves current parameters to the ANC350 memory. Will be recalled on startup.
        '''
        self.anc.saveParams()


class ANC300(Instrument): #open loop controller, we don't use this anymore
    '''
    THIS CONTROLLER NOT USED AS OF ~August 2016
    For remote operation of the Attocubes. Order of axes is X, Y, Z (controllers 1,2,3 are in that order).

    To test: up/down fanciness with negative signs. I think it works, but not 100%
    '''
    _stages = ['x','y','z']
    _modes = ['gnd','cap','stp']

    def __init__(self, montana, host='192.168.69.3', port=7230):
        self.host = host
        self.port = port

        self._freq = {}
        self._mode = {}
        self._V = {}
        self._cap = {}

        self.freq
        self.mode
        self.V

        self._freq_lim = 1000 # self-imposed, 10000 is true max
        self._step_lim = 5000 #self-imposed, no true max
        if montana.temperature['platform'] < 10:
            self._V_lim = 55.000 #LT limit
        else:
            self._V_lim = 40.000 #RT limit

        self.check_voltage()

        atexit.register(self.stop)  # will stop all motion if program quits

    def help(self):
        msg = self.send('help')
        print(msg)

    @property
    def freq(self):
        for i in range(3):
            msg = self.send('getf %i' %(i+1)) # i+1 -> controllers labeled 1,2,3, not 0,1,2
            self._freq[self._stages[i]] = int(self._getValue(msg))
        return self._freq

    @freq.setter
    def freq(self, f):
        for key, value in f.items():
            if value > self._freq_lim:
                raise Exception('frequency out of range, max %i Hz' %self._freq_lim)
            elif value < 1:
                value = 1
            self.send('setf %i %i' %(self._stages.index(key)+1, value)) # e.g. setf 1 100 to set x axis to 100 Hz
            self._freq[key] = value

    @property
    def mode(self):
        """ Mode, choose from: gnd, cap, stp """
        for i in range(3):
            msg = self.send('getm %i' %(i+1)) # i+1 -> controllers labeled 1,2,3, not 0,1,2
            self._mode[self._stages[i]] = self._getValue(msg)
        return self._mode

    @mode.setter
    def mode(self, m):
        for key, value in m.items():
            if value not in self._modes:
                raise Exception('Bad mode for stage %i' %(i+1))
            else:
                msg = self.send('setm %i %s' %(self._stages.index(key)+1, value))
                self._mode[key] = value

    @property
    def V(self):
        for i in range(3):
            msg = self.send('getv %i' %(i+1)) # i+1 -> controllers labeled 1,2,3, not 0,1,2
            self._V[self._stages[i]] = float(self._getValue(msg))
        return self._V

    @V.setter
    def V(self, v):
        for key, value in v.items():
            if value > self._V_lim:
                raise Exception('voltage out of range, max %f V' %self._V_lim)
            elif value < 0:
                raise Exception('voltage out of range, min 0 V')
            self.send('setv %i %i' %(self._stages.index(key)+1, value)) # e.g. setf 1 10 to set x axis to 10 V
            self._V[key] = value

    @property
    def cap(self):
        self.mode = {'x':'cap', 'y':'cap', 'z':'cap'}
        for i in range(3):
            self.send('capw %i' %(i+1)) # wait for capacitance measurement to finish
            msg = self.send('getc %i' %(i+1))
            self._cap[self._stages[i]] = float(self._getValue(msg))
        return self._cap

    def close(self):
        '''
        Closes telnet connection
        '''
        self._tn.close()


    def connect(self):
        '''
        Connects to ANC300 Attocube Controller via LAN. If for some reason communication does not work, first check for IP 192.168.69.3 in cmd using arp -a, then troubleshoot using cygwin terminal: telnet 192.168.69.3 7230
        '''
        self._tn = telnetlib.Telnet(host, port, 5) # timeout 5 seconds
        self._tn.read_until(b"Authorization code: ") #skips to pw entry
        self._tn.write(b'123456'+ b'\n') #default password
        self._tn.read_until(b'> ')        # skip to input


    def check_voltage(self):
        for key, value in self.V.items():
            if value > self._V_lim:
                self.V = {key: self._V_lim}
                print("Axis %s voltage was too high, set to %f" %(key, self._V_lim))

    def ground(self):
        self.mode = {'x':'gnd', 'y':'gnd', 'z':'gnd'}

    def step(self, axis, numsteps, updown):
        """ steps up for number of steps given; if None, ignored; if 0, continuous"""
        self.check_voltage()

        if updown not in ['u','d']:
            raise Exception('What doesn\'t come up must come down!')

        self.mode = {axis: 'stp'}
        if numsteps > self._step_lim:
            raise Exception('too many steps! Max %i' %self._step_lim)
        elif numsteps == 0:
            raise Exception('That won\'t get you anywhere!')
            # msg = self.send('step%s %i c' %(updown, i+1)) NO!!!!! THIS IS BAD!!! WE DON'T WANT TO MOVE CONTINUOUSLY
        else:
            self.send('step%s %i %i' %(updown, self._stages.index(axis)+1, numsteps))
            self.send('stepw %i' %(self._stages.index(axis)+1)) # waits until motion has ended to run next command; Attocube.stop will stop motion no matter what
        self.mode = {axis: 'gnd'}

    def move(self, numsteps):
        self.up(numsteps)

    def up(self, numsteps):
        for axis, num in numsteps.items():
            if num > 0:
                upordown = 'u'
            else:
                num = -num
                upordown = 'd'
            self.step(axis, num, upordown)

    def down(self, numsteps):
        for axis, num in numsteps.items():
            if num > 0:
                upordown = 'd'
            else:
                num = -num
                upordown = 'u'
            self.step(axis, num, upordown)

    def stop(self):
        for i in range(3):
            msg = self.send('stop %i' %(i+1))

    def send(self, cmd):
        self.connect()
        cmd = cmd + '\n'
        try:
            self._tn.write(bytes(cmd, 'ascii'))
        except:
            print("Could not connect to ANC300 Attocube Controller!")
        self.close()
        return self._tn.read_until(b'\n> ') # looks for input line \n fixed bug with help

    def _getDigits(self,msg):
        """ Extracts digits from attocube message """
        for s in str(msg).split():
            if s.isdigit():
                return int(s)
        raise Exception('no numbers found') # will only run if number is not returned
        # integ = int(re.search(r'\d+', str(msg)).group())

    def _getValue(self, msg):
        """ Looks after equals sign in returned message to get value of parameter """
        return msg.split()[msg.split().index(b'=')+1].decode('utf-8') #looks after the equal sign



class ANC350_like300(Instrument):
    '''
    THIS CLASS NOT USED AS OF August 2016
    For remote operation of the Attocubes with the ANC350. Adapted directly from ANC300. Order of axes is X, Y, Z (controllers 1,2,3 are in that order).
    '''
    _stages = ['x','y','z']
    _modes = ['gnd','cap','stp']

    def __init__(self, montana):
        self.anc = PyANC350v4.Positioner()

        self._freq = {}
        self._V = {}
        self._cap = {}

        self.freq
        self.V

        self._freq_lim = 1000 # self-imposed, 10000 is true max
        self._step_lim = 5000 #self-imposed, no true max
        if montana.temperature['platform'] < 10:
            self._V_lim = 60.000 #LT limit
        else:
            self._V_lim = 45.000 #RT limit

        self.check_voltage()

        atexit.register(self.stop)  # will stop all motion if program quits


    @property
    def freq(self):
        for i in range(3):
            freq = self.anc.getFrequency(i)
            self._freq[self._stages[i]] = freq
        return self._freq

    @freq.setter
    def freq(self, f):
        for key, value in f.items():
            if value > self._freq_lim:
                raise Exception('frequency out of range, max %i Hz' %self._freq_lim)
            elif value < 1:
                value = 1
            self.anc.setFrequency(self._stages.index(key), value)
            self._freq[key] = value

    # @property
    # def mode(self):
        # """ Mode, choose from: gnd, cap, stp """
        # for i in range(3):
            # msg = self.send('getm %i' %(i+1)) # i+1 -> controllers labeled 1,2,3, not 0,1,2
            # self._mode[self._stages[i]] = self._getValue(msg)
        # return self._mode

    # @mode.setter
    # def mode(self, m):
        # for key, value in m.items():
            # if value not in self._modes:
                # raise Exception('Bad mode for stage %i' %(i+1))
            # else:
                # msg = self.send('setm %i %s' %(self._stages.index(key)+1, value))
                # self._mode[key] = value

    @property
    def V(self):
        for i in range(3):
            v = self.anc.getAmplitude(i)
            self._V[self._stages[i]] = v
        return self._V

    @V.setter
    def V(self, v):
        for key, value in v.items():
            if value > self._V_lim:
                raise Exception('voltage out of range, max %f V' %self._V_lim)
            elif value < 0:
                raise Exception('voltage out of range, min 0 V')
            self.anc.setAmplitude(self._stages.index(key), value)
            self._V[key] = value


    def check_voltage(self):
        for key, value in self.V.items():
            if value > self._V_lim:
                self.V = {key: self._V_lim}
                print("Axis %s voltage was too high, set to %f" %(key, self._V_lim))

    def ground(self):
        for i in range(3):
            self.anc.startContinuousMove(i, 0, backward)
            self.anc.setAxisOutput(i, 0, 0)

    def step(self, axis, numsteps, updown):
        self.check_voltage()

        if updown not in ['u','d']:
            raise Exception('updown must be \'u\' to move up and \'d\' to move down')

        self.anc.setAxisOutput(self._stages.index(axis), 1, 0)
        time.sleep(0.5) # wait for output to turn on
        if numsteps == None:
            pass
        elif numsteps > self._step_lim:
            raise Exception('too many steps! Max %i' %self._step_lim)
        elif numsteps == 0:
            raise Exception('numsteps was 0')
            # msg = self.send('step%s %i c' %(updown, i+1)) NO!!!!! THIS IS BAD!!! WE DON'T WANT TO MOVE CONTINUOUSLY
        else:
            if updown == 'u':
                backward = 0
            else:
                backward = 1
            self.anc.startContinuousMove(self._stages.index(axis), 1, backward)
            time.sleep(abs(numsteps)/self.freq[axis])
            self.anc.startContinuousMove(self._stages.index(axis), 0, backward)
        self.anc.setAxisOutput(self._stages.index(axis), 0, 0)

    def move(self, numsteps):
        self.up(numsteps)

    def up(self, numsteps):
        for axis, num in numsteps.items():
            if num == None:
                pass
            elif num > 0:
                upordown = 'u'
            else:
                num = -num
                upordown = 'd'
            self.step(axis, num, upordown)

    def down(self, numsteps):
        for axis, num in numsteps.items():
            if num == None:
                pass
            elif num > 0:
                upordown = 'd'
            else:
                num = -num
                upordown = 'u'
            self.step(axis, num, upordown)

    def stop(self):
        self.ground()


class Attocube(ANC350): ### ANC350 is closed loop controller, we use this one at the moment.
    pass
