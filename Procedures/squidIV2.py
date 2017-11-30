import numpy as np
import matplotlib.pyplot as plt
from ..Utilities.save import Measurement

class SQUID_IV(Measurement):
    _daq_inputs = ['iv']
    _daq_outputs = ['iv']
    instrument_list = ['daq']

    _IV_MAX_I = 100e-6

    def __init__(self,
                 instruments = {},
                 iv_Is = np.linspace(-100e-6,100e-6,1000),
                 iv_Rbias = 2000,
                 samplerate = 1000,
                 gain = 5000, # FIXME
                 ):
        super().__init__(instruments=instruments)
        
        self.iv_Rbias  = iv_Rbias
        self.iv_Is     = np.array(iv_Is)
        self.iv_Vs     = self.iv_Is * self.iv_Rbias
        self.samplerate= samplerate
        self.gain      = gain

        self._safetychecker()

    def _safetychecker(self):
        if max(abs(self.iv_Is)) > SQUID_IV._IV_MAX_I:
            print('WARNING: max(IV current) > {0}'.format(SQUID_IV._IV_MAX_I))

    def do(self, hysteresis=True, safe=True, plot=True, removeplot=False):
        if safe: # sweeps slowly to the first voltage
            _,_ = self.daq.singlesweep('iv', self.iv_Vs[0], 
                                       numsteps=len(self.iv_Vs)/2)
            #pre_od, pre_r = self.daq.sweep(
            #    Vstart = {'iv': self.daq.outputs['iv'].V},   
            #    Vend   = {'iv': self.iv_Vs[0]},
            #    chan_in = self._daq_inputs,
            #    sample_rate = self.samplerate,
            #    numsteps = len(self.iv_Vs)/2
            #)

        fu_od, fu_r = self.daq.sweep(
            Vstart = {'iv': self.iv_Vs[ 0]},
            Vend   = {'iv': self.iv_Vs[-1]},
            chan_in = self._daq_inputs,
            sample_rate = self.samplerate,
            numsteps = len(self.iv_Vs)
        )

        if hysteresis:
            fd_od, fd_r = self.daq.sweep(
                Vstart = {'iv': self.iv_Vs[-1]},
                Vend   = {'iv': self.iv_Vs[ 0]},
                chan_in = self._daq_inputs,
                sample_rate = self.samplerate,
                numsteps = len(self.iv_Vs)
            )

        if safe: # sweep slowly to zero
            _,_ = self.daq.singlesweep('iv', 0
                                       numsteps=len(self.iv_Vs)/2)
            #post_od, post_r = self.daq.sweep(
            #    Vstart = {'iv': self.daq.outputs['iv'].V},   
            #    Vend   = {'iv': 0},
            #    chan_in = self._daq_inputs,
            #    sample_rate = self.samplerate,
            #    numsteps = len(self.iv_Vs)/2
            #)

        self.Vmeas_up = np.array( fu_r['iv']/self.gain)
        self.Vsrc_up  = np.array(fu_od['iv'])

        if hysteresis:
            self.Vmeas_down = np.array(fd_r['iv']/self.gain)
            self.Vsrc_down  = np.array(fd_od['iv'])
        
        if plot:
            self.plot(hysteresis=hysteresis)
        if removeplot:
            plt.close()


    def plot(self, hysteresis=True):
        super().plot()
        self.ax.plot(self.Vsrc_up / self.iv_Rbias / 1e-6, 
                     self.Vmeas_up / 1e-6,
                     label='UP')
        if hysteresis:
            self.ax.plot(self.Vsrc_down / self.iv_Rbias / 1e-6,
                         self.Vmeas_down / 1e-6,
                         label='DOWN')
            self.ax.legend()
        self.ax.set_xlabel('I ($\mu A$)')
        self.ax.set_ylabel('V ($\mu V$)')
        self.ax.annotate(self.filename, xy=(.02,.98), xycoords='axes fraction',
                         fontsize=8, ha='left', va='top', family='monospace')

    def plot_resistance(self, hysteresis=True):
        self.ax_res = self.ax.twinx()
        s = self.Vsrc_up/self.iv_Rbias
        spacing = abs(s[0]-s[1])
        self.ax_res.plot(self.Vsrc_up / self.iv_Rbias / 1e-6,
                         np.gradient(savitzky_golay(self.Vmeas_up, 15, 13, 0), spacing),
                         #savitzky_golay(self.Vmeas_up, 15, 13, 0)/1e-6,
                         linestyle='-',
                         marker='o', markersize=1,
                         label='UP: dv/di')
        if hysteresis:
            self.ax_res.plot(self.Vsrc_down / self.iv_Rbias / 1e-6,
                         np.gradient(self.Vmeas_up, spacing),
                         linestyle='',
                         marker='o', markersize=1,
                         label='DOWN: dv/di')
        self.ax_res.set_ylabel('Resistance ($\Omega$)')
        self.ax_res.legend()


    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        plt.pause(.01)


