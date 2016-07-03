"""
Classes for controlling StarCryo electronics for the SQUID array: PCI100 (PC pci) and PFL102 (programmable feedback loop)

Possible to-do: make parameter values quantized to 12 bits to more accurately reflect actual parameter values
"""

import visa
import time
import atexit

class PCI100:
    def __init__(self, visaResource='COM3'):
        self._visaResource = visaResource
        atexit.register(self.close)
        
    def connect():
        '''
        Connect to the PCI100 for the StarCryo SQUID array
        '''    
        try:
            rm = visa.ResourceManager()
            self.instrument = rm.open_resource(str(visaResource))
            self.instrument.baud_rate = 9600        
        except visa.VisaIOError as e:
            print("Cannot connect to STAR Cryoelectronics SQUID interface:", e)
            
    def send(self, command):
        '''
        Sends a command to the PCI from the computer, will relay information to the PFL
        '''
        self.connect()
        try:
            self.instrument.write(command)
        except visa.VisaIOError as e:
            print("Cannot transmit data to STAR Cryo SQUID interface:", e)
        self.close()
            
    def close(self):
        '''
        Close PCI connection
        '''
        self.instrument.close()

class PFL102:   
    FeedbackResistors = {'1kOhm': 0x0002, '10kOhm': 0x0004, '100kOhm': 0x0000}
    IntegratorCapacitors = {'1.5nF': 0x0000, '15nF': 0x0100, '150nF': 0x0200}
    TestInputs = {'S_bias': 0x0010, 'A_bias': 0x0020, 'S_flux': 0x0040, 'A_flux': 0x0080}
    ParamRegisters = {'S_bias': 0b0010, 'A_bias': 0b0011, 'S_flux': 0b0000, 'A_flux': 0b0001, 'offset': 0b0100}
    TestSignalOptions = {'Off': 0, 'On': 1, 'Auto': 2}
    S_bias_lim = 2000 
    A_bias_lim = 100         
    S_flux_lim = 100 
    A_flux_lim = 200    
    offset_lim = 9.8     
    amplifierGain = 5040.0  
              
    def __init__(self, channel, pci):
        """ Will initialize PFL 102 and zero everything """
        assert channel>= 1 and channel <=8 # choose 1
        
        self.label = 'PFL102'
        self.channel = channel
        self.pci = pci
        self.pflRegister = None
        
        self._arrayLocked = False
        self._squidLocked = False
        
        self._S_bias = 0 
        self._A_bias = 0 
        self._S_flux = 0 
        self._A_flux = 0 
        self._offset = 0 
        
        self._integratorCapacitor = '1.5nF' 
        self._feedbackResistor = '100kOhm'
        self._sensitivity = 'High'
        self._testSignal = 'Auto'
        self._testInput = 'A_flux'
        self.resetIntegrator = False
        
        self.unlock() # make sure nothing is trying to lock
        self.updateAll() # to make sure all parameters are zero to begin
        
    ######### PROPERTY DEFINITIONS ###################
      
#S_bias      
    @property
    def S_bias(self):
        """ SQUID bias in uA """
        return self._S_bias

    @S_bias.setter
    def S_bias(self, value):
        if value < 0:
            self._S_bias = 0
        elif value > self.S_bias_lim:
            self._S_bias = self.S_bias_lim
        else:
            self._S_bias = value
        self.updateParam('S_bias')
    
# A_bias
    @property
    def A_bias(self):
        """ Array bias in uA """

        return self._A_bias

    @A_bias.setter
    def A_bias(self, value):
        if value < 0:
            self._A_bias = 0
        elif value > self.A_bias_lim:
            self._A_bias = self.A_bias_lim
        else:
            self._A_bias = value
        self.updateParam('A_bias')
    
# S_flux
    @property
    def S_flux(self):
        """ SQUID flux in uA """
        return self._S_flux

    @S_flux.setter
    def S_flux(self, value):
        if value < 0:
            self._S_flux = 0
        elif value > self.S_flux_lim:
            self._S_flux = self.S_flux_lim
        else:
            self._S_flux = value
        self.updateParam('S_flux')
     
# A_flux
    @property
    def A_flux(self):
        """ Array flux in uA """
        return self._A_flux
        
    @A_flux.setter
    def A_flux(self, value):
        if value < 0:
            self._A_flux = 0
        elif value > self.A_flux_lim:
            self._A_flux = self.A_flux_lim
        else:
            self._A_flux = value
        self.updateParam('A_flux')
        
# offset
    @property
    def offset(self):
        """ Preamp offset in mV - can only change when tuning """
        return self._offset
        
    @offset.setter
    def offset(self, value):
        if not self._squidLocked and not self._arrayLocked:
            if value < -self.offset_lim:
                self._offset = -self.offset_lim
            elif value > self.offset_lim:
                self._offset = self.offset_lim
            else:
                self._offset = value
            self.updateParam('offset')
        else:
            print('Cannot change offset while locked!')
    
