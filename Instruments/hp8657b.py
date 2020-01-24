'''
Instrument driver for the HP 8657b signal generator -- functionality includes
changing the output frequency and amplitude (dBm)
This code is mostly modified from the file "lockin.py" on GitHub/Nowack_Lab
'''

import time, numpy as np
from tabulate import tabulate
from .instrument import Instrument, VISAInstrument

import visa

class HP8657b(VISAInstrument):
	'''
	microwave 2 GHz source generator
	'''
	_label = 'signalgenerator'

	_amplitude = None
	_frequency = None
	_increment = None

	def __init__(self, gpib_address = 7):

		if type(gpib_address) is int:
			gpib_address = 'GPIB::%02i::INSTR' %gpib_address

		self.gpib_address = gpib_address
		self.device_id = 'HP8657b_GPIB_' + str(self.gpib_address)
		self._increment = 10
		self._frequency = 100
		self._amplitude = -143.5
		self._init_visa()
		self._visa_handle.timeout = 3000

		print('Successfully initialized hp8657b')

	def _init_visa(self):
		self._visa_handle = visa.ResourceManager().open_resource(
															self.gpib_address)
		self._visa_handle.read_termination = '\n'
		self._visa_handle.write('OUTX 1') #1=GPIB

	def ask(self, cmd, timeout=3000):
		'''
		Default timeout 3000 ms. None for infinite timeout
		'''
		self._visa_handle.timeout = timeout
		return self._visa_handle.ask(cmd);

	def __del__(self):
		'''
		destroy the object and close the visa handle
		'''
		self.close()

	def __getstate__(self):
		self._save_dict = {"frequency": self._frequency,
                          "amplitude": self._amplitude,
						  "gpib_address": self.gpib_address}
		return self._save_dict

	@property
	def amplitude(self):
		'''
		get the carrier amplitude (dBm)
		'''
		return self._amplitude

	@amplitude.setter
	def amplitude(self, value):
		'''
		set the amplitdue in dBm
		'''
		if value < -143.5:
			value = -143.5
		if value > 13:
			value = 13
		self.write('AP%sDM' %value)
		self._amplitude = value
		#print('Setting amplitude to %.1f dBm' % value)

	@property
	def frequency(self):
		'''
		Returns the last set frequency
		'''
		return self._frequency

	@frequency.setter
	def frequency(self,value):
		'''
		set the frequency (MHz)
		'''
		if value < 0.1:
			value = 0.1
		if value > 2060:
			value = 2060
		self._frequency = value
		self.write('FR%sMZ' %value)
		#print('Setting frequency to %.1f MHz' % value)

if __name__ == '__main__':
    signalgenerator = HP8657b('GPIB::07::INSTR')
