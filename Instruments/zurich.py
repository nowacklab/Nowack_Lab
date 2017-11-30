"""
Nowack_Lab high level driver for Zurich HF2LI

Needs: zhinst, numpy, .instrument, time and _future_
"""

# Copyright 2016 Zurich Instruments AG

from __future__ import print_function
import time
from .instrument import Instrument
import numpy as np
import zhinst.utils

class gateVoltageError( Exception ):
    pass


class HF2LI(Instrument):
    '''
    Creates a Zurich HF2Li object, to control a zurich lock in amplifier
    '''

    _label = 'Zurich HF2LI'

    def __init__(self, server_address = 'localhost', server_port = 8005 ,
                device_serial = ''):
        '''
        Creates the HF2LI object. By choosing server address, can connection
        to HF2LI on remote (local network) computer.

        Arguments:

        server_address (str,optional) = Private IPV4 address of the computer
                            hosting the zurich. Defults to 'localhost',
                            the computer the python kernel is running on.

        server_port (int, optional) = Port of Zurich HF2LI. For local is
                            always 8005 (default), usually 8006 for remote.

        device_serial (str, optional) = Serial number of prefered zurich
                            hf2li. If empty string or does not exist,
                            uses first avaliable ZI.

        '''
        # Accesses the DAQServer at the instructed address and port.
        self.daq = zhinst.ziPython.ziDAQServer(server_address, server_port)
        # Gets the list of ZI devices connected to the Zurich DAQServer
        deviceList = zhinst.utils.devices(self.daq)

        # Checks if the device serial number you asked for is in the list
        if device_serial in deviceList :
            # Sets class variable device_id to the serial number
            self.device_id = device_serial
            # Tells the user that the ZI they asked for was found
            print('Using Zurich HF2LI with serial %s' % self.device_id)

        # Checks if you actually asked for a specific serial
        elif device_serial != '' :
            # Tells user ZI wasn't found.
            print('Requested device not found.')
            # Sets device_id to the first avaliable. Prints SN.
            self.device_id = zhinst.utils.autoDetect(self.daq)
        else:
            # Sets device_id to the first avaliable. Prints SN.
            self.device_id = zhinst.utils.autoDetect(self.daq)


    def zurich_setup(self, config):
            '''
            Pass in a dictionary with the desired configuration. If an element
            is ommited from the dictionary, no change.
            Obey the following conventions:

            Signal input config:
            key: sigin'#' (str, e.g. sigin0)
            elem: {ac:(boolean), range:(float, 1e-4:2), diff:(boolean)}

            Demodulator config:
            key: demod'#' (str, e.g. demod0)
            elem: {enable:(boolean), rate:(float), oscselect: (int), order:(int),
                    timeconstant:(float), harmonic:(int) }

            Oscillator config:
            key: osc'#' (str, e.g. osc0)
            elem: {freq: (float)}

            Signal output config:
            key: sigout'#' (str, e.g. sigout0)
            elem: {enable:(boolean), range: (float, .01,.1,1,10),
                    amplitude: (float, -1,1, scaling of signal to output range), offset: (float, -1:1 of FR)

            TA config:
            key: tamp'#' (str, e.g. tamp0)
            elem: {currentgain: (float, 1:1e8), dc: (boolean)}
            '''
            zCONFIG = []
            checkarray = {'sigin': {'ac': [bool], 'range': [float, 1e-4, 2],
                                                                'diff':[bool]},

                          'demod': {'enable':[bool], 'rate': [float],
                            'oscselect':[int, [0,1]], 'order': [int, 1,8],
                            'timeconstant':[float], 'harmonic':[int, 1, 1023]},

                          'osc':{'freq': [float, 0, 1e8]},

                          'sigout':{'enable';[bool],
                                                'range':[float, [.01,.1,1,10]],
                             'amplitude':[float, -1,1],'offset':[float, -1,1]},

                          'TAMP':{
                            'currentgain': [int,[1e2,1e3,1e4,1e5,1e6,1e7,1e8]],
                            'dc':[bool], 'voltagegain': [int, [1,10]],
                            'offset':[float]}
                          }
            tampchannel = -1
            for i in [0,1]:
                if self.daq.getString('/%s/ZCTRLS/%d/TAMP/AVAILABLE'
                                                        % (self.device_id, i)):
                                                        tampchannel = i
            for subsystem in config.keys():
                if subsystem[:-1] in checkarray.keys():
                    subconfig = config[subsystem]
                    subcheck = checkarray[subsystem[:-1]]
                    for param in subconfig.keys():
                        value = subconfig[param]
                        paramchk = subcheck[param]
                        if param in subcheck.keys():
                            if type(value) is paramchk[0]:
                                if type(value) is bool:
                                    value = int(value)
                                if (len(paramchk) == 1
                                    or
                                    (len(paramchk) == 2 and
                                    value in paramchk[1])
                                    or
                                    (len(paramchk)== 3   and
                                    value <= paramchk[2] and
                                    value >= paramchk[1])
                                    ):
                                    if subsystem[:-1] == 'TAMP':
                                        if tampchannel == -1:
                                            Exception('No TA connected!')
                                        else:
                                            zCONFIG.append([
                                            '/%s/ZCTRLS/%i/TAMP/%i/%s'
                                            % (self.device_id,tampchannel,
                                                subsystem[-1], param), value])
                                    else:
                                        zCONFIG.append(['/%s/%s/%d/%s'
                                        % (self.device_id,subsystem[:-1],
                                            subsystem[-1], param), value])
                                else:
                                    Exception('Parameter ' + param +' of ' +
                                                subsystem + 'is out of domain')
                            else:
                                Exception('Parameter ' + param +' of ' +
                                            subsystem +
                                            'is the wrong type, should be' +
                                            str(paramchk[0]))
                        else:
                            Exception(param +'is not a valid parameter for'
                                                                   + subsystem)
                else:
                    Exception(subsystem + 'is not a valid Zurich subsystem')
            self.daq.set(zCONFIG)
            config_as_set =  self.daq.get(*,True)
            for subconfig in zCONFIG:
                if config_as_set[subconfig[0]] != subconfig[1]
                    print(str(subconfig[0] + ' was set to ' +
                    config_as_set[subconfig[0]]))
