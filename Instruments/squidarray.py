'''
Classes for controlling StarCryo electronics for the SQUID array: PCI100 (PC pci) and PFL102 (programmable feedback loop)

Possible to-do: make parameter values quantized to 12 bits to more accurately reflect actual parameter values
'''

import visa, time, os, json, jsonpickle as jsp
from IPython.display import clear_output
from .instrument import VISAInstrument, Instrument


class PCI100(VISAInstrument):
    def __init__(self, port='COM3'):
        if isinstance(port, int):
            port = 'COM%i' % port
        self.port = port

        try:
            self._init_visa(port)
        except BaseException:
            raise Exception(
                "Cannot connect to STAR Cryoelectronics SQUID interface")
        self.close()

    def write(self, cmd):
        '''
        Write to the PCI; create and destroy visa handles every time.
        '''
        self._init_visa(self.port)
        try:
            super().write(cmd)
        except BaseException:
            raise Exception(
                "Cannot transmit data to STAR Cryo SQUID interface")
        self.close()


class PFL102(Instrument):
    FeedbackResistors = {'1kOhm': 0x0002, '10kOhm': 0x0004, '100kOhm': 0x0000}
    IntegratorCapacitors = {'1.5nF': 0x0000, '15nF': 0x0100, '150nF': 0x0200}
    TestInputs = {
        'S_bias': 0x0010,
        'A_bias': 0x0020,
        'S_flux': 0x0040,
        'A_flux': 0x0080}
    ParamRegisters = {
        'S_bias': 0b0010,
        'A_bias': 0b0011,
        'S_flux': 0b0000,
        'A_flux': 0b0001,
        'offset': 0b0100}
    TestSignalOptions = {'Off': 0, 'On': 1, 'Auto': 2}

    # Limits; N.B. these are hard-coded by the resistors in the PFL box.
    # Do not change in software unless you change the resistors.
    S_bias_lim = 2000
    A_bias_lim = 100
    S_flux_lim = 100
    A_flux_lim = 200
    offset_lim = 9.8

    amplifierGain = 5040.0
    param_filename = os.path.join(
        os.path.dirname(__file__),
        'squidarray_params.json')

    def __init__(self, channel, pci):
        '''
        Initialize the PFL102.
        '''
        assert channel >= 1 and channel <= 8  # choose 1

        self.channel = channel
        self.pci = pci
        self.pflRegister = None
        self.resetIntegrator = False

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

        self.unlock()  # make sure nothing is trying update digital control

        self.updateAll()
        self.updateDigitalControl()

    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        self._save_dict = {"Array_bias": self._A_bias,
                           "Array_flux": self._A_flux,
                           "SQUID_bias": self._S_bias,
                           "SQUID_flux": self._S_flux,
                           "Array_locked": self._arrayLocked,
                           "Feedback_resistor": self._feedbackResistor,
                           "Integrator_capacitor": self._integratorCapacitor,
                           "Preamp_voltage_offset": self._offset,
                           "sensitivity": self._sensitivity,
                           "SQUID_locked": self._squidLocked,
                           "Test_input": self._testInput,
                           "Test_signal": self._testSignal,
                           "channel": self.channel,
                           "resetIntegrator": self.resetIntegrator
                           }
        return self._save_dict

    def __setstate__(self, state):
        '''
        NOTE: this will load the real instrument. Load with caution!
        '''
        keys = [
            ('_A_bias', 'Array_bias'),
            ('_A_flux', 'Array_flux'),
            ('_S_bias', 'SQUID_bias'),
            ('_S_flux', 'SQUID_flux'),
            ('_arrayLocked', 'Array_locked'),
            ('_feedbackResistor', 'Feedback_resistor'),
            ('_integratorCapacitor', 'Integrator_capacitor'),
            ('_offset', 'Preamp_voltage_offset'),
            ('_sensitivity', 'sensitivity'),
            ('_testInput', 'Test_input'),
            ('_squidLocked', 'SQUID_locked'),
            ('_testSignal', 'Test_signal'),
        ]

        for new, old in keys:
            try:
                state[new] = state.pop(old)
            except:
                pass

        self.__dict__.update(state)
        self._loaded = True

    ######### PROPERTY DEFINITIONS ###################

