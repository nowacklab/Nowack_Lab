import visa, time, numpy as np
from .instrument import Instrument

GAINS = [1,2,5,10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000]
FILTER = [0.03, 0.1, 0.3, 1, 3, 10, 30, 1e2, 3e2, 1e3, 3e3, 1e4, 3e4, 1e5, 3e5,1e6]

class SR560(Instrument):
    _label = 'preamp'

    #Put the gains as class variable tuples

    def __init__(self, port='COM5'):
        '''
        Driver for the Stanford Research SR560 preamplifier.
        e.g. preamp = SR560('COM5')
        '''
        if type(port) is int:
            port = 'COM%i' %port
        self.connect(port)
        self.write('LALL')


    def __getstate__(self):
        #not sure if this will work
        #might be better to save "gain" and "filter" in the Measurement, since
        #they are chosen in the Measurement
        self._save_dict = {"gain": self._gain,
                          "filter": self._filter,
                          "dccoupled": self.is_dc_coupled(),
                          "overloaded": self.is_OL()
                          }
        return self._save_dict


    @property
    def filter(self):
        print('SR560 is listen-only')

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
        self.write('HFRQ %i' %FILTER.index(low)) #these are deliberately backwards
        self.write('LFRQ %i' %FILTER.index(high))
        self._filter = (low, high)

    @property
    def gain(self):
        print('SR560 is listen-only')

    @gain.setter
    def gain(self, value):
        if value > 5e4:
            raise Exception('Max 50,000 gain!')
        elif value not in GAINS:
            raise Exception('INVALID GAIN')
        else:
            gaintowrite = GAINS.index(value)
            self.write('GAIN %i' % gaintowrite)
            self._gain = value

    def close(self):
        '''
        Closes connection to preamp
        '''
        self._inst.close()


    def connect(self, port):
        '''
        Connects to preamp via serial port
        '''
        rm = visa.ResourceManager()
        self._inst = rm.open_resource(port)


    def id(self):
        print('SR560 is listen-only')

    def dc_coupling(self, dc=True, ground=False):
        '''
        Sets the preamp ac/dc coupling
        '''
        if dc and ground:
            raise Exception('Cannot be both DC coupled and ground coupled!')
        elif dc:
            cpl = 1
        elif ground:
            cpl = 0
        else:
            cpl = 2
        self.write('CPLG%i' %(cpl)) # 0 = ac, 1=dc
        self._coupling = cpl

    def dr_high(self, high=True):
        self.write('DYNR %i' %(high)) # 0 = low noise, 1=high reserve

    def filter_mode(self, pass_type, rolloff=6):
        PASS = ['flat','band','low','high']
        ROLLOFF = [6, 12]
        if pass_type not in PASS:
            raise Exception('flat, band, low, or high pass')
        if rolloff not in ROLLOFF:
            raise Exception('for 6dB should be 6, for 12 dB should be 12')
        if pass_type == 'band' and rolloff == 12:
            raise Exception('Rolloff in bandpass may only be 6 dB')
        if pass_type == 'flat':
            fm = 0
        elif pass_type == 'band':
            fm = 5
        elif pass_type == 'low':
            fm = rolloff/6
        elif pass_type == 'high':
            fm = rolloff/6 + 2
        self.write('FLTM %i' %fm)

    def diff_input(self, AminusB=True, binput = False):
        if AminusB and binput:
            raise Exception('Can only amplify A-B or B')
        elif AminusB:
            srcm = 1
        elif binput:
            srcm = 2
        else:
            srcm = 0
        self.write('SRCE %i' %(srcm)) # 0 = A, 1 = A-B

    def recover(self):
        self.write('ROLD')

    def write(self, cmd):
        self._inst.write(cmd + '\r \n')



class FakeSR560(Instrument):
    _label = 'preamp'
    def __init__(self, port='COM1', gain=1, filter=(0,100e3), dc_coupling=True):
        self.gain = gain;
        self.filter = filter;
        self._dc_coupling = True;
        return;

    def __getstate__(self):
        self._save_dict = {"gain": self.gain,
                          "filter": self.filter,
                          "dccoupled": self.is_dc_coupled(),
                          "overloaded": self.is_OL()
                          }
        return self._save_dict

    def close(self):
        return;

    def connect(self):
        return;

    def is_OL(self):
        return False;

    def dc_coupling(self, dc=True):
        self._dc_coupling=dc;

    def is_dc_coupled(self):
        return self._dc_coupling;

    def dr_high(self, high=True):
        return;

    def filter_mode(self, pass_type, rolloff=0):
        return;

    def diff_input(self, AminusB=True):
        return;

    def recover(self):
        return;

    def time_const(self, tensec):
        return;

    def write(self, cmd, read=False):
        return;







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
