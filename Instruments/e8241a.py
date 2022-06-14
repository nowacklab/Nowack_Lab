'''
Instrument driver for the E8241a signal generator
Functionality includes changing the output frequency and amplitude (dBm)
From
https://github.com/nowacklab/Nowack_Lab/commit/ab98db0fcd89e203fa5600fd6016ea8dc25e1c96
'''

import time
import numpy as np
from tabulate import tabulate
from .instrument import Instrument, VISAInstrument

import visa

class E8241a(VISAInstrument):
    '''
    20 GHz signal generator
    '''
    _label = 'signalgenerator'

    _outputting = None
    _amplitude  = None
    _frequency  = None
    _startfreq  = None
    _stopfreq   = None

    def __init__(self, ip_address = '192.168.84.217'):

        gpib_address = 'TCPIP0::%s::inst0::INSTR' %ip_address

        self.gpib_address = gpib_address
        self.device_id = 'E8241a_TCPIP_' + str(self.gpib_address)
        self._init_visa()
        self._visa_handle.timeout = 3000

        print('Successfully initialized E8241A')

    def _init_visa(self):
        self._visa_handle = visa.ResourceManager().open_resource(self.gpib_address)
        time.sleep(.01)
        self._visa_handle.read_termination = '\n'
        time.sleep(.01)

        self._visa_handle.write('OUTX 1') #1=GPIB

    def query(self, cmd, timeout=3000):
        '''
        Default timeout 3000 ms. None for infinite timeout
        '''
        self._visa_handle.timeout = timeout
        return self._visa_handle.query(cmd);

    def __del__(self):
        '''
        Destroy the object and close the visa handle
        '''
        self.close()

    def __getstate__(self):
        self._save_dict = {
            "frequency": self._frequency,
            "amplitude": self._amplitude,
            "gpib_address": self.gpib_address,
        }
        return self._save_dict

    @property
    def outputting(self):
        '''
        Get the RF output state (ON/OFF)
        '''
        outputting = self.query(':OUTP:STAT?')
        if outputting == '0':
            self._outputting = False
        elif outputting == '1':
            self._outputting = True
        else:
            raise RuntimeError('Unknown output status')
        return self._outputting

    @outputting.setter
    def outputting(self, value):
        '''
        Set the RF output state
            True:  ON
            False: OFF
        '''
        if value == True:
            self.write(':OUTP:STAT ON')
        elif value == False:
            self.write(':OUTP:STAT OFF')
        else:
            raise ValueError('The output should be ON (True) or OFF (False)')
        self.outputting

    @property
    def amplitude(self):
        '''
        Get the carrier amplitude (dBm)
        '''
        self._amplitude = self.query(':SOUR:POW:LEV:IMM:AMPL?')
        return float(self._amplitude)

    @amplitude.setter
    def amplitude(self, value):
        '''
        Set the amplitude in dBm
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
        self._frequency = self.query(':SOUR:FREQ:FIX?')
        return float(self._frequency)

    @frequency.setter
    def frequency(self, value):
        '''
        Set the frequency (Hz)
        '''
        if value < 100e3:
            value = 100e3
        if value > 20e9:
            value = 20e9
        self._frequency = value
        self.write(':SOUR:FREQ:FIX %i' %value)

    @property
    def startfreq(self):
        self._startfreq = self.query(':SOUR:FREQ:STAR?')
        return self._startfreq

    @startfreq.setter
    def startfreq(self, value):
        self.write(':SOUR:FREQ:STAR %i' %value)
        self._startfreq = value

    @property
    def stopfreq(self):
        self._stopfreq = self.query(':SOUR:FREQ:STOP?')
        return self._stopfreq

    @stopfreq.setter
    def stopfreq(self, value):
        self.write(':SOUR:FREQ:STOP %i' %value)
        self._stopfreq = value

    def trigsweep(self, daq, freqmin, freqmax,
            chan_in = None,
            numcollect = 1000,
            pixeltime = 1e-3,
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

        # Remove one point since we are adding one at the end.
        numcollect += -1
        oversample = 10
        dutycycle = .5  # How long the trigger should be on
        phase = (oversample-1)/oversample # Alignment of trigger to beginning of step
        trigger_height = 5 # Amplitude of trigger in volts

        def squarewave(t):
            if ((t % oversample <= (phase + dutycycle)*oversample) and
                (t % oversample >= (phase)*oversample)):
                toreturn = trigger_height
            else:
                toreturn = 0
            return toreturn

        output_data = {}
        # Plus one is to provide one last rising edge.
        output_data[trigger] = list(map(squarewave,
            np.arange((numcollect + 1)*oversample - 1)))
        sample_rate = oversample / pixeltime
        daq.sweep({trigger: 0}, {trigger: 0}, numsteps = 1)

        # Lower the trigger for the line.
        time.sleep(0.2)
        self.output_data = output_data

        self.sample_rate = sample_rate
        received = daq.send_receive(
            output_data,
            chan_in = chan_in,
            sample_rate = sample_rate
        )
        downsampledreceived = {}
        for k in received.keys():
            downsampledreceived[k] = received[k][::oversample]
        downsampledreceived['freq'] = np.linspace(freqmin, freqmax, numcollect)
        return downsampledreceived


