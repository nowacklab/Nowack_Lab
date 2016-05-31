from ctypes import cdll
import atexit
import clr
import sys
from tabulate import tabulate

class Montana():
    def __init__(self, ip='192.168.69.101', port=7773):
        sys.path.append(r'C:\Users\Hemlock\Documents\GitHub\Nowack_Lab\Utilities')
        clr.AddReference('CryostationComm')
        from CryostationComm import CryoComm
        
        self.cryo = CryoComm()
        self.cryo.IP_Address = ip
        self.cryo.Port = port
        self.cryo.Connect()
        if not self.cryo.CheckConnection():
            raise Exception('Need to toggle \"Enable External Control\" button in Montana software!')
        atexit.register(self.delete)
        
        self._temperature = {}
        self._temperature = self.temperature
        self._temperature_stability = {}
        self._temperature_stability = self.temperature_stability

        
    @property
    def temperature(self):
        self._temperature['platform'] = float(self.ask('GPT'))
        self._temperature['stage 1'] = float(self.ask('GS1T'))
        self._temperature['stage 2'] = float(self.ask('GS2T'))
        self._temperature['sample'] = float(self.ask('GST'))
        self._temperature['user'] = float(self.ask('GUT'))
        self._temperature['setpoint'] = float(self.ask('GTSP'))
        
        return self._temperature

        
    @property
    def temperature_stability(self):
        self._temperature_stability['platform'] = self.ask('GPS')
        self._temperature_stability['sample'] = self.ask('GSS')
        self._temperature_stability['user'] = self.ask('GUS')
        return self._temperature_stability
        
    @property
    def pressure(self):
        self._pressure = self.ask('GCP')
        return self._pressure
        
    def ask(self, command):
        _, response = self.cryo.SendCommandAndGetResponse(command,command) # Not sure why need two arguments
        return response
        
    def log(self):
        table = []
        for key, value in sorted(self._temperature.items()):
            table.append([key,value])
        for key, value in sorted(self._temperature_stability.items()):
            table.append([key+' stability',value])
        table.append(['chamber pressure', self.pressure])
        print(tabulate(table))
        
        
        
    def delete(self):
        self.cryo.Exit
        
if __name__ == '__main__':
    mont = Montana()
    mont.log()
        