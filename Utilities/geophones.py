import numpy as np

class Geophone(object):
    '''
    Conversions for geophones
    '''
    conversion = 0
    c_acc = lambda f, G: np.abs(G * 2j*np.pi*f /
                                ((2j*np.pi*f)**2 + 18*2j*np.pi*f + 760))
    c_vel = lambda f, G: np.abs(G * (2j*np.pi*f)**2 /
                                ((2j*np.pi*f)**2 + 18*2j*np.pi*f + 760))
    c_pos = lambda f, G: np.abs(G * (2j*np.pi*f)**3 /
                                ((2j*np.pi*f)**2 + 18*2j*np.pi*f + 760))

    def __init__(self, 
                 conversion=31.5 # V/(m/s)
                 ):
        self.conversion = conversion

    def convert(self, psd_V, f):
        '''
        Converts the psd in f space from volts to 
        [acceleration, velocity, position]
        '''
        acc = psd_V / self.__class__.c_acc(f, self.conversion)
        vel = psd_V / self.__class__.c_vel(f, self.conversion)
        pos = psd_V / self.__class__.c_pos(f, self.conversion)

        return [acc, vel, pos]