# capacitor
    @property
    def integratorCapacitor(self):
        """ Capacitor in the integrator; 1.5nF, 15nF, or 150nF """
        return self._integratorCapacitor
        
    @integratorCapacitor.setter
    def integratorCapacitor(self, value):
        if value in self.IntegratorCapacitors.keys():
            self._integratorCapacitor = value
        else:
            print('Incorrect value; capacitor not changed!')
        self.updateDigitalControl()
        
# resistor
    @property
    def feedbackResistor(self):
        """" Feedback resistor; 1kOhm, 10kOhm, 100kOhm """
        return self._feedbackResistor
        
    @feedbackResistor.setter
    def feedbackResistor(self, value):
        if value in self.FeedbackResistors.keys():
            self._feedbackResistor = value
        else:
            print('Incorrect value; resistor not changed!')
        self.updateDigitalControl()
        
# Test signal
    @property
    def testSignal(self):
        """" Test signal; On, Auto (only on when tuning), Off """
        return self._testSignal
        
    @testSignal.setter
    def testSignal(self, value):
        if value in self.TestSignalOptions.keys():
            self._testSignal = value
        else:
            print('Test signal must be Off, On, or Auto!')
        self.updateDigitalControl()
        
 # Test input
    @property
    def testInput(self):
        """" Test input; S_bias, A_bias, S_flux, A_flux """

        return self._testInput
        
    @testInput.setter
    def testInput(self, value):
        if value in self.TestInputs.keys():
            self._testInput = value
        else:
            print('Test input must be S_bias, A_bias, S_flux, or A_flux')
        self.updateDigitalControl()
        
 # Sensitivity
    @property
    def sensitivity(self):
        """" Sensitivity, chooses R and C in feedback; High, Med, Low """
        return self._sensitivity
        
    @sensitivity.setter
    def sensitivity(self, value):
        if value == 'High' or value == 'high' or value == 'hi' or value == 'Hi' or value == 'HI':
            self.feedbackResistor = '100kOhm'
            self.integratorCapacitor = '1.5nF'
        elif value == 'Med' or value == 'med' or value == 'Medium' or value == 'medium':
            self.feedbackResistor = '10kOhm'
            self.integratorCapacitor = '15nF'
        elif value == 'Low' or value == 'low' or value == 'Lo' or value == 'lo' or value == 'LO' or value == 'LOW':
            self.feedbackResistor = '1kOhm'
            self.integratorCapacitor = '150nF'
        else:
            print('Sensitivity must be High, Med, or Low')
        
    ###############################
    
    
    def heat(self, t_heat=0.2, t_cool=10):
        """ Sends heat command for given t_heat, t_cool (in seconds)"""
        t_pulse = 0.1
        data = 0x1000+0x0800 # heater on + integrator -> amplifier
        
        for param in ['S_bias','A_bias','S_flux','A_flux']:
            self.updateParam(param, True) #true will zero this parameter

        print('Heating...')
        for i in range(int(t_heat/t_pulse)):
            self.send(data, 'DR')
            time.sleep(t_pulse)
        data = 0x0800 # heater off
        self.send(data, 'DR') # DR = digital control register
        print('Cooling...')
        time.sleep(t_cool)
        print('Done')
        self.updateAll()
        self.reset() # will reset the integrator and restore settings
        
    def lock(self, what):
        """ Lock SQUID xor array """
        if what == 'SQUID' or what == 'squid' or what == 'Squid':
            self._squidLocked = True
            self._arrayLocked = False
        elif what == 'ARRAY' or what == 'array' or what == 'Array':
            self._squidLocked = False
            self._arrayLocked = True
        self.updateDigitalControl()
            
    def reset(self):
        """ Reset the integrator """
        self.resetIntegrator = True
        self.updateDigitalControl()
        self.resetIntegrator = False
        self.updateDigitalControl()
      
    def send(self, data, registername):
        '''
        Prepare data to send to PCI
        '''
        if registername == 'DR':
            register = 0b01010000 # digital control register # register == "opcode"
        elif registername == 'FR':
            register = 0b01100000 # frequency control register
        else:
            raise Exception('registername must be DR or FR!')
        self.channel # "address"
        
        # calculate parity
        numbits = 0
        for x in [self.channel, register, data]:
            numbits += sum([x&(1<<i)>0 for i in range(32)])
        parity = numbits%2 # 1 if odd, 0 if even
        register += (not parity)*0x80 # if even number of 1's, adds parity bit to make odd
        
        command = '%02X%02X%04X;' % (self.channel, register, data) # make command into hex ASCII string
        
        self.pci.send(command)
            
    def unlock(self):
        """ Unlock both SQUID and array"""
        self._squidLocked = False
        self._arrayLocked = False
        self.updateDigitalControl()
    
    def toHex(self, attr):
        """ Converts value of parameter to hex number sent to PFL """
        value = getattr(self, attr)
        max_value = getattr(self,attr+'_lim')
        if attr == 'offset':
            hex_value = int(0xFFF*(value+max_value)/(2*max_value)) # this is because offset goes from -9.8 mV to 9.8 mV over 0x000 to 0xFFF
        else: 
            hex_value = int(0xFFF*value/max_value)
        return hex_value
    
    def updateDigitalControl(self):
        """Code will send new parameters to PFL, following section 6.5 in SCCv45.pdf"""       
        data = 0x0000
        
        # building up from lowest bit
        
        # Reset integrator
        if self.resetIntegrator:
            data += 0x0001
        
        # Feedback resistor selection
        data += self.FeedbackResistors[self.feedbackResistor]
        
        # Feedback select
        if self._squidLocked:
            data += 0x0008

        # Check if test signal supposed to be on and choose test signal if on
        if self.testSignal == 'Auto' or self.testSignal == 'On':
            if ((self.testInput in ('A_bias', 'A_flux')) and (not self._arrayLocked)) or ((self.testInput in ('S_bias', 'S_flux')) and (not self._squidLocked)) or self.testSignal == 'On':
                data += self.TestInputs[self.testInput]

        # capacitor select
        data += self.IntegratorCapacitors[self.integratorCapacitor]
        
        # feedback and integrator control: 0x400 for feedback if locked, 0x800 for amplifier if tuning
        if self._squidLocked or self._arrayLocked:
            data += 0x400
        else:
            data += 0x800
        
        # heater control is in other function because it totally overwrites the "data"
        self.send(data, 'DR') # DR= digital control register
    
    def updateAll(self):
        """ Refresh values of all parameters """
        for param in ['S_bias','A_bias','S_flux','A_flux','offset']:
            self.updateParam(param) # restores parameter settings
    
    def updateParam(self, param_name, zero=False):
        """ Update a single parameter """
        data = 0x0000
        data += self.ParamRegisters[param_name] # last nibble indicates parameter to change
        if not zero: # For heating, will zero all parameters
            data += self.toHex(param_name)*0x10

        # print('data sent: ', bin(data))

        self.send(data, 'FR') # FR = frequency control register

        
