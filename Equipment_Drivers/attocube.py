import visa
import atexit
import time
import telnetlib
import re

class Attocube():
    '''
    For remote operation of the Attocubes. Order of axes is Z, Y, X (controllers 1,2,3 are in that order). 
    
    To test: up/down fanciness with negative signs. I think it works, but not 100%
    '''
    Stages = {'z': 1, 'y': 2, 'x':3}
    
    def __init__(self, low_temp=False, host='192.168.69.3', port=7230):
        self._tn = telnetlib.Telnet(host, port, 5) # timeout 5 seconds
        self._tn.read_until(b"Authorization code: ") #skips to pw entry
        self._tn.write(b'123456'+ b'\n') #default password
        self._tn.read_until(b'> ')        # skip to input

        self._freq = None
        self._mode = None
        self._voltage = None
        self._cap = None
        
        self.mode
        self.frequency
        self.voltage
        self.cap()
        
        self._freq_lim = 1000 # self-imposed, 10000 is true max
        self._step_lim = 5000 #self-imposed, no true max
        if low_temp:
            self._voltage_lim = 55.000 #RT limit
        else:
            self._voltage_lim = 40.000 #RT limit

        self._modes = ['gnd','cap','stp']
        atexit.register(self.stop)  # will stop all motion if program quits     
        
    def help(self):
        msg = self.send('help')
        print(msg)
        
    @property
    def frequency(self):
        if self._freq == None:
            self._freq = []
            for i in range(3):
                msg = self.send('getf %i' %(i+1))
                self._freq.append(int(self._getValue(msg)))    
        return self._freq
        
    @frequency.setter
    def frequency(self, f):
        for i in range(3):
            if f[i] == None:
                continue
            if f[i] > self._freq_lim:
                raise Exception('frequency out of range, max %i Hz' %self._freq_lim)
            elif f[i] < 1:
                f[i] = 1
            msg = self.send('setf %i %i' %(i+1, f[i]))
            self._freq[i] = f[i]
            
    @property
    def mode(self):
        """ Mode: gnd, cap, stp """
        if self._mode == None:
            self._mode = []
            for i in range(3):
                msg = self.send('getm %i' %(i+1))
                strmsg = self._getValue(msg)
                self._mode.append(strmsg)  
        return self._mode
        
    @mode.setter
    def mode(self, mode):
        for i in range(3):
            if mode[i] == None:
                continue
            if mode[i] not in self._modes:
                print('Bad mode for stage %i' %(i+1))
            else:
                msg = self.send('setm %i %s' %(i+1, mode[i]))
                self._mode[i] = mode[i]

    @property
    def voltage(self):
        if self._voltage == None:
            self._voltage = []
            for i in range(3):
                msg = self.send('getv %i' %(i+1))
                self._voltage.append(float(self._getValue(msg)))    
        return self._voltage
        
    @voltage.setter
    def voltage(self, v):
        for i in range(3):
            if v[i] == None:
                continue
            if v[i] > self._voltage_lim:
                raise Exception('voltage out of range, max %f V' %self._voltage_lim)
            elif v[i] < 0:
                raise Exception('voltage out of range, min 0 V')
            msg = self.send('setv %i %f' %(i+1, v[i]))
            self._voltage[i] = float(v[i])                

    def ground(self):
        self.mode = ['gnd', 'gnd', 'gnd']
    
    def cap(self, refresh=False):
        if refresh:
            self.mode = ['cap', 'cap', 'cap']
            for i in range(3):
                msg = self.send('capw %i' %(i+1)) # wait for capacitance measurement to finish
        self._cap = []
        for i in range(3):
            msg = self.send('getc %i' %(i+1))
            self._cap.append(float(self._getValue(msg)))    
        return self._cap

    def step(self, numsteps, upordown, wait=True):
        """ steps up for number of steps given; if None, ignored; if 0, continuous"""
        for i in range(3):
            if numsteps[i] == None:
                continue
            if upordown[i] in ('up', 'Up', 'UP', 'u', 'U', '+'):
                updown = 'u'
            elif upordown[i] in ('down', 'Down', 'DOWN', 'd', 'D', '-'):
                updown = 'd'
            else:
                print('What doesn\'t come up must come down!')
                continue
            if self._mode[i] != 'stp':
                print('Must be in stp mode!')
                continue               
            if numsteps[i] > self._step_lim:
                raise Exception('too many steps! Max %i' %self._step_lim)
            elif numsteps[i] == 0:
                msg = self.send('step%s %i c' %(updown, i+1))
            else:
                msg = self.send('step%s %i %i' %(updown, i+1, numsteps[i]))
                if wait:
                    msg = self.send('stepw %i' %(i+1)) # waits until motion has ended to run next command; Attocube.stop will stop motion no matter what
    
    def move(self, numsteps):
        self.up(numsteps)
    
    def up(self, numsteps):
        self.step([abs(num) if num != None else None for num in numsteps], [None if numsteps[i]==None else 'up' if numsteps[i]>0 else 'down' for i in range(3)]) # numsteps negative means go down
    
    def down(self, numsteps):
        self.step([abs(num) if num != None else None for num in numsteps], [None if numsteps[i]==None else 'down' if numsteps[i]>0 else 'up' for i in range(3)])

    def stop(self):
        for i in range(3):
            msg = self.send('stop %i' %(i+1))
        
    def send(self, cmd):      
        cmd = cmd + '\n'
        try:
            self._tn.write(bytes(cmd, 'ascii'))
        except:
            print("Could not connect!")
        return self._tn.read_until(b'\n> ') # looks for input line \n fixed bug with help
        
    def _getDigits(self,msg):
        """ Extracts digits from attocube message """
        for s in str(msg).split():
            if s.isdigit():
                return int(s)
        raise Exception('no numbers found') # will only run if number is not returned
        # integ = int(re.search(r'\d+', str(msg)).group())

    def _getValue(self, msg):
        """ Looks after equals sign in returned message to get value of parameter """
        return msg.split()[msg.split().index(b'=')+1].decode('utf-8') #looks after the equal sign


