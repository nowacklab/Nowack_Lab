import visa
import atexit
import time
import telnetlib
import re
try:
    from pyanc350v4 import Positioner as ANC350Pos
except:
    print('PyANC350 not installed!')
from .instrument import Instrument

''' *** Use the Attocube class, definition is at the bottom *** '''

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

        V_lim = 45 # room temperature
        if montana:
            if montana.temperature['platform'] < 30:
                V_lim = 60 # low temperature requires more voltage to step
        else:
            print('Voltage limited to 45 V, no communication with Montana!')

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
            'x attocube': self.x,
            'y attocube': self.y,
            'z attocube': self.z
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
        self.anc.startAutoMove(self.num, enable=1, relative=0) # start

        # wait for the position to come within the tolerance
        while abs(self.pos - new_pos) > self.pos_tolerance: # all in um
            pass
        time.sleep(1) # wait for position measurement to settle

        # wait again for position to come closer to tolerance
        while abs(self.pos - new_pos) > self.pos_tolerance: # all in um
            pass
        time.sleep(5)

        self.anc.startAutoMove(self.num, enable=0, relative=0) # stop

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
        Do a continuous move at the current frequency for the amount of time
        corresponding to the number of steps desired.

        Attributes:
        numsteps (int): positive or negative number of steps desired
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

class Attocube(ANC350): ### ANC350 is closed loop controller, we use this one at the moment.
    pass
