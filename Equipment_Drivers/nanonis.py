import serial
import struct

class HVA():
    '''
    For remote monitoring of the Nanonis HVA4 High Voltage Amplifier. Note that you must set gain and outputs manually. This is just for double checking in code/confirming gain values. NOT TESTED YET, GET SERIAL CABLE
    '''    
    def __init__(self, comm='COM1', baud=9600):
        self._ser = serial.Serial(comm, baud, timeout=2)
        
    def get_data(self):
        data = self._ser.read(2)
        print(data)
        #print(struct.unpack(">L", data)[0])
        return hex(data)
        
    def checkSupply(self):
        return bool(0x0200&self.get_data() >> 9)
    
    def isEnabled(self, channel):
        if channel in ['aux', 'AUX']:
            return bool(0x8000&self.get_data() >> 15)
        elif channel in ['z','Z']:
            return bool(0x4000&self.get_data() >> 14)
        elif channel in ['y','Y','x','X']:
            return bool(0x2000&self.get_data() >> 13)
        else:
            raise Exception('x, y, z, or aux!')
    
    def get_gain(self, channel):
        gain_bits = 0x0000
        if channel in ['aux', 'AUX']:
            gain_bits = (0x0060&self.get_data()) >> 5
        elif channel in ['z','Z']:
            gain_bits = (0x0003&self.get_data())
        elif channel in ['y','Y','x','X']:
            gain_bits = (0x000C&self.get_data()) >> 2
        else:
            raise Exception('x, y, z, or aux!')
            
        if gain_bits == 0b00:
            return 1
        elif gain_bits == 0b10:
            return 4
        elif gain_bits == 0b01:
            return 15
        elif gain_bits == 0b11:
            return 40
            
    def get_z_pol(self):
        return bool(0x0010&self.get_data() >> 4)    

if __name__ == '__main__':
    """ Testing the code.  """
    amp = HVA()
   
    amp.isEnabled('x')
    amp.get_gain('x')
   