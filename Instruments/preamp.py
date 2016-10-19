import visa
import numpy as np

COARSE_GAIN = [5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000]
FINE_GAIN = [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0]
ALL_GAINS = []
FILTER = [0, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000, 100000, 300000]

class SR5113():
    _gain = None
    _filter = None
    def __init__(self, port='COM1'):
        '''
        Driver for the Signal Recovery 5113 preamplifier.
        e.g. preamp = SR5113('COM1')
        '''
        self.port = port
        self._first_connect = True

        for cg in COARSE_GAIN:
            for fg in FINE_GAIN:
                ALL_GAINS.append(int(cg*fg))

        self._gain = self.gain
        self._filter = self.filter

    def __getstate__(self):
        #not sure if this will work
        #might be better to save "gain" and "filter" in the Measurement, since
        #they are chosen in the Measurement
        self._save_dict = {"port": self.port,
                          "gain": self.gain,
                          "filter": self.filter}
        return self._save_dict


    def __setstate__(self, state):
        self.port = state.pop('port')
        self._first_connect = True

        return state


    @property
    def filter(self):
        try:
            low = self.write('FF0', True)
            high = self.write('FF1', True)
            self._filter = (FILTER[int(low)], FILTER[int(high)])
        except:
            print('Couldn\'t communicate with SR5113; filter may be wrong!')
        return self._filter

    @filter.setter
    def filter(self, value):
        # HOW TO DO DC?
        low, high = value #unpack tuple (low, high)

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
            cg = self.write('CG', True) #gets coarse gain index
            fg = self.write('FG', True) #gets fine gain index
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
            elif value in [1,2,3,4]: #special case, see manual
                fg = value-5 #-4 for gain of 1, etc.
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

    def close(self):
        '''
        Closes connection to preamp
        '''
        self.inst.close()

    def connect(self):
        '''
        Connects to preamp via serial port
        '''
        if self._first_connect:
            try:
                self.rm = visa.ResourceManager()
                self.inst = self.rm.open_resource(self.port)
                self.inst.read() # for some reason this always times out the first time you try to connect
            except:
                self._first_connect = False # It gets here from the timeout, will never try to do the timeout read again

        # Open the instrument for real
        self.rm = visa.ResourceManager()
        self.inst = self.rm.open_resource(self.port)

    def id(self):
        msg = self.write('ID', True)
        print(msg)

    def dc_coupling(self, dc=True):
        self.write('CP%i' %(dc)) # 0 = ac, 1=dc

    def dr_high(self, high=True):
        self.write('DR%i' %(high)) # 0 = low noise, 1=high reserve

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
        self.write('IN%i' %(AminusB)) # 0 = A, 1 = A-B

    def recover(self):
        self.write('OR')

    def time_const(self, tensec):
        self.write('TC%i' %(tensec)) # 0 = 1s, 1 = 10s

    def write(self, cmd, read=False):
        '''
        Will write commands to SR5113 preamp via serial port. If expect a value back, then set read=True. Figured this out by trial and error. First read command reads back the command sent, last read command will be empty (*\n). Middle command will contain response.
        e.g. preamp.write('ID', True)
        '''
        self.connect()

        self.inst.write(cmd+'\r')
        self.inst.read()
        if read:
            response = self.inst.read()
        self.inst.read()
        if read:
            return response.rstrip() #rstrip gets rid of \n

        self.close()

if __name__ == '__main__':
    preamp = SR5113()
    preamp.gain = 500
    print(preamp.gain)
    print(preamp.filter)
    preamp.recover()
    #preamp.filter_mode('high', 6)

    # try:
        # import visa
        # rm = visa.ResourceManager()
        # rm.list_resources()
        # inst = rm.open_resource('COM1')
        # # inst.write('ID\r')
        # # print(inst.read())
        # # print(inst.read())
        # inst.read()
        # # inst.close()
        # # rm.close()
    # except:
        # import visa
        # rm = visa.ResourceManager()
        # rm.list_resources()
        # inst = rm.open_resource('COM1')
        # inst.write('ID\r')
        # print(inst.read())
        # print(inst.read())
        # inst.read()
        # inst.close()
        # rm.close()
