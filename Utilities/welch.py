import scipy.signal as signal

class Welch:
    '''
    Tool for computing the power spectral density or
    power spectrum for a signal
    '''

    def __init__(self):
        pass

    @staticmethod
    def welchf(v, sample_rate, freqspace,
                windowfnct = 'blackmanharris',
                scaling='density'
              ):
        '''
        Computes the power spectral density or power spectrum

        Input:
            v (nparray):
                signal to take the fourier transform of

            sample_rate (float):
                sample rate of the measurement in Hz

            freqspace (float):
                desired frequency spacing of final spectrum in Hz

            windowfnct (string):
                type of window function used by welch

            scaling (string):
                'density'  for power spectral density
                'spectrum' for power spectrum

        Returns: [f, psd]
            f (nparray):
                frequencies
            psd (nparray):
                power at those frequencies f, in units of [v]^2/Hz or [v]^2
psd
        '''
        [w, nperseg] = Welch._makewindow(freqspace, sample_rate, windowfnct)
        return signal.welch(v, sample_rate, window=w, nperseg=nperseg,
                            scaling=scaling)

    @staticmethod
    def _makewindow(freqspace, sample_rate, windowfnct):
        n = int(sample_rate/freqspace)
        return [ getattr(signal, windowfnct)(n, False), n]