class SquidArray(PFL102):
    def __init__(self):
        super().__init__(1, PCI100())
    
    def tune_and_lock(self):
        """ Walks you through tuning and locking array/squid """
        pass

if __name__ == '__main__':
    """ Example/test code"""
   
   ##  CODE BELOW IS OLD AS OF 7/2/16  
    pci = PCI100('COM1')
    pfl = PFL102(1, pci) #channel, pci, sccAddress
    # pfl.A_bias = 00e-6
    # pfl.offset = -2.5e-3
    
    # pfl.A_bias = 0e-6
    # pfl.A_flux = 0e-6
    # pfl.S_bias = 0e-6
    # pfl.S_flux = 0e-6

    # time.sleep(2)    
    # print(pfl.testInput)
    
    # what = 'S_bias'
    # pfl.testInput = what
    # pfl.sensitivity = 'High'
    # pfl.testSignal = 'Off'
    # time.sleep(2)
    # pfl.testSignal = 'On'
    # for i in range(20):
        # setattr(pfl, what, i/20*100e-6)
        # print(getattr(pfl, what))
        # time.sleep(0.1)
    # for i in range(20):
        # setattr(pfl, what, 100e-6-i/20*100e-6)
        # print(getattr(pfl, what))
        # time.sleep(0.1)
    # setattr(pfl, what, 0)
    
    # pfl.reset()
      
    #pfl.heat(2, 2)



    
  
    
    # print('setting inputs to 19 uV/uA')
    # pfl.S_bias = var
    # print('Sbias value: ', pfl.S_bias)
    
    # pfl.A_bias = var
    # print('Abias value: ', pfl.A_bias)

    # pfl.S_flux = var
    # print('Sflux value: ', pfl.S_flux)
    
    # pfl.A_flux = var
    # print('Aflux value: ', pfl.A_flux)
    
    # pfl.offset = var
    # print('offset value: ', pfl.offset)
    
    # print('heat')
    # pfl.heat()
    # print('lock',' current lock states: SQUID: ', pfl.squidLocked, ' Array: ', pfl.arrayLocked)
    # pfl.lock('array')
    # pfl.lock('squid')
    # print('final lock states: SQUID: ', pfl.squidLocked, ' Array: ', pfl.arrayLocked)
    # print('unlock')
    # pfl.unlock()
    # print('final lock states: SQUID: ', pfl.squidLocked, ' Array: ', pfl.arrayLocked)

   
   
   ##### EXTRA CODE FOR PROPERTIES #####
           ## Good idea but doesn't work
        # for propname in ['S_bias', 'A_bias', 'S_flux', 'A_flux']:
            # fget = eval("lambda self: self._get(%s)" %propname)
            # fset = eval("lambda self, value: self._set(%s, value)" %propname)        
            # setattr(self, propname, property(self._get, self._set))
        # self._set('S_bias',5)
    
    # def _get(self, propname):
        # # Get function for array properties
        # print('hey')
        # # return getattr(self, propname)
        
    # def _set(self, propname, value): #this isn't being called for some reason :(
        # # Set function for array properties
        # lim = getattr(self, propname + '_lim')
        # print(lim)
        # if value < 0:
            # setattr(self, propname,0)
        # elif value > lim:
            # setattr(self, propname,lim)
        # else:
            # setattr(self, propname,value)
        # self.updateDigitalControl()
    
        # S_bias

