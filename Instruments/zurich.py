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
class zurichInstrument(Instrument):
    '''
    Creates a Zurich object, to control a zurich lock in amplifier. Do
    not call this class, call it's subclasses.
    '''

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
            print('Using Zurich lock-in with serial %s' % self.device_id)

        # Checks if you actually asked for a specific serial
        elif device_serial != '' :
            # Tells user ZI wasn't found.
            print('Requested device not found.')
            # Sets device_id to the first avaliable. Prints SN.
            self.device_id = zhinst.utils.autoDetect(self.daq)
        else:
            # Sets device_id to the first avaliable. Prints SN.
            self.device_id = zhinst.utils.autoDetect(self.daq)
        #Sets the default name of the zurich object. It can, of course,
        #be changed later.
        self.name = 'zurich ' + self.device_id
        #Retrieve all the nodes on the zurich
        allNodes = self.daq.listNodes(self.device_id, 0x07)
        #Index through nodes
        for elem in allNodes:
            #generates the name of the attribute, simply replacing the
            # / of the the zurich path with underscores. Removes the "dev1056"
            nameofattr = elem.replace('/','_')[9:]
            # Checks that the node is not a special high speed streaming node
            if not 'SAMPLE' == elem[-6:]:
                #Sets an attribute of the class, specifically a property
                #with getters and setters going to elem
                setattr(self.__class__, nameofattr, property(
               fget=eval("lambda self: self.daq.getDouble('%s')" %elem),
               fset=eval("lambda self, value: self.daq.setDouble('%s', value)"
                                                                        %elem)))
            else:
                #If it is a high speed streaming node, use getsample.
                setattr(HF2LI, nameofattr, property(fget=eval(
                        "lambda self: dict = self.daq.getSample('%s');" %elem
                                + "{'x': dict['x'], 'y':dict['y']}")))
    def __getstate__(self):

        self._save_dict = self.daq.get('/', True)
        return self._save_dict

    def setup(self, config):
            '''
            Pass in a dictionary with the desired configuration. If an element
            is ommited from the dictionary, no change. Dictionary will be
            compared to a check array. To determine formatting, structure your
            dictionary the same way as the checkarray, but the inner most
            element in the dict (a list) replaced by the value you want. The
            value must be of the type given in the first element of the array
            at that dict location, and if the second element of the list is an
            array, it must be an element of that array. Conversely, if the
            second element is a number, the value must be inclusive between
            the second and third elements.
            Obey the following conventions:

            checkarray = {'sigin': {'ac': [bool], 'range': [float, 1e-4, 2],
                                                                'diff':[bool]},

                          'demod': {'enable':[bool], 'rate': [float],
                            'oscselect':[int, [0,1]], 'order': [int, 1,8],
                            'timeconstant':[float], 'harmonic':[int, 1, 1023]},

                          'osc':{'freq': [float, 0, 1e8]},

                          'sigout':{'enable':[bool],
                                                'range':[float, [.01,.1,1,10]],
                             'amplitude':[float, -1,1],'offset':[float, -1,1]},

                          'TAMP':{
                            'currentgain': [int,[1e2,1e3,1e4,1e5,1e6,1e7,1e8]],
                            'dc':[bool], 'voltagegain': [int, [1,10]],
                            'offset':[float]}
                          }
            '''
            zCONFIG = []
            checkarray = {'sigin': {'ac': [bool], 'range': [float, 1e-4, 2],
                                                                'diff':[bool]},

                          'demod': {'enable':[bool], 'rate': [float],
                            'oscselect':[int, [0,1]], 'order': [int, 1,8],
                            'timeconstant':[float], 'harmonic':[int, 1, 1023]},

                          'osc':{'freq': [float, 0, 1e8]},

                          'sigout':{'enable':[bool],
                                                'range':[float, [.01,.1,1,10]],
                             'amplitude':[float, -1,1],'offset':[float, -1,1]},

                          'TAMP':{
                            'currentgain': [int,[1e2,1e3,1e4,1e5,1e6,1e7,1e8]],
                            'dc':[bool], 'voltagegain': [int, [1,10]],
                            'offset':[float]}
                          }
            tampchannel = -1
            for i in [0,1]:
                if self.daq.getInt('/%s/ZCTRLS/%d/TAMP/AVAILABLE'
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
                                            raise Exception('No TA connected!')
                                        else:
                                            zCONFIG.append([
                                            '/%s/ZCTRLS/%i/TAMP/%i/%s'
                                            % (self.device_id,tampchannel,
                                                subsystem[-1], param), value])
                                    else:
                                        zCONFIG.append(['/%s/%ss/%s/%s'
                                        % (self.device_id,subsystem[:-1],
                                            subsystem[-1], param), value])
                                else:
                                    raise Exception('Parameter ' + param +' of '
                                               + subsystem + 'is out of domain')
                            else:
                                raise Exception('Parameter ' + param +' of ' +
                                    subsystem + ' is the wrong type, should be'
                                    + str(paramchk[0]))
                        else:
                            raise Exception(param +
                                    'is not a valid parameter for' + subsystem)
                else:
                    raise Exception(subsystem + 'is not a Zurich subsystem')
            self.daq.set(zCONFIG)
            config_as_set_changed = []
            for subconfig in zCONFIG:
                if type(subconfig[1]) is int:
                    config_as_set_changed.append([subconfig[0],
                                            self.daq.getInt(subconfig[0])])
                elif type(subconfig[1]) is str:
                    config_as_set_changed.append([subconfig[0],
                                            self.daq.getString(subconfig[0])])
                elif type(subconfig[1]) is float:
                    config_as_set_changed.append([subconfig[0],
                                            self.daq.getDouble(subconfig[0])])
                else:
                    raise Exception('type not handled!')
            return config_as_set_changed
            #return zCONFIG
class HF2LI(zurichInstrument):
      pass
class MFLI(zurichInstrument):
      pass
