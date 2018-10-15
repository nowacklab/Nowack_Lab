import visa, time, numpy as np
from .instrument import VISAInstrument

COARSE_GAIN = [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000]
FINE_GAIN = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0]
ALL_GAINS = []
for cg in COARSE_GAIN:
    for fg in FINE_GAIN:
        ALL_GAINS.append(int(cg*fg))
FILTER = [0, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000, 100000, 300000]

class SR5113(VISAInstrument):
    _label = 'preamp'
    _idn = None # *IDN? does not work

    _gain = None
    _filter = None

    def __init__(self, port='COM4'):
        '''
        Driver for the Signal Recovery 5113 preamplifier.
        '''
        if type(port) is int:
            port = 'COM%i' %port
        self.port = port

        self._init_visa(port, termination = '\r')

        self._gain = self.gain
        self._filter = self.filter


    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        self._save_dict = {'gain': self.gain,
                          'filter': self.filter}
        return self._save_dict


    @property
    def filter(self):
        try:
            low = self.query('FF0')
            high = self.query('FF1')
            self._filter = (FILTER[int(low)], FILTER[int(high)])
        except:
            print('Couldn\'t communicate with SR5113; filter may be wrong!')
        return self._filter

    @filter.setter
    def filter(self, value):
        # FIXME HOW TO DO DC?
        low, high = value  # unpack tuple (low, high)

        def find_nearest(array,value):
            diff = [a-value if a-value >= 0 else 1e6 for a in array]
            idx = (np.array(diff)).argmin()
            return array[idx]

        low = find_nearest(FILTER, low)
        high = find_nearest(FILTER, high)

        if low > high:
            raise Exception('Low cutoff frequency must be below high cutoff!')
        if low == 0:
            self.filter_mode('low',6)
        elif high > 1e6:
            self.filter_mode('high',6)
        self.write('FF0 %i' %FILTER.index(low))
        self.write('FF1 %i' %FILTER.index(high))
        self._filter = (low, high)

    @property
    def gain(self):
        try:
            cg = self.query('CG')  # gets coarse gain index
            fg = self.query('FG')  # gets fine gain index
            if int(fg) < 0:
                self._gain = 5+int(fg)
            else:
                self._gain = int(COARSE_GAIN[int(cg)]*FINE_GAIN[int(fg)])
        except:
            print('Couldn\'t communicate with SR5113! Gain may be wrong!')
        return self._gain

    @gain.setter
    def gain(self, value):
        if value != self.gain:
            if value > 100000:
                raise Exception('Max 100000 gain!')
            elif value in [1,2,3,4]:  # special case, see manual
                fg = value-5  # -4 for gain of 1, etc.
                cg = 0
            elif value not in ALL_GAINS:
                raise Exception('INVALID GAIN')
            else:
                for f in FINE_GAIN:
                    for c in COARSE_GAIN:
                        if int(f*c) == value:
                            break
                    if int(f*c) == value:
                        break
                fg = FINE_GAIN.index(f)
                cg = COARSE_GAIN.index(c)
            self.write('CG%i' %cg)
            self.write('FG%i' %fg)
            self._gain = value


    def id(self):
        msg = self.query('ID')
        print(msg)


    def is_OL(self):
        status = self.query('ST')
        status = int(status)  # returned a string
        if ((status >> 3) & 1):  # if third bit is 1
            return True
        else:
            return False

    def dc_coupling(self, dc=True):
        self.write('CP%i' %(dc))  # 0 = ac, 1=dc

    def dr_high(self, high=True):
        self.write('DR%i' %(high))  # 0 = low noise, 1=high reserve

    def filter_mode(self, pass_type, rolloff=0):
        PASS = ['flat','band','low', 'low','low','high','high','high']
        ROLLOFF = [0, 0, 6, 12, 612, 6, 12, 612]
        if pass_type not in PASS:
            raise Exception('flat, band, low, or high pass')
        if rolloff not in ROLLOFF:
            raise Exception('for 6dB should be 6, for 12 dB should be 12, for 6/12 dB should be 612')
        pass_indices = [i for i, x in enumerate(PASS) if x==pass_type] # indices with correct pass type
        roll_indices = [i for i, x in enumerate(ROLLOFF) if x==rolloff]
        index = (set(pass_indices) & set(roll_indices)).pop() #finds which index is the same
        self.write('FLT%i' %index)

    def diff_input(self, AminusB=True):
        self.write('IN%i' %(AminusB))  # 0 = A, 1 = A-B

    def recover(self):
        self.write('OR')

    def time_const(self, tensec):
        self.write('TC%i' %(tensec))  # 0 = 1s, 1 = 10s

    def query(self, cmd):
        '''
        Will write commands to SR5113 preamp via serial port.
        Figured this out by trial and error.
        First read command reads back the command sent,
        Middle read command will contain response
        last read command will be empty (*\n).
        '''
        return self.write(cmd, read=True)

    def write(self, cmd, read=False):
        '''
        Will write commands to SR5113 preamp via serial port.
        Figured this out by trial and error.
        First read command reads back the command sent,
        Middle read command will contain response (if one)
        last read command will be empty (*\n).

        read: set to True if response is expected
        '''

        time.sleep(0.05)  # Make sure we've had enough time to make connection.
        super().write(cmd+'\r')
        self.read() # read back the same command
        if read:
            response = self.read()
        self.read()

        if read:
            return response
