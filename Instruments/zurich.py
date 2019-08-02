"""
Nowack_Lab high level driver for Zurich HF2LI

Needs: zhinst, numpy, .instrument, time and _future_
"""


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
        self.zurichformatnodes = {}
        self.auxnames = {'auxin0':'auxin0', 'auxin1':'auxin1'}
        self.daq.unsubscribe('/')
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
            nameofattr  = '_'.join(elem.split('/')[2:])
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
                setattr(self.__class__, nameofattr, property(fget=eval(
                "lambda self: {'x': self.daq.getSample('%s')['x'][0]," % elem
                            + "'y':self.daq.getSample('%s')['y'][0]}" % elem)))
    def __getstate__(self):
        zdict = self.daq.get('/'+ self.device_id + '/', True)
        self._save_dict = {}
        for key in zdict.keys():
            self._save_dict['_'.join(key.split('/')).upper()]= zdict[key]
        return self._save_dict

    def convert_output(self, value):
        self.AUXOUTS_0_SCALE
        if not np.isscalar(value):
            value = np.array(value)
            return np.array(value/self.AUXOUTS_0_SCALE)
        return value/self.AUXOUTS_0_SCALE

    def device_id(self):

        return 'Zurich_' + self.daq.device_id

    def convert_node(self, node):
        '''
        Converts a node name from nowack lab format (underscores, no devid)
        to zhist format (/, devid)
        '''
        return '/'+self.device_id.upper()+'/'+ node.replace('_', '/')

    def subscribe(self, nodes):
            '''
            Subscribes to nodes on zurich, and stores names under which to
            return the data.
            nodes (dictionary):keys are names of attributes of the
                                zurich., items are user specified names.

                                A special use case is to rename auxins as user
                                defined strings in the demod returns. In this
                                use case, the keys are 'auxin#', and the items
                                are the user names. Of course, these may also
                                be subscribed in the general way, but then
                                acquisition will not be synchronized.
            '''
            for zurichname in nodes.keys():
                if zurichname in self.auxnames.keys():
                    self.auxnames[zurichname] = nodes[zurichname]
                else:
                    username = nodes[zurichname]
                    if zurichname in self.zurichformatnodes.keys():
                        if username == self.zurichformatnodes[zurichname]:
                            print('Node is already subscribed')
                        else:
                            raise Exception('Two nodes may not be given the'+
                                                                      ' same name')
                    self.zurichformatnodes[self.convert_node(zurichname)] = (
                        username)

            self.daq.subscribe(list(self.zurichformatnodes.keys()))

    def unsubscribe(self, nodes):
            '''
            Unsubscribes to nodes on zurich.
            nodes (list): list of zurich nodes in _ format to unsubscribe
            '''
            zurichunsubnodes = []
            for node in nodes:
                if not self.convert_node(node) in self.zurichformatnodes.keys():
                    print('Not subscribed to node %s' + node )
                else:
                    zurichunsubnodes.append(self.convert_node(node))
                    self.zurichformatnodes.pop(self.convert_node(node))
            self.daq.unsubscribe(zurichunsubnodes)

    def poll(self):
            '''
            Returns stored data in all buffers.

            returns (dict): keys are the names you specified in subscribe for
                            the data. Values are 1D arrays of data.
            '''
            returned_data = self.daq.poll(1,100, 0x0004, True)
            formatteddata = {}
            for key in returned_data.keys():
                if key.upper() in self.zurichformatnodes.keys():
                    name = self.zurichformatnodes[key.upper()]
                    #ourformatkey = '_'.join(key.upper().split('/')[2:])
                    if key.split('/')[-1] == 'sample':
                        formatteddata[name] = {}
                        formatteddata[name]['x']  = returned_data[key]['x']
                        formatteddata[name]['y']  = returned_data[key]['y']
                        formatteddata[name][self.auxnames['auxin0']]  = (
                                                returned_data[key]['auxin0'])
                        formatteddata[name][self.auxnames['auxin1']]  = (
                                                returned_data[key]['auxin1'])
                    else:
                        formatteddata[name] = returned_data[key]
                else:
                    raise Exception('Unrecognized data returned')
            return formatteddata

class HF2LI1(zurichInstrument):
      pass
class HF2LI2(zurichInstrument):
      pass
class HF2LI3(zurichInstrument):
      pass
class MFLI1(zurichInstrument):
      pass
class MFLI2(zurichInstrument):
      pass
class MFLI3(zurichInstrument):
      pass
