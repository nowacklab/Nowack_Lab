import visa
import atexit
import time
import telnetlib
import re

class Attocube():
    '''
    For remote operation of the Attocubes. Order of axes is X, Y, Z (controllers 1,2,3 are in that order). 
    
    To test: up/down fanciness with negative signs. I think it works, but not 100%
    '''
    _stages = ['x','y','z']
    _modes = ['gnd','cap','stp']
    
    def __init__(self, montana, host='192.168.69.3', port=7230):
        self._tn = telnetlib.Telnet(host, port, 5) # timeout 5 seconds
        self._tn.read_until(b"Authorization code: ") #skips to pw entry
        self._tn.write(b'123456'+ b'\n') #default password
        self._tn.read_until(b'> ')        # skip to input

        self._freq = {}
        self._mode = {}
        self._V = {}
        self._cap = {}
        
        self.freq
        self.mode
        self.V
        
        self._freq_lim = 1000 # self-imposed, 10000 is true max
        self._step_lim = 5000 #self-imposed, no true max
        if montana.temperature['platform'] < 10:
            self._V_lim = 55.000 #LT limit
        else:
            self._V_lim = 40.000 #RT limit
       
        self.check_voltage()

        atexit.register(self.stop)  # will stop all motion if program quits     
        
    def help(self):
        msg = self.send('help')
        print(msg)
        
    @property
    def freq(self):
        for i in range(3):
            msg = self.send('getf %i' %(i+1)) # i+1 -> controllers labeled 1,2,3, not 0,1,2
            self._freq[self._stages[i]] = int(self._getValue(msg))     
        return self._freq
        
    @freq.setter
    def freq(self, f):
        for key, value in f.items():
            if value > self._freq_lim:
                raise Exception('frequency out of range, max %i Hz' %self._freq_lim)
            elif value < 1:
                value = 1
            self.send('setf %i %i' %(self._stages.index(key)+1, value)) # e.g. setf 1 100 to set x axis to 100 Hz 
            self._freq[key] = value
            
    @property
    def mode(self):
        """ Mode, choose from: gnd, cap, stp """
        for i in range(3):
            msg = self.send('getm %i' %(i+1)) # i+1 -> controllers labeled 1,2,3, not 0,1,2
            self._mode[self._stages[i]] = self._getValue(msg)
        return self._mode
        
    @mode.setter
    def mode(self, m):
        for key, value in m.items():
            if value not in self._modes:
                raise Exception('Bad mode for stage %i' %(i+1))
            else:
                msg = self.send('setm %i %s' %(self._stages.index(key)+1, value))
                self._mode[key] = value

    @property
    def V(self):
        for i in range(3):
            msg = self.send('getv %i' %(i+1)) # i+1 -> controllers labeled 1,2,3, not 0,1,2
            self._V[self._stages[i]] = float(self._getValue(msg))     
        return self._V
        
    @V.setter
    def V(self, v):
        for key, value in v.items():
            if value > self._V_lim:
                raise Exception('voltage out of range, max %f V' %self._V_lim)
            elif value < 0:
                raise Exception('voltage out of range, min 0 V')
            self.send('setv %i %i' %(self._stages.index(key)+1, value)) # e.g. setf 1 10 to set x axis to 10 V 
            self._V[key] = value
            
    @property
    def cap(self):
        self.mode = {'x':'cap', 'y':'cap', 'z':'cap'}
        for i in range(3):
            self.send('capw %i' %(i+1)) # wait for capacitance measurement to finish
            msg = self.send('getc %i' %(i+1))
            self._cap[self._stages[i]] = float(self._getValue(msg))    
        return self._cap

    def check_voltage(self):
        for key, value in self.V.items():
            if value > self._V_lim:
                self.V = {key: self._V_lim}
                print("Axis %s voltage was too high, set to" %(key, self._V_lim))
        
    def ground(self):
        self.mode = {'x':'gnd', 'y':'gnd', 'z':'gnd'}

    def step(self, axis, numsteps, updown):
        """ steps up for number of steps given; if None, ignored; if 0, continuous"""
        self.check_voltage()
    
        if updown not in ['u','d']:
            raise Exception('What doesn\'t come up must come down!')
        
        self.mode = {axis: 'stp'}
        if numsteps > self._step_lim:
            raise Exception('too many steps! Max %i' %self._step_lim)
        elif numsteps == 0:
            raise Exception('That won\'t get you anywhere!')
            # msg = self.send('step%s %i c' %(updown, i+1)) NO!!!!! THIS IS BAD!!! WE DON'T WANT TO MOVE CONTINUOUSLY
        else:
            self.send('step%s %i %i' %(updown, self._stages.index(axis)+1, numsteps))
            self.send('stepw %i' %(self._stages.index(axis)+1)) # waits until motion has ended to run next command; Attocube.stop will stop motion no matter what
        self.mode = {axis: 'gnd'}
    
    def move(self, numsteps):
        self.up(numsteps)
    
    def up(self, numsteps):
        for axis, num in numsteps.items():
            self.step(axis, num, 'u')
    
    def down(self, numsteps):
        for axis, num in numsteps.items():
            self.step(axis, num, 'd')
            
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
    
    
    
    #### EVERYTHING BELOW IS OUT OF DATE
    
    
    # atto = Attocube()
    # # atto.V = [55, 55, 55]
    # atto.mode = ['gnd', 'gnd', 'stp']
    
    # atto.step([None, None, 0], [None, None, '+'])
    # # # prescribed number of steps, will wait by default until current action is done. Does axes sequentially
    # # for i in range(2):
        # # atto.step([None, 2000, 2000], [None, '+', '+'])
        # # # time.sleep(5)
        # # atto.step([None, 2000, 2000], [None, '-', '-'])
        # # # time.sleep(5)
    # time.sleep(2)
    # # atto.stop()
    # #continuous motion - must stop before changing direction
        # # for i in range(2):
        # # atto.step([None, None, 0], [None, None, 'up'])
        # # time.sleep(5)
        # # atto.stop() # must stop before changing direction!
        # # atto.step([None, None, 0], [None, None, 'down'])
        # # time.sleep(5)
        # # atto.stop()
    # # print(atto.cap(True))
    # # print(atto.frequency)
    # # atto.frequency = [200, 800, 800]
    # # print(atto.frequency)
    # # print(atto.mode)
    # # atto.mode = ['gnd', None, None]
    # # print(atto.mode)
    # # print(atto.voltage)
    # # atto.voltage = [50, 50, 50]
    # # print(atto.voltage)

    # """ Test code that worked"""
    # # import telnetlib
    # # HOST = '192.168.69.3'
    # # print(1)
    # # tn = telnetlib.Telnet(HOST,7230)   
    # # print(2);
    # # print(tn.read_until(b"Authorization code: "))
    # # print(3)
    # # tn.write(b'123456'+ b'\n')
    # # print(4)
    # # print(tn.read_until(b'> '))
    # # print(4.5)
    # # tn.write(b"getf 1\n") 
    # # print(5)
    # # print(tn.read_until(b'> '))
    # # print(5.5)
    # ###########################
    

    
   