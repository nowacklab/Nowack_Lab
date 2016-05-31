from ctypes import cdll
import atexit

class Montana():
	def __init__(self, ip='192.168.69.101', port=7773):
		dll = cdll.LoadLibrary('C:\Users\Hemlock\Documents\GitHub\Nowack_Lab\Utilities\CryostationComm.dll')
		self.cryo = dll.CryoComm
		self.cryo.IP_Address = ip
		self.cryo.Port = port
		self.cryo.Connect
		if not self.cryo.CheckConnection:
			raise Exception('Need to toggle \"Enable External Control\" button in Montana software!')
		atexit.register(self.delete)
		
		self._temperature = {}
		self._temperature_stability = {}
		
	@property
	def temperature(self):
		self._temperature['platform'] = self.ask('GPT')
		self._temperature['stage 1'] = self.ask('GS1T')
		self._temperature['stage 2'] = self.ask('GS2T')
		self._temperature['sample'] = self.ask('GST')
		self._temperature['user'] = self.ask('GUT')
		self._temperature['setpoint'] = self.ask('GTSP')
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
		[~, response] = self.cryo.SendCommandAndGetResponse(command)
		return response
		
	def delete(self, command):
		self.cryo.Exit
		self.cryo.delete
		