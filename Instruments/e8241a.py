'''
Instrument driver for the E8241a signal generator -- functionality includes
changing the output frequency and amplitude (dBm)
This code is mostly modified from the file "hp8657b.py" on GitHub/Nowack_Lab
'''

import time, numpy as np
from tabulate import tabulate
from .instrument import Instrument, VISAInstrument

import visa

class E8241a(VISAInstrument):
	'''
	20 GHz signal generator
	'''
	_label = 'signalgenerator'

	_amplitude = None
	_frequency = None
	_startfreq = None
	_stopfreq = None

	def __init__(self, ip_address = '192.168.63.163'):

		gpib_address = 'TCPIP0::%s::inst0::INSTR' %ip_address

		self.gpib_address = gpib_address
		self.device_id = 'E8241a_TCPIP_' + str(self.gpib_address)
		self._init_visa()
		self._visa_handle.timeout = 3000

		print('Successfully initialized E8241b')

	def _init_visa(self):
		self._visa_handle = visa.ResourceManager().open_resource(
															self.gpib_address)
		time.sleep(.01)
		self._visa_handle.read_termination = '\n'
		time.sleep(.01)

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
		self._amplitude = self.ask(':SOUR:POW:LEV:IMM:AMPL?')
		return float(self._amplitude)

	@amplitude.setter
	def amplitude(self, value):
		'''
		set the amplitdue in dBm
		'''
		if value < -135:
			value = -135
		if value > 11:
			value = 11
		self.write(':SOUR:POW:LEV:IMM:AMPL %i' %value)
		self._amplitude = value

	@property
	def frequency(self):
		'''
		Returns the last set frequency
		'''
		self._frequency = self.ask(':SOUR:FREQ:FIX?')
		return float(self._frequency)

	@frequency.setter
	def frequency(self,value):
		'''
		set the frequency (Hz)
		'''
		if value < 100e3:
			value = 100e3
		if value > 20e9:
			value = 20e9
		self._frequency = value
		self.write(':SOUR:FREQ:FIX %i' %value)

	@property
	def startfreq(self):
		self._startfreq = self.ask(':SOUR:FREQ:STAR?')
		return self._startfreq

	@startfreq.setter
	def startfreq(self,value):
		self.write(':SOUR:FREQ:STAR %i' %value)
		self._startfreq = value

	@property
	def stopfreq(self):
		self._stopfreq = self.ask(':SOUR:FREQ:STOP?')
		return self._stopfreq

	@stopfreq.setter
	def stopfreq(self,value):
		self.write(':SOUR:FREQ:STOP %i' %value)
		self._stopfreq = value

	def trigsweep(self, daq, freqmin, freqmax, chan_in=None, numcollect = 1000, pixeltime = 1e-3,
				 trigger = False):
		'''
		Modified from piezos.py
		 specify the channels you want to monitor as a list

		 numcollect (int): the number of datapoints you want collected on
							chan_in
		 time (float): how long you want the entire acquisition to take

		 trigger (daq channel, string): which daq channel you want to have
										a pixel trigger on.
		'''
		self.daq = daq
		self.freqmin = freqmin
		self.freqmax = freqmax
		self.chan_in = chan_in
		self.numcollect = numcollect
		self.pixeltime = pixeltime
		self.trigger = trigger

		self.write('*RST')
		self.write('*CLS')
		self.write('FREQ:MODE LIST')
		self.write('FREQ:STAR %f Hz' % freqmin)
		self.write('FREQ:STOP %f Hz' % freqmax)
		self.write('SWE:POIN %i' % numcollect)
		self.write(':LIST:TRIG:SOUR EXT')
		self.write('POW:AMPL 6 dBm')
		self.write('OUTP:STAT ON')

	@property
	def trigrun(self):
		daq = self.daq
		freqmin = self.freqmin
		freqmax = self.freqmax
		chan_in = self.chan_in
		numcollect = self.numcollect
		pixeltime = self.pixeltime
		trigger = self.trigger

		self.write('INIT:IMM:ALL')

		#remove one point since we are adding one at the end.
		numcollect += -1
		oversample = 10
		dutycycle = .5  #how long the trigger should be on
		phase = (oversample-1)/oversample #alignment of trigger to beginning of step\
		trigger_height = 5 #amplitude of trigger in volts

		def squarewave(t):
			if ((t % oversample <= (phase + dutycycle)*oversample) and
				(t % oversample >= (phase)*oversample)):
				toreturn = trigger_height
			else:
				toreturn = 0
			return toreturn
		output_data = {}
		output_data[trigger] =  list(map(squarewave,
										np.arange((numcollect+1)*
															oversample-1)))
		#plus one is to provide one last rising edge.
		sample_rate = oversample/(pixeltime)
		daq.sweep({trigger:0}, {trigger:0}, numsteps = 1)
		# lower the trigger for the line.
		time.sleep(.2)
		self.output_data = output_data

		self.sample_rate = sample_rate
		received = daq.send_receive(output_data,
												chan_in = chan_in,
												sample_rate=sample_rate)
		downsampledreceived = {}
		for k in received.keys():
			downsampledreceived[k] = received[k][::oversample]
		downsampledreceived['freq'] = np.linspace(freqmin, freqmax, numcollect)
		return downsampledreceived