if __name__ == '__main__':
    """ Testing the code. If for some reason communication does not work, first check for IP 192.168.69.3 in cmd using arp -a, then troubleshoot using cygwin terminal: telnet 192.168.69.3 7230 """
    atto = Attocube()
    # atto.voltage = [55, 55, 55]
    atto.mode = ['gnd', 'gnd', 'stp']
    
    atto.step([None, None, 0], [None, None, '+'])
    # # prescribed number of steps, will wait by default until current action is done. Does axes sequentially
    # for i in range(2):
        # atto.step([None, 2000, 2000], [None, '+', '+'])
        # # time.sleep(5)
        # atto.step([None, 2000, 2000], [None, '-', '-'])
        # # time.sleep(5)
    time.sleep(2)
    # atto.stop()
    #continuous motion - must stop before changing direction
        # for i in range(2):
        # atto.step([None, None, 0], [None, None, 'up'])
        # time.sleep(5)
        # atto.stop() # must stop before changing direction!
        # atto.step([None, None, 0], [None, None, 'down'])
        # time.sleep(5)
        # atto.stop()
    # print(atto.cap(True))
    # print(atto.frequency)
    # atto.frequency = [200, 800, 800]
    # print(atto.frequency)
    # print(atto.mode)
    # atto.mode = ['gnd', None, None]
    # print(atto.mode)
    # print(atto.voltage)
    # atto.voltage = [50, 50, 50]
    # print(atto.voltage)

    """ Test code that worked"""
    # import telnetlib
    # HOST = '192.168.69.3'
    # print(1)
    # tn = telnetlib.Telnet(HOST,7230)   
    # print(2);
    # print(tn.read_until(b"Authorization code: "))
    # print(3)
    # tn.write(b'123456'+ b'\n')
    # print(4)
    # print(tn.read_until(b'> '))
    # print(4.5)
    # tn.write(b"getf 1\n") 
    # print(5)
    # print(tn.read_until(b'> '))
    # print(5.5)
    ###########################
    

    
   