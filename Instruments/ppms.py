'''
PPMS Control Driver written by Guen Prawiroatmodjo c. Nov 2015
Adapted for use by the Nowack lab Jan 2017
'''

from .instrument import Instrument
import select, os, time, subprocess

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
    _pid = None # process id number for server

    def __init__(self, host='192.168.0.103', port=50009, s=None):
        '''
        Default host and port are for the PPMS measurement computer.
        '''
        # Establish connection to the socket.
        if s == None:
            self._start_server(host, port)
        else:
            self._s = s

        self._units = {'temperature': 'K', 'temperature_rate': 'K/min','field': 'Oe', 'field_rate': 'Oe/min'}

        # Getters and setters for available commands
        for param in ['temperature', 'temperature_rate', 'field', 'field_rate', 'temperature_approach', 'field_approach', 'field_mode']:
            setattr(PPMS,param,property(fget=eval("lambda self: self._get_param('%s')" %param),
                                                fset=eval("lambda self, value: self._set_param('%s',value)" %param)))
        for param in ['temperature_status', 'field_status', 'chamber']:
            setattr(PPMS,param,property(fget=eval("lambda self: self._get_param('%s')" %param)))
        self._params = ['temperature', 'temperature_rate', 'temperature_approach', 'field', 'field_rate', 'field_approach', 'field_mode', 'temperature_status', 'field_status', 'chamber']
        self._functions = []

    def __del__(self):
        if self._pid is not None:
            self.kill_server()

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

    def _start_server(self, host, port):
        '''
        Start background IronPython running run_server_blue.py
        This process runs in the jupyter notebook cmd prompt.
        Window text will show a mishmash of a normal cmd prompt and
        the one used to start jupyter notebook.
        '''
        # Run script to start PyQDInstrument server
        ironpython = r'"C:\Program Files\IronPython 2.7\ipy.exe"'
        here = os.path.dirname(__file__)
        path_to_script = os.path.join(here,
                           'ppms_server/run_server_blue.py')

        print('Launching IronPython server...')

        # Get current process id list.
        get_pids_path = os.path.join(here, 'ppms_server/get_pids.bat')
        p = subprocess.Popen(get_pids_path, stdout=subprocess.PIPE)
        out = p.communicate()
        out = out[0].decode()
        i = out.find('echo')
        pids = out[i:].split()[1] # extract printed output from batch
                                  # this is a list of open PIDs for ipy.exe
        pids_no_p = pids.replace('p', '') # p added by script

        i = -1
        try:
            i = int(pids_no_p.split(' ')[0]) # Passes if there one or more PID numbers.
        except: # try fails if no PID numbers. But this is the good case!
            pass

        if i != -1: # if there is already a PID number:
            self._pid = i
            self.kill_server() # kill that communication.

        # Start the ironpython ipy.exe server
        os.system('start /B cmd /k %s %s %s %i' %(ironpython, path_to_script, host, port))

        # Compare PID load_instruments
        p = subprocess.Popen(os.path.join(here, 'ppms_server','compare_pids.bat %s') %pids, stdout=subprocess.PIPE)
        out = p.communicate()
        out = out[0].decode()
        i = out.find('echo')
        self._pid = out[i:].split()[2] # This is the PID of the ipy.exe server

        time.sleep(1)
        print('Attempting to connect...')
        try:
            self._s = connect_socket(host, port)
        except Exception as e:
            self.kill_server()
            raise e
        print('PPMS Connected. Process ID %s' %self._pid)

    def kill_server(self,):
        '''
        Terminates the running IronPython (ipy.exe) server and closes cmd window.
        WARNING: Assumes that the only instance of ipy.exe is for the PPMS server.
        In future, if you can figure out the correct process ID, then
        add '/fi "PID eq %s"' in between /f and /im, and then format the string
        with %PID_number.
        '''
        err = os.system('taskkill /f /fi "PID eq %s" /im ipy.exe' %self._pid)
        # if err == 0:
        #     print('Killed IronPython server with PID %s' %self._pid)
        # else:
        #     print('Failed killing IronPython server with PID %s' %self._pid)


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
