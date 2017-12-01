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

#class CheckArray(object):
#    def __init__(self, *args):
#        """
#        """
#
#    def check(self):

class subnode():
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
        numberlookup = {'0': 'zero','1':'one','2':'two','3':'three','4':'four',
                        '5':'five','6':'six','7':'seven','8':'eight',
                        '9':'nine'}
        def check_add(obj, nodes_check):
                passedobj = obj
                for node_check in nodes_check:
                    if not hasattr(passedobj, node_check):
                        setattr(passedobj, node_check, subnode())
                    passedobj = getattr(passedobj, node_check)
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
        allNodes = self.daq.listNodes(self.device_id, 0x07)
        typeNodes = self.daq.getList(self.device_id)
        for elem in allNodes:
            nodes = elem.split('/')
            nodes = [x for x in nodes if x != '']
            attrPath = 'self'
            nodesclean = []
            for node in nodes:
                if node in numberlookup.keys():
                    nodesclean.append(numberlookup[node])
                else:
                    nodesclean.append(node)
            for node in nodesclean[:-1]:
                attrPath  = attrPath + '.' + node
            if elem in list(map(list, zip(*typeNodes)))[0]:
                prop  = property(fget=eval("lambda self: self.daq.getDouble('%s')" %elem),
                                                    fset=eval("lambda self, value: self.daq.getDouble(%s)" %elem))
            else:
                prop  = property(fget=eval("lambda self: self.daq.getSample('%s')" %elem))
            check_add(self, nodesclean)
            print(nodesclean)
            print(attrPath)
            setattr(eval(attrPath), nodesclean[-1],prop)
    def demod_sample(self, demod_numbers, keys_to_include):
            '''
            Returns the sample dict from one demod.
            '''
            datadict = {}
            for i in demod_numbers:
                datadict['demod%i' % i] = {}
                raw = self.daq.getSample('dev1056/DEMODS/%i/SAMPLE' % i)
                for key in keys_to_include:
                    datadict['demod%i' % i][key] = raw[key]
            return datadict

    @property
    def sigout0_offset(self):
            '''
            Returns the output offset in volts
            '''
            offset = self.daq.getDouble('/dev1056/sigouts/0/offset')
            outputrange = self.daq.getDouble('/dev1056/sigouts/0/range')

            return offset*outputrange


    @sigout0_offset.setter
    def sigout0_offset(self,value):
            '''
            Sets the offset in voltage
            '''
            outputrange = self.daq.getDouble('/dev1056/sigouts/0/range')
            self.daq.setDouble('/dev1056/sigouts/0/offset', value/outputrange)

    @property
    def sigout1_offset(self):
            '''
            Returns the output offset in volts
            '''
            offset = self.daq.getDouble('/dev1056/sigouts/1/offset')
            outputrange = self.daq.getDouble('/dev1056/sigouts/1/range')

            return offset*outputrange


    @sigout1_offset.setter
    def sigout1_offset(self,value):
            '''
            Sets the offset in voltage
            '''
            outputrange = self.daq.getDouble('/dev1056/sigouts/1/range')
            self.daq.setDouble('/dev1056/sigouts/1/offset', value/outputrange)

    @property
    def osc0_freq(self):
        '''
        Returns the frequency of osc0
        '''
        return self.daq.getDouble('/dev1056/oscs/0/freq')

    @osc0_freq.setter
    def osc0_freq(self,value):
        '''
        Sets the frequency of osc0
        '''
        return self.daq.setDouble('/dev1056/oscs/0/freq')

    @property
    def osc1_freq(self):
        '''
        Returns the frequency of osc0
        '''
        return self.daq.getDouble('/dev1056/oscs/1/freq')

    @osc0_freq.setter
    def osc1_freq(self,value):
        '''
        Sets the frequency of osc0
        '''
        return self.daq.setDouble('/dev1056/oscs/1/freq')

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
