from ctypes import cdll
import atexit
import sys, clr, os
from tabulate import tabulate
import time

class Montana():
    _temperature = {}
    cryo = None
    def __init__(self, ip='192.168.69.101', port=7773):
        directory_of_this_module = os.path.dirname(os.path.realpath(__file__))
        sys.path.append(directory_of_this_module) # so CryostationComm is discoverable

        clr.AddReference('CryostationComm')
        from CryostationComm import CryoComm

        self.cryo = CryoComm()
        self.cryo.IP_Address = ip
        self.cryo.Port = port

        atexit.register(self.exit)

        self._temperature = self.temperature
        self._temperature_stability = {}
        self._temperature_stability = self.temperature_stability


    def __getstate__(self):
        self.save_dict = {"temperature": self.temperature,
                          "stability": self._temperature_stability}
        return self.save_dict

    @property
    def pressure(self):
        self._pressure = self.ask('GCP')
        return self._pressure

    @property
    def temperature(self):
        temps = self.ask('GPT', 'GS1T', 'GS2T', 'GST', 'GUT', 'GTSP')
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
        response = self.ask('STSP'+str(value))
        print(response)

    @property
    def temperature_stability(self):
        stabs = self.ask('GPS', 'GSS', 'GUS')
        self._temperature_stability['platform'] = stabs['GPS']
        self._temperature_stability['sample'] = stabs['GSS']
        self._temperature_stability['user'] = stabs['GUS']
        return self._temperature_stability

    def ask(self, *args, to_float = True):
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

    def cooldown(self):
        resp = self.ask('SCD', to_float = False)
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
        resp = self.ask('SSB', to_float = False)
        print(resp)

    def warmup(self):
        resp = self.ask('SWU', to_float = False)
        print(resp)

if __name__ == '__main__':
    mont = Montana()
    mont.log()