# S_bias
    @property
    def S_bias(self):
        ''' SQUID bias in uA '''
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
        ''' Array bias in uA '''

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
        ''' SQUID flux in uA '''
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
        ''' Array flux in uA '''
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
        ''' Preamp offset in mV - can only change when tuning '''
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
        ''' Capacitor in the integrator; 1.5nF, 15nF, or 150nF '''
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
        ''' Feedback resistor; 1kOhm, 10kOhm, 100kOhm '''
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
        ''' Test signal; On, Auto (only on when tuning), Off '''
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
        ''' Test input; S_bias, A_bias, S_flux, A_flux '''

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
        ''' Sensitivity, chooses R and C in feedback; High, Med, Low '''
        return self._sensitivity

    @sensitivity.setter
    def sensitivity(self, value):
        if value == 'High' or value == 'high' or value == 'hi' or value == 'Hi' or value == 'HI':
            self.feedbackResistor = '100kOhm'
            self.integratorCapacitor = '1.5nF'
            self._sensitivity = "High"
        elif value == 'Med' or value == 'med' or value == 'Medium' or value == 'medium':
            self.feedbackResistor = '10kOhm'
            self.integratorCapacitor = '15nF'
            self._sensitivity = "Med"
        elif value == 'Low' or value == 'low' or value == 'Lo' or value == 'lo' or value == 'LO' or value == 'LOW':
            self.feedbackResistor = '1kOhm'
            self.integratorCapacitor = '150nF'
            self._sensitivity = "Low"
        else:
            print('Sensitivity must be High, Med, or Low')

    ###############################

    def heat(self, t_heat=0.2, t_cool=10):
        ''' Sends heat command for given t_heat, t_cool (in seconds)'''
        t_pulse = 0.1
        data = 0x1000 + 0x0800  # heater on + integrator -> amplifier

        for param in ['S_bias', 'A_bias', 'S_flux', 'A_flux']:
            self.updateParam(param, True)  # true will zero this parameter

        print('Heating...')
        for i in range(int(t_heat / t_pulse)):
            self.send(data, 'DR')
            time.sleep(t_pulse)
        data = 0x0800  # heater off
        self.send(data, 'DR')  # DR = digital control register
        print('Cooling...')
        time.sleep(t_cool)
        print('Done')
        self.updateAll()
        self.reset()  # will reset the integrator and restore settings

    @staticmethod
    def load(json_file=None, port='COM3'):
        '''
        Load last saved parameters for the array from a file.
        '''
        if json_file is None:
            json_file = os.path.join(
                os.path.dirname(__file__),
                'squidarray_params.json')
        with open(json_file, encoding='utf-8') as f:
            obj_dict = json.load(f)

        # we have loaded something else
        if 'SquidArray' not in obj_dict['py/object']:
            # find the squidarray dict
            obj_dict = obj_dict['py/state']['squidarray']

        obj_string = json.dumps(obj_dict)
        obj = jsp.decode(obj_string)

        obj.pci = PCI100(port=port)
        return obj

    def lock(self, what):
        ''' Lock SQUID xor array '''
        if what == 'SQUID' or what == 'squid' or what == 'Squid':
            self._squidLocked = True
            self._arrayLocked = False
        elif what == 'ARRAY' or what == 'array' or what == 'Array':
            self._squidLocked = False
            self._arrayLocked = True
        self.updateDigitalControl()

    def reset(self):
        ''' Reset the integrator '''
        self.resetIntegrator = True
        self.updateDigitalControl()
        self.resetIntegrator = False
        self.updateDigitalControl()

    def save(self):
        '''
        Saves current parameters to squidarray_params.json for future loading.
        '''
        obj_string = jsp.encode(self)
        obj_dict = json.loads(obj_string)
        with open(self.param_filename, 'w', encoding='utf-8') as f:
            json.dump(obj_dict, f, sort_keys=True, indent=4)

    def send(self, data, registername):
        '''
        Prepare data to send to PCI
        '''
        if registername == 'DR':
            register = 0b01010000  # digital control register # register == "opcode"
        elif registername == 'FR':
            register = 0b01100000  # frequency control register
        else:
            raise Exception('registername must be DR or FR!')
        self.channel  # "address"

        # calculate parity
        numbits = 0
        for x in [self.channel, register, data]:
            numbits += sum([x & (1 << i) > 0 for i in range(32)])
        parity = numbits % 2  # 1 if odd, 0 if even
        # if even number of 1's, adds parity bit to make odd
        register += (not parity) * 0x80

        # make command into hex ASCII string
        command = '%02X%02X%04X;' % (self.channel, register, data)

        self.pci.write(command)

        self.save()

    def unlock(self):
        ''' Unlock both SQUID and array'''
        self._squidLocked = False
        self._arrayLocked = False
        self.updateDigitalControl()

    def toHex(self, attr):
        ''' Converts value of parameter to hex number sent to PFL '''
        value = getattr(self, attr)
        max_value = getattr(self, attr + '_lim')
        if attr == 'offset':
            # this is because offset goes from -9.8 mV to 9.8 mV over 0x000 to
            # 0xFFF
            hex_value = int(0xFFF * (value + max_value) / (2 * max_value))
        else:
            hex_value = int(0xFFF * value / max_value)
        return hex_value

    def updateDigitalControl(self):
        '''Code will send new parameters to PFL, following section 6.5 in SCCv45.pdf'''
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
            if ((self.testInput in ('A_bias', 'A_flux'))
                and (not self._arrayLocked)) or (
                    (self.testInput in ('S_bias', 'S_flux'))
                    and (not self._squidLocked)) or self.testSignal == 'On':
                data += self.TestInputs[self.testInput]

        # capacitor select
        data += self.IntegratorCapacitors[self.integratorCapacitor]

        # feedback and integrator control: 0x400 for feedback if locked, 0x800
        # for amplifier if tuning
        if self._squidLocked or self._arrayLocked:
            data += 0x400
        else:
            data += 0x800

        # heater control is in other function because it totally overwrites the
        # "data"
        self.send(data, 'DR')  # DR= digital control register

    def updateAll(self):
        ''' Refresh values of all parameters '''
        for param in ['S_bias', 'A_bias', 'S_flux', 'A_flux', 'offset']:
            self.updateParam(param)  # restores parameter settings

    def updateParam(self, param_name, zero=False):
        ''' Update a single parameter '''
        data = 0x0000
        # last nibble indicates parameter to change
        data += self.ParamRegisters[param_name]
        if not zero:  # For heating, will zero all parameters
            data += self.toHex(param_name) * 0x10

        # print('data sent: ', bin(data))

        self.send(data, 'FR')  # FR = frequency control register


