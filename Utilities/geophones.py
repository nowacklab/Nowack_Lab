import numpy as np
from scipy.optimize import curve_fit

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

class Geophone_cal(object):
    '''
    Fit params and functions for fitting geophone calibration data
    '''

    def __init__(self, Rs):
        self.arg0 = [4.5, 2, 380, .1, 33**2/.023]
        self.Zi = 10e9
        self.Rs = Rs

    def _Ze(self, f, f0, Q0, Rt, Lt, Z12sqOvMo):
        return Rt + 2j * np.pi * f * Lt + Z12sqOvMo * (2j * np.pi * f)/(
                (2 * np.pi*f0)**2 * (1 - (f/f0)**2 + (1j/Q0)* (f/f0)))

    def _Zsp(self, Rs, Zi):
        return Rs*Zi/(Rs + Zi) 

    def _Zep(self, Ze, Zi):
        return Ze*Zi/(Ze + Zi) 

    def rho(self, f, f0, Q0, Rt, Lt, Z12sqOvMo):
        Ze = self._Ze(f, f0, Q0, Rt, Lt, Z12sqOvMo)
        Zep = self._Zep(Ze, self.Zi)
        return np.abs(Zep/(Zep + self._Zsp(self.Rs, self.Zi)))

    def calfit(self, f, dft):
        return self._calfit(f, dft, self.arg0)

    def _calfit(self, f, dft, p0):
        popt, pcov = curve_fit(self.rho, f, dft, p0=p0)
        return popt, pcov
