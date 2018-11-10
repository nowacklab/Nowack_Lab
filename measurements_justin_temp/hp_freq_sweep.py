from ..Instruments.HP8657B import functiongenerator
from ..Instruments.nidaq import *
import numpy as np
import matplotlib.pyplot as plt
import os
import time
from datetime import datetime
from Nowack_Lab.Utilities import dataset
from IPython.display import clear_output


class hp_freq_sweep_linear_abs():

	def __init__(self, freq_range, filepath, source_power = 15, notes = "No notes", plot=True):
		"""freq_range should be range of Hz values"""
		print("Remember to manually turn on source!")
		self.fxn_gen = functiongenerator(7)
		self.dq = NIDAQ()
		self.freq_range = freq_range
		self.power = 15  # +15 dbm default
		self.arr_for_DC = np.zeros((len(freq_range), 2))
		self.filepath = filepath
		self.notes = notes
		self.plot = plot

	def do(self):
		# for saving data
		now = datetime.now()
		run_timestamp = now.strftime('%Y-%m-%d_%H%M%S')

		# run measurement
		num_freqpoints = len(self.freq_range)
		self.arr_for_DC[:,0] = self.freq_range

		for i in range(num_freqpoints):
			time.sleep(.05)
			freq_val = self.freq_range[i]
			self.fxn_gen.freq = freq_val
			DC_val = self.dq.ai0.V
			if i % 10 == 0:
				clear_output()
				print(DC_val)
			self.arr_for_DC[i, 1] = np.absolute(DC_val)

		self.save_data(run_timestamp, self.arr_for_DC)
		if self.plot:
			hp_freq_sweep_linear_abs.plot(self.filepath + '\\' + run_timestamp + "_hp_freq_sweep_linear_abs.hdf5") # call the static plotting method
		#plt.plot(self.arr_for_DC[:, 0], self.arr_for_DC[:, 1])
		#plt.xlabel('Frequency step (Hz)')
		#plt.ylabel('DAQ DC reading (V)')
		#plt.show()


	@staticmethod
	def plot(some_filename):
		data_to_plot = dataset.Dataset(some_filename)
		fig, ax = plt.subplots(1, 1, figsize=(10, 6))
		arr_for_DC = data_to_plot.get(some_filename + '/arr_for_DC')
		notes = data_to_plot.get(some_filename + '/notes')
		plt.plot(arr_for_DC[:, 0], arr_for_DC[:, 1])
		plt.xlabel('Frequency step (Hz)')
		plt.ylabel('DAQ DC reading (V)')
		plt.show()
		# firstpart, secondpart = some_filename[:len(some_filename)/2], some_filename[len(some_filename)/2:]
		ax.set_title(some_filename[36:] + "\n source power = " +
					str(data_to_plot.get(some_filename + '/power')) + ' dBm' + "\n" + notes)
		path_for_savefig = some_filename.replace(".hdf5", "GRAPH.png")
		fig.savefig(path_for_savefig)


	def save_data(self, timestamp, arr):
		name = timestamp + '_hp_freq_sweep_linear_abs'
		path = os.path.join(self.filepath, name + '.hdf5')
		info = dataset.Dataset(path)
		info.append(path + '/freq_range', self.freq_range)
		info.append(path + '/power', self.power)

		info.append(path + '/arr_for_DC', self.arr_for_DC)
		info.append(path + '/notes', self.notes)

class hp_freq_sweep_logarithmic_abs():
	def __init__(self, freq_range, filepath, source_power = 15, notes = "No notes", plot=True):
		"""freq_range should be np.logspace range of Hz values"""
		print("Remember to manually turn on source!")
		self.fxn_gen = functiongenerator(7)
		self.dq = NIDAQ()
		self.freq_range = freq_range  # should be a numpy log range
		self.power = 15  # +15 dbm default
		self.arr_for_DC = np.zeros((len(freq_range), 2))
		self.filepath = filepath
		self.notes = notes
		self.plot = plot

	def do(self):
		# for saving data
		now = datetime.now()
		run_timestamp = now.strftime('%Y-%m-%d_%H%M%S')

		# run measurement
		num_freqpoints = len(self.freq_range)
		self.arr_for_DC[:,0] = self.freq_range

		for i in range(num_freqpoints):
			time.sleep(.05)
			freq_val = self.freq_range[i]
			self.fxn_gen.freq = freq_val
			DC_val = self.dq.ai0.V
			if i % 10 == 0:
				clear_output()
				print(DC_val)
			self.arr_for_DC[i, 1] = np.absolute(DC_val)

		self.save_data(run_timestamp, self.arr_for_DC)
		if self.plot:
			hp_freq_sweep_logarithmic_abs.plot(self.filepath + '\\' + run_timestamp + "_hp_freq_sweep_logarithmic_abs.hdf5") # call the static plotting method

	@staticmethod
	def plot(some_filename):
		data_to_plot = dataset.Dataset(some_filename)
		fig, ax = plt.subplots(1, 1, figsize=(10, 6))
		arr_for_DC = data_to_plot.get(some_filename + '/arr_for_DC')
		notes = data_to_plot.get(some_filename + '/notes')
		plt.semilogx(arr_for_DC[:, 0], arr_for_DC[:, 1])
		plt.xlabel('Frequency step (Hz)')
		plt.ylabel('DAQ DC reading (V)')
		plt.show()
		# firstpart, secondpart = some_filename[:len(some_filename)/2], some_filename[len(some_filename)/2:]
		ax.set_title(some_filename[36:] + "\n source power = " +
					str(data_to_plot.get(some_filename + '/power')) + ' dBm' + "\n" + notes)
		path_for_savefig = some_filename.replace(".hdf5", "GRAPH.png")
		fig.savefig(path_for_savefig)


	def save_data(self, timestamp, arr):
		name = timestamp + '_hp_freq_sweep_logarithmic_abs'
		path = os.path.join(self.filepath, name + '.hdf5')
		info = dataset.Dataset(path)
		info.append(path + '/freq_range', self.freq_range)
		info.append(path + '/power', self.power)

		info.append(path + '/arr_for_DC', self.arr_for_DC)
		info.append(path + '/notes', self.notes)