class SquidArray(PFL102):
    _label = 'squidarray'

    def __init__(self, port='COM3', load=True):
        '''
        Port: where the PCI100 is connected
        load: Load previous parameters.
        '''
        self.channel = 1
        self.pci = PCI100(port)
        if load:
            self.load_dict()
        else:
            super().__init__(self.channel, self.pci)


    def load_dict(self, json_file=None):
        '''
        Load Squid array parameters from a JSON file without needing to create
        a new object.
        '''
        obj = SquidArray.load(json_file)
        self.__dict__.update(obj.__dict__)

    def tune(self):
        '''
        Walks you through tuning and locking array/squid
        '''
        input("Turn test signal on. Ramp, 3.5 Vpp, 100 Hz. Press enter to continue.")
        clear_output()
        self.unlock()
        self.testSignal = 'Auto'
        self.testInput = 'A_flux'

        def quit():
            raise Exception('Quit by user.')

        # Array bias
        while True:
            inp = input(
                'ARRAY BIAS = %.1f uA\nEnter the desired array bias (uA) and press enter.\nIf the bias point looks fine, press enter. (q to quit)' %
                self.A_bias)
            clear_output()
            if inp == '':
                break
            elif inp == 'q':
                quit()
            try:
                self.A_bias = float(inp)
            except BaseException:
                pass

        # Offset
        while True:
            inp = input(
                'OFFSET = %.3f mV\nEnter the desired offset (mV) and press enter.\nIf offset looks good, press enter. (q to quit)' %
                self.offset)
            clear_output()
            if inp == '':
                break
            elif inp == 'q':
                quit()
            try:
                self.offset = float(inp)
            except BaseException:
                pass

        # Squid bias
        while True:
            inp = input(
                'SQUID BIAS = %.1f uA\nEnter the desired SQUID bias (uA) and press enter. If SQUID bias looks alright, press enter.' %
                self.S_bias)
            clear_output()
            if inp == '':
                break
            elif inp == 'q':
                quit()
            try:
                self.S_bias = float(inp)
            except BaseException:
                pass

        # Lock the array
        inp = input('About to lock the array. Okay to proceed? (q to quit)')
        if inp == 'q':
            quit()
        self.lock('array')
        clear_output()

        # Confirm array locked
        while True:
            inp = input(
                'Array should be locked? Enter to proceed, r to reset feedback, q to quit.')
            clear_output()
            if inp == 'q':
                quit()
            elif inp == 'r':
                self.reset()
            else:
                break

        # SQUID bias
        input('Increase amplitude of test signal to max.')
        self.testInput = 'S_flux'
        while True:
            inp = input(
                'SQUID BIAS = %.1f uA\nEnter the desired squid bias (uA) and press enter.\nIf the bias point looks fine, press enter. (q to quit)' %
                self.S_bias)
            clear_output()
            if inp == '':
                break
            elif inp == 'q':
                quit()
            try:
                self.S_bias = float(inp)
            except BaseException:
                pass

        # Array flux
        while True:
            inp = input(
                'ARRAY FLUX = %.1f uA\nEnter the desired array flux (uA) and press enter.\n"r" to reset.\nIf the bias point looks fine, press enter. (q to quit)' %
                self.A_flux)
            clear_output()
            if inp == '':
                break
            elif inp == 'q':
                quit()
            elif inp == 'r':
                self.reset()
            else:
                try:
                    self.A_flux = float(inp)
                except BaseException:
                    pass

        # Lock the squid
        inp = input('About to lock the SQUID. Okay to proceed? (q to quit)')
        clear_output()
        if inp == 'q':
            quit()
        self.lock('squid')

        # Confirm array locked
        while True:
            inp = input(
                'SQUID should be locked? Enter to proceed, reset to r feedback, q to quit.')
            clear_output()
            if inp == 'q':
                quit()
            elif inp == 'r':
                self.reset()
            else:
                break

        # Squid flux
        while True:
            inp = input(
                'SQUID FLUX = %.1f uA\nEnter the desired SQUID flux (uA) and press enter.\n"r" to reset.\nIf the bias point looks fine, press enter. (q to quit)' %
                self.S_flux)
            clear_output()
            if inp == '':
                break
            elif inp == 'q':
                quit()
            elif inp == 'r':
                self.reset()
            else:
                try:
                    self.S_flux = float(inp)
                except BaseException:
                    pass
                self.reset()

        print('...and we\'re all tuned up!\n')
        for var in ['A_bias', 'A_flux', 'S_bias', 'S_flux']:
            print(var + ' = %.1f' % getattr(self, var))
        print('offset = %.3f' % self.offset)

    def zero(self):
        self.unlock()
        self.testSignal = 'Off'
        self.S_bias = 0
        self.S_flux = 0
        self.A_bias = 0
        self.A_flux = 0
        self.offset = 0