class SQUID_Mod(Measurement):
    _daq_outputs = ['mod']

    def __init__(self,
                 instruments = {},
                 iv_Is = np.linspace(-100e-6,100e-6,100),
                 mod_Is = np.linspace(-100e-6,100e-6,100),
                 iv_Rbias = 2000,
                 mod_Rbias = 2000,
                 samplerate = 1000,
                 gain = 5000, # FIXME
                 ):
        super().__init__(instruments=instruments)
        self.mod_Is     = mod_Is
        self.iv_Is      = iv_Is
        self.iv_Rbias   = iv_Rbias
        self.mod_Rbias  = mod_Rbias
        self.samplerate = samplerate
        self.gain       = gain

        self.mod_Vs = self.mod_Is / self.mod_Rbias

    def do(self):

        _,_ = daq.singlesweep('mod', self.mod_Vs[0], 
                              numsteps=len(self.mod_Vs)/2)
        filenames = []
        ivs = []
        self.V = np.full( (len(self.mod_Is), len(self.iv_Is)), np.nan)
        # multithread this?
        for m_v in self.mod_Vs:
            daq.outputs['mod'].V = m_v
            iv = SQUID_IV(instruments, 
                          iv_Is = self.iv_Is,
                          iv_Rbias = self.iv_Rbias,
                          samplerate = self.samplerate,
                          gain = self.gain
                         )
            ivs.append(iv)
            iv.run(removeplot=True)

        _,_ = daq.singlesweep('mod', 0, numsteps=len(self.mod_Vs)/2)
       
        for i,iv in zip(range(len(ivs)),ivs):
            self.V[:][i] = iv.Vmeas_up
        

        self.plot()

    def setup_plots(self):
        pass

    def plot(self):
        pass



def savitzky_golay(y, window_size, order, deriv=0, rate=1):
    r"""Smooth (and optionally differentiate) data with a Savitzky-Golay filter.
    The Savitzky-Golay filter removes high frequency noise from data.
    It has the advantage of preserving the original shape and
    features of the signal better than other types of filtering
    approaches, such as moving averages techniques.
    Parameters
    ----------
    y : array_like, shape (N,)
        the values of the time history of the signal.
    window_size : int
        the length of the window. Must be an odd integer number.
    order : int
        the order of the polynomial used in the filtering.
        Must be less then `window_size` - 1.
    deriv: int
        the order of the derivative to compute (default = 0 means only smoothing)
    Returns
    -------
    ys : ndarray, shape (N)
        the smoothed signal (or it's n-th derivative).
    Notes
    -----
    The Savitzky-Golay is a type of low-pass filter, particularly
    suited for smoothing noisy data. The main idea behind this
    approach is to make for each point a least-square fit with a
    polynomial of high order over a odd-sized window centered at
    the point.
    Examples
    --------
    t = np.linspace(-4, 4, 500)
    y = np.exp( -t**2 ) + np.random.normal(0, 0.05, t.shape)
    ysg = savitzky_golay(y, window_size=31, order=4)
    import matplotlib.pyplot as plt
    plt.plot(t, y, label='Noisy signal')
    plt.plot(t, np.exp(-t**2), 'k', lw=1.5, label='Original signal')
    plt.plot(t, ysg, 'r', label='Filtered signal')
    plt.legend()
    plt.show()
    References
    ----------
    .. [1] A. Savitzky, M. J. E. Golay, Smoothing and Differentiation of
       Data by Simplified Least Squares Procedures. Analytical
       Chemistry, 1964, 36 (8), pp 1627-1639.
    .. [2] Numerical Recipes 3rd Edition: The Art of Scientific Computing
       W.H. Press, S.A. Teukolsky, W.T. Vetterling, B.P. Flannery
       Cambridge University Press ISBN-13: 9780521880688
    """
    import numpy as np
    from math import factorial

    try:
        window_size = np.abs(np.int(window_size))
        order = np.abs(np.int(order))
    except ValueError:
        raise ValueError("window_size and order have to be of type int")
    if window_size % 2 != 1 or window_size < 1:
        raise TypeError("window_size size must be a positive odd number")
    if window_size < order + 2:
        raise TypeError("window_size is too small for the polynomials order")
    order_range = range(order+1)
    half_window = (window_size -1) // 2
    # precompute coefficients
    b = np.mat([[k**i for i in order_range] for k in range(-half_window, half_window+1)])
    m = np.linalg.pinv(b).A[deriv] * rate**deriv * factorial(deriv)
    # pad the signal at the extremes with
    # values taken from the signal itself
    firstvals = y[0] - np.abs( y[1:half_window+1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half_window-1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    return np.convolve( m[::-1], y, mode='valid')