class constant_freq_change_flux():
	def __init__(self, frequency, source_power, filepath, Ibias_range, bias_resistor_value, preamp_gain, notes="No notes", plot=True):
		"""frequency in Hz. Ibias_range: np.linspace(start_current(amps), stop_current, number of points)"""
		if abs(max(Ibias_range)) > 10e-3:
			print("Check Ibias range values: do not send too much current thru field coil")
		print("Make sure bias resistor is connected (do not blow up squid)")
		self.frequency = frequency
		self.fxn_gen = functiongenerator(7)
		self.fxn_gen.freq = self.frequency
		self.power = source_power
		self.dq = NIDAQ(input_range=5)
		self.Ibias_range = Ibias_range
		self.bias_resistor_value = bias_resistor_value
		self.preamp_gain = preamp_gain
		self.Vbias_range = self.Ibias_range*bias_resistor_value
		self.filepath = filepath
		self.notes = notes
		self.plot = plot # boolean. will save plot regardless.

		self.arr_for_DC= np.zeros((len(self.Ibias_range), 2))

	def do(self):
		# create timestamp for saving
		now = datetime.now()
		run_timestamp = now.strftime('%Y-%m-%d_%H%M%S')

		# set the proper drive frequency
		self.fxn_gen.freq = self.frequency

		# run the measurement and record data
		num_Vbias_points = len(self.Vbias_range)
		for i in range(num_Vbias_points):
			time.sleep(.01)
			self.dq.ao0.V = self.Vbias_range[i]  # set field coil current
			self.arr_for_DC[i, 0] = self.Ibias_range[i]
			self.arr_for_DC[i, 1] = self.dq.ai0.V/self.preamp_gain
			sum = 0
			if i % 10 == 0:
				clear_output()
				print(i)

		self.save_data(run_timestamp, self.arr_for_DC)
		if self.plot:
			constant_freq_change_flux.plot(self.filepath + '\\' + run_timestamp + "_constant_freq_change_flux.hdf5") # call the static plotting method


	@staticmethod
	def plot(some_filename):
		data_to_plot = dataset.Dataset(some_filename)
		fig, ax = plt.subplots(1, 1, figsize=(10, 6))
		arr_for_DC = data_to_plot.get(some_filename + '/arr_for_DC')
		notes = data_to_plot.get(some_filename + '/notes')
		plt.plot(arr_for_DC[:, 0]*(1e3), arr_for_DC[:, 1])
		plt.xlabel('Bias current (mA)')
		plt.ylabel('preamp_gain-normalized-DAQ DC reading (V)')
		plt.show()
		# firstpart, secondpart = some_filename[:len(some_filename)/2], some_filename[len(some_filename)/2:]
		ax.set_title(some_filename[36:] + "\n source power = " +
					str(data_to_plot.get(some_filename + '/power')) + ' dBm' + "\n" + notes)
		path_for_savefig = some_filename.replace(".hdf5", "GRAPH.png")
		fig.savefig(path_for_savefig)

	def save_data(self, timestamp, arr):
		name = timestamp + '_constant_freq_change_flux'
		path = os.path.join(self.filepath, name + '.hdf5')
		info = dataset.Dataset(path)
		info.append(path + '/frequency', self.frequency)
		info.append(path + '/power', self.power)
		info.append(path + '/Ibias_range', self.Ibias_range)
		info.append(path + '/bias_resistor', self.bias_resistor_value)
		info.append(path + '/arr_for_DC', self.arr_for_DC)
		info.append(path + '/notes', self.notes)
