import visa
import atexit
from tabulate import tabulate
import numpy

class SR830():
    '''
    Instrument driver for SR830, modified from Guen's squidpy driver
    '''
    def __init__(self, gpib_address=''):
        self.gpib_address = gpib_address
        
        self.init_visa()

        atexit.register(self.exit)
        
        self.ch1_daq_input = None
        self.ch2_daq_input = None
        
        self.time_constant_options = {
                "10 us": 0,
                "30 us": 1,
                "100 us": 2,
                "300 us": 3,
                "1 ms": 4,
                "3 ms": 5,
                "10 ms": 6,
                "30 ms": 7,
                "100 ms": 8,
                "300 ms": 9,
                "1 s": 10,
                "3 s": 11,
                "10 s": 12,
                "30 s": 13,
                "100 s": 14,
                "300 s": 15,
                "1 ks": 16,
                "3 ks": 17,
                "10 ks": 18,
                "30 ks": 19
            }
        self.time_constant_values = [10e-6, 30e-6, 100e-6, 300e-6, 1e-3, 3e-3, 10e-3, 30e-3, 100e-3, 300e-3, 1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000]
        self.sensitivity_options = [
        2e-9, 5e-9, 10e-9, 20e-9, 50e-9, 100e-9, 200e-9,
        500e-9, 1e-6, 2e-6, 5e-6, 10e-6, 20e-6, 50e-6, 100e-6,
        200e-6, 500e-6, 1e-3, 2e-3, 5e-3, 10e-3, 20e-3,
        50e-3, 100e-3, 200e-3, 500e-3, 1]
        self.reserve_options = ['High Reserve', 'Normal', 'Low Noise']
    
    @property
    def sensitivity(self):
        '''Get the lockin sensitivity'''
        return self.sensitivity_options[int(self._visa_handle.ask('SENS?'))]

    @sensitivity.setter
    def sensitivity(self, value):
        '''Set the sensitivity'''
        if value > 1:
            value = 1
        index = abs(numpy.array([v - value  if (v - value)>=0 else -100000 for v in self.sensitivity_options])).argmin() #finds sensitivity just above input
        good_value = self.sensitivity_options[index]
        
        self._visa_handle.write('SENS%d' %self.sensitivity_options.index(good_value))

    @property
    def amplitude(self):
        '''Get the output amplitude'''
        return self._visa_handle.ask('SLVL?')
    
    @amplitude.setter
    def amplitude(self, value):
        '''Set the amplitude.'''
        if value < 0.004:
            value = 0.004
        if value > 5:
            value = 5
        self._visa_handle.write('SLVL %s' %value)
    
    @property
    def frequency(self):
        return self._visa_handle.ask('FREQ?')

    @frequency.setter
    def frequency(self, value):
        self._visa_handle.write('FREQ %s' %value)

    @property
    def X(self):
        return float(self._visa_handle.ask('OUTP?1'))

    @property
    def Y(self):
        return float(self._visa_handle.ask('OUTP?2'))

    @property
    def R(self):
        return float(self._visa_handle.ask('OUTP?3'))

    @property
    def theta(self):
        return float(self._visa_handle.ask('OUTP?4'))

    @property
    def time_constant(self):
        options = {self.time_constant_options[key]: key for key in self.time_constant_options.keys()}

        #return options[int(self._visa_handle.ask('OFLT?'))]
        return self.time_constant_values[int(self._visa_handle.ask('OFLT?'))]
        
    @time_constant.setter
    def time_constant(self, value):
        if type(value) is str:
            if value in list(self.time_constant_options.keys()):
                index = self.time_constant_options[value]
            else:
                raise Exception('Must choose allowed time constant or input as float in units of seconds!')
        elif type(value) in (float, int):
            if value < 10e-6:
                value = 10e-6
            index = abs(numpy.array([value - v  if (value-v)>=0 else -100000 for v in self.time_constant_values])).argmin() #finds time constant just below input
            good_value = self.time_constant_values[index]

        self._visa_handle.write('OFLT %s' %index)
    
    @property
    def reserve(self):
        i = int(self._visa_handle.ask('RMOD?'))
        return self.reserve_options[i]
     
    @reserve.setter
    def reserve(self, value):
        i = self.reserve_options.index(value)
        self._visa_handle.write('RMOD%i' %i)
    
    def auto_gain(self):
        self._visa_handle.write('AGAN')

    def auto_phase(self):
        self._visa_handle.write('APHS')
        
    def init_visa(self):
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        self._visa_handle.read_termination = '\n'
        self._visa_handle.write('OUTX 1') #1=GPIB
    
    def get_all(self):
        table = []
        for name in ['sensitivity', 'amplitude', 'frequency', 'time_constant']:
            table.append([name, getattr(self, name)])
        snapped = self._visa_handle.ask('SNAP?1,2,3,4')
        snapped = snapped.split(',')
        table.append(['X', snapped[0]])
        table.append(['Y', snapped[1]])
        table.append(['R', snapped[2]])
        table.append(['theta', snapped[3]])        
        return tabulate(table, headers = ['Parameter', 'Value'])
    
    def set_out(self, chan, param):
        """ set output on channel [1,2] to parameter [Ch1:['R','X'],Ch2:['Y','theta']]"""
        if chan == 1:
            if param not in ('R','X'):
                raise Exception('Cannot display %s on Channel 1!!' %param)
        elif chan == 2:
            if param not in ('Y','theta'):
                raise Exception('Cannot display %s on Channel 1!!' %param)
        else:
            raise Exception('Channel only 1 or 2!')
        
        if param in ('X', 'Y'):
            self._visa_handle.write('DDEF%i,0,0' %chan)
            self._visa_handle.write('FPOP%i,0' %chan)
        else:
            self._visa_handle.write('DDEF%i,1,0' %chan)
            self._visa_handle.write('FPOP%i,0' %chan)
            
    def convert_output(self, value):
        if not numpy.isscalar(value):
            value = numpy.array(value)
        return list(value/10*self.sensitivity) # will give actual output in volts, since output is scaled to 10 V == sensitivity

    def exit(self):
        self._visa_handle.close()
        
if __name__ == '__main__':
    lockin = SR830('GPIB::09::INSTR')
    #print(lockin.time_constant)
    #lockin.auto_phase()
    print(lockin.get_all())
    #print(lockin.time_constant)

    #lockin.auto_gain()
    
    # lockin.auto_phase() # test this