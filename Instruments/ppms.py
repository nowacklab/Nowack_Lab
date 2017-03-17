# PPMS Control Driver written by Guen Prawiroatmodjo c. Nov 2015, adapted for use by the Nowack lab Jan 2017

from .instrument import Instrument
import select

class PPMS(Instrument):
    r'''
    For remote operation of the Quantum Design PPMS.
    Makes use of PyQDInstrument (https://github.com/guenp/PyQDInstrument)
    Make sure to run PyQDInstrument.run_server() in an IronPython console on a machine that can connect to the PPMS control PC's QDInstrument_Server.exe program.
    The basic commands to set up the server for the blue PPMS are:
        import sys
        sys.path.append(r'C:\Users\ccmradmin\Documents\GitHub') (if pyQDInstrument is in the GitHub directory)
        import pyQDInstrument as pqi
        pqi.run_server('192.168.0.103', 50009, '192.168.0.100', 11000)
    Attributes represent the system control parameters:
    'temperature', 'temperature_rate', 'temperature_approach', 'field', 'field_rate', 'field_approach', 'field_mode', 'temperature_status', 'field_status', 'chamber'
    '''
    def __init__(self, host, port, s=None):
        if s == None:
            self._s = connect_socket(host, port)
        else:
            self._s = s
        self._units = {'temperature': 'K', 'temperature_rate': 'K/min','field': 'Oe', 'field_rate': 'Oe/min'}
        for param in ['temperature', 'temperature_rate', 'field', 'field_rate', 'temperature_approach', 'field_approach', 'field_mode']:
            setattr(PPMS,param,property(fget=eval("lambda self: self._get_param('%s')" %param),
                                                fset=eval("lambda self, value: self._set_param('%s',value)" %param)))
        for param in ['temperature_status', 'field_status', 'chamber']:
            setattr(PPMS,param,property(fget=eval("lambda self: self._get_param('%s')" %param)))
        self._params = ['temperature', 'temperature_rate', 'temperature_approach', 'field', 'field_rate', 'field_approach', 'field_mode', 'temperature_status', 'field_status', 'chamber']
        self._functions = []

    def __getstate__(self):
        d = {}
        for param in self._params:
            d[param] = getattr(self, param)
        return d

    def __setstate__(self, state):
        self.__dict__.update(state)

    def _get_param(self, param):
        return ask_socket(self._s, param)

    def _set_param(self, param, value):
        if type(value) == str:
            cmd = "%s = '%s'" %(param, value)
        else:
            cmd = '%s = %s' %(param, value)
        return ask_socket(self._s, cmd)

    def __del__(self):
        if hasattr(self, '_s'):
            self._s.close()

def connect_socket(HOST, PORT):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    return s

def socket_poll(s):
    inputready, o, e = select.select([s],[],[], 0.0)
    return len(inputready)>0

def ask_socket(s, cmd, startbytes=0):
    data = ask_socket_raw(s, cmd)
    if startbytes>0:
        data = data[startbytes:]
    try:
        ans = eval(data)
    except (IndentationError, SyntaxError, NameError, TypeError):
        ans = data.decode()
    return ans

def ask_socket_raw(s, cmd):
    import time
    '''query socket and return response'''
    #empty socket buffer
    while socket_poll(s):
        s.recv(1024)
        time.sleep(.01)
    s.sendall(cmd.encode())
    while not socket_poll(s):
        time.sleep(.01)
    data = b''
    while socket_poll(s):
        data += s.recv(1024)
        time.sleep(.01)
    return data
