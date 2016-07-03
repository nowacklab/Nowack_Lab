from ctypes import cdll
import atexit
import sys, clr, os
from tabulate import tabulate


class Montana():
    def __init__(self, ip='192.168.69.101', port=7773):
        directory_of_this_module = os.path.dirname(os.path.realpath(__file__))
        sys.path.append(directory_of_this_module) # so CryostationComm is discoverable
        
        clr.AddReference('CryostationComm')
        from CryostationComm import CryoComm
        
        self.cryo = CryoComm()
        self.cryo.IP_Address = ip
        self.cryo.Port = port

        atexit.register(self.exit)
        
        self._temperature = {}
        self._temperature = self.temperature
        self._temperature_stability = {}
        self._temperature_stability = self.temperature_stability
       
    @property
    def pressure(self):
        self._pressure = self.ask('GCP')
        return self._pressure
        
    @property
    def temperature(self):
        self._temperature['platform'] = float(self.ask('GPT'))
        self._temperature['stage 1'] = float(self.ask('GS1T'))
        self._temperature['stage 2'] = float(self.ask('GS2T'))
        self._temperature['sample'] = float(self.ask('GST'))
        self._temperature['user'] = float(self.ask('GUT'))
        self._temperature['setpoint'] = float(self.ask('GTSP'))
        
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        self._temperature['setpoint'] = value
        response = self.ask('STSP'+str(value))
        print(response)
        
    @property
    def temperature_stability(self):
        self._temperature_stability['platform'] = self.ask('GPS')
        self._temperature_stability['sample'] = self.ask('GSS')
        self._temperature_stability['user'] = self.ask('GUS')
        return self._temperature_stability
        
    def ask(self, command):
        '''
        Sends a command to Montana
        '''
        self.connect()
        _, response = self.cryo.SendCommandAndGetResponse(command,command) # Not sure why need two arguments
        self.exit()
        
        return response
        
    def cooldown(self):
        resp = self.ask('SCD')
        print(resp)
        
    def connect(self):
        '''
        Opens connection to Montana
        '''
        self.cryo.Connect()
        if not self.cryo.CheckConnection():
            inp = input('Need to toggle \"Enable External Control\" button in Montana software! Enter \'quit\' to halt execution and fix.')
            if inp == 'quit':
                raise Exception('Quit by user')
                        
    def exit(self):
        '''
        Closes connection to Montana
        '''
        self.cryo.Exit
               
    def log(self):
        table = []
        for key, value in sorted(self._temperature.items()):
            table.append([key+' temp',value])
        for key, value in sorted(self._temperature_stability.items()):
            table.append([key+' stability',value])
        table.append(['chamber pressure', self.pressure])
        return tabulate(table)
        
    def standby(self):
        resp = self.ask('SSB')
        print(resp)
        
    def warmup(self):
        resp = self.ask('SWU')
        print(resp)
        
if __name__ == '__main__':
    mont = Montana()
    mont.log()
        