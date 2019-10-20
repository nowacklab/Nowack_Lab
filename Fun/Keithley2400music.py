"""
This file is a collection of classes which allow
musical control of the keithley sourcemeters.
Please warn your labmates before use.
"""
"""
rev
1/4/2011 - LNT - init.  while waiting for my
	active directory profile to load on the
	lab computer, i decided to write a program
	to make the sourcemeter play music
"""
# includes
from time import sleep
import visa

"""
This class provides a basic communication and control
interface to the keithley sourcemeter
"""
class BasicGPIB():
	def __init__(self, portNum=23):
        # assume GPIB
		self._GPIBaddr_ = portNum
		self.raw = visa.ResourceManager().open_resource('GPIB::' + str(self._GPIBaddr_) + '::INSTR')
        # self._visa_handle.read_termination = '\n'
		# self.raw = instrument('GPIB::' + str(self._GPIBaddr_) + '::INSTR')

	"""
	These routines are redundant but provide easier and more robust
	access to the pyvisa routines
	"""
	def write(self,data):
		self.raw.write(data + '\n')	# adds the newline (needed by some)

	def read(self):
		return self.raw.read()		# pure passthrough function

	# Mimics the pyvisa 'query' method with a wait
	def query(self,data):
		self.raw.write(data +'\n')	# write data or command
		sleep(0.001)				# wait 1ms (arbitrary)
		return self.raw.read()		# read result (if any)

	"""
	These routines provide easier programming access to
	common keithley tasks
	"""
	def reset(self):
		self.write('*RST')			# send the standard GPIB reset
		sleep(15)					# wait 15s for effect

	def ID(self):
		return self.query('*IDN?')

	# beep at frequency 'pitch' with length 'sust'
	# freq range is 65 to 2e6
	def beep(self,pitch,sust):
		if sust>512/pitch:
			print("note too long")
			return '-1'
		else:
			self.write(':SYST:BEEP '+str(pitch)+','+str(sust))

	def beepOff(self):
		self.write(':SYST:BEEP:STAT OFF')

	def beepOn(self):
		self.write(':SYST:BEEP:STAT ON')

	"""
	Mapping of musical notes onto keithley frequency range with useful time signatures
	tempo: beats per minute
	ts: time signature (tells which note gets a full beat)
	"""
	# an 'A' quarter note
	def qA(self,tempo,ts):
		sust=ts*4.0*60.0/tempo		# make sure tempo is a float!
		pitch=440					# a concert 'A' note
		self.beep(pitch,sust/10)
		sleep(sust*.9)

	# a 1st sixteenth note in a given key
	def s1(self,key,tempo,ts):
		sust=ts*4.0*60.0/(4*tempo)		# make sure tempo is a float!
		pitch=key					# first tone in a given key
		self.beep(pitch,sust/10)
		sleep(sust*.9)

	# an eighth rest
	def sREST(self,tempo,ts):
		sust=ts*4.0*60.0/(4*tempo)
		sleep(sust)

	# a 1st eighth note in a given key
	def e1(self,key,tempo,ts):
		sust=ts*4.0*60.0/(2*tempo)		# make sure tempo is a float!
		pitch=key					# first tone in a given key
		self.beep(pitch,sust/10)
		sleep(sust*.9)

	# an eighth rest
	def eREST(self,tempo,ts):
		sust=ts*4.0*60.0/(2*tempo)
		sleep(sust)

	# a 1st in a given key
	def q1(self,key,tempo,ts):
		sust=ts*4.0*60.0/tempo		# make sure tempo is a float!
		pitch=key					# first tone in a given key
		self.beep(pitch,sust/10)
		sleep(sust*.9)

	def qREST(self,tempo,ts):
		sust=ts*4.0*60.0/temp
		sleep(sust)


	# a 1st half note in a given key
	def h1(self,key,tempo,ts):
		sust=ts*4.0*2*60.0/tempo		# make sure tempo is a float!
		pitch=key					# first tone in a given key
		self.beep(pitch,sust/10)
		sleep(sust*.9)

	# a half rest
	def hREST(self,tempo,ts):
		sust=ts*4.0*2*60.0/tempo
		sleep(sust)
