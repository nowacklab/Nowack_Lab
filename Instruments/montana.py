from ctypes import cdll
import atexit
import sys, os
try:
    import clr
except:
    print('clr not imported')
from tabulate import tabulate
import time
from .instrument import Instrument

class Montana(Instrument):
    _label = 'montana'
    _temperature = {}
    _temperature_stability = {}
    _compressor_speed = None
    cryo = None
    def __init__(self, ip='192.168.100.237', port=7773):
        directory_of_this_module = os.path.dirname(os.path.realpath(__file__))
        sys.path.append(directory_of_this_module) # so CryostationComm is discoverable

        clr.AddReference(os.path.join(directory_of_this_module,'CryostationComm'))
        from CryostationComm import CryoComm

        self.cryo = CryoComm()
        self.cryo.IP_Address = ip
        self.cryo.Port = port

        atexit.register(self.exit)

        # Record initial values
        self.temperature
        self.temperature_stability
        self.compressor_speed

    def __getstate__(self):
        self._save_dict = {'temperature': self._temperature,
                          'stability': self._temperature_stability,
                          'compressor_speed': self._compressor_speed
                          }
        return self._save_dict


    def __setstate__(self, state):
        '''
        For loading.
        '''
        state['_temperature'] = state.pop('temperature')
        state['_temperature_stability'] = state.pop('stability')
        state['_compressor_speed'] = state.pop('compressor_speed')

        self.__dict__.update(state)

    @property
    def compressor_speed(self):
        cs = self.query('GCS')
        if cs in (25, 30):
            self._compressor_speed = 'high'
        elif cs == 14:
            self._compressor_speed = 'low'
        else:
            self._compressor_speed = 'custom'
        return self._compressor_speed

    @compressor_speed.setter
    def compressor_speed(self, value):
        '''
        Set the compressor speed.
        value either 'high', 'low', or 'off'
        There are more options. See Montana communication manual.
        '''
        assert value in ('high', 'low', 'off')
        if value == 'high':
            response = self.query('SCS7', to_float=False)
        elif value == 'low':
            response = self.query('SCS2', to_float=False)
        elif value == 'off':
            response = self.query('SCS0', to_float=False)
        print(response)

    @property
    def pressure(self):
        self._pressure = self.query('GCP')
        return self._pressure

    @property
    def temperature(self):
        temps = self.query('GPT', 'GS1T', 'GS2T', 'GST', 'GUT', 'GTSP')
        self._temperature['platform'] = temps['GPT']
        self._temperature['stage 1'] = temps['GS1T']
        self._temperature['stage 2'] = temps['GS2T']
        self._temperature['sample'] = temps['GST']
        self._temperature['user'] = temps['GUT']
        self._temperature['setpoint'] = temps['GTSP']

        return self._temperature

    @temperature.setter
    def temperature(self, value):
        self._temperature['setpoint'] = value
        response = self.query('STSP'+str(value), to_float=False)
        print(response)

    @property
    def temperature_stability(self):
        stabs = self.query('GPS', 'GSS', 'GUS')
        self._temperature_stability['platform'] = stabs['GPS']
        self._temperature_stability['sample'] = stabs['GSS']
        self._temperature_stability['user'] = stabs['GUS']
        return self._temperature_stability

    def query(self, *args, to_float = True):
        '''
        Sends many commands to Montana. If one command, returns one value. Else returns a dictionary with keys = commands, values = responses
        '''
        self.connect()
        responses = {}
        for command in args:
            _, responses[command] = self.cryo.SendCommandAndGetResponse(command,command) # Not sure why need two arguments
        self.exit()

        try:
            if to_float:
                for key, value in responses.items():
                    responses[key] = float(value)

            if len(responses) == 1:
                return next(iter(responses.values())) # will return only value
            return responses
        except:
            raise Exception('Problem connecting to Montana! Try again.')

    def check_status(self):
        '''
        Returns True if Montana status is okay. Returns False if there is a
        communication issue, implying the software has closed.
        '''
        try:
            self.temperature['platform']
            return True
        except:
            return False

    def cooldown(self):
        resp = self.query('SCD', to_float = False)
        print(resp)

    def connect(self):
        '''
        Opens connection to Montana
        '''
        inp = 'asdfasd'
        self.cryo.Connect()
        if not self.cryo.CheckConnection():
            inp = input('Need to toggle \"Enable External Control\" button in Montana software! Fix this and press enter to try connection again.')
        if inp == '':
            self.connect()
            print('Connection to Montana established.')


    def exit(self):
        '''
        Closes connection to Montana
        '''
        self.cryo.Exit()
        time.sleep(0.05) # slight delay to prevent issues with trying to connect again in quick succession

    def log(self):
        table = []
        for key, value in sorted(self._temperature.items()):
            table.append([key+' temp',value])
        for key, value in sorted(self._temperature_stability.items()):
            table.append([key+' stability',value])
        table.append(['chamber pressure', self.pressure])
        return tabulate(table)

    def standby(self):
        resp = self.query('SSB', to_float = False)
        print(resp)

    def warmup(self):
        resp = self.query('SWU', to_float = False)
        print(resp)

if __name__ == '__main__':
    mont = Montana()
    mont.log()
