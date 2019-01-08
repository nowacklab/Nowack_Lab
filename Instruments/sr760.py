from .instrument import VISAInstrument
import numpy as np

class SR760(VISAInstrument):
    _idn = 'SR760'
    _NUM_BINS = 400

    def __init__(self, gpib_address=''):
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address = gpib_address

        self._init_visa(gpib_address, termination='\n')

    def query(self, cmd, timeout=3000):
        '''
        Write and read combined operation.
        Default timeout 3000 ms. None for infinite timeout
        Strip terminating characters from the response.
        '''
        return super().query(cmd+'\n', timeout)


    def get_spectrum(self):
        trace = 0

        self.f = np.full(self._NUM_BINS, np.nan)
        self.V = np.full(self._NUM_BINS, np.nan)

        for nbin in range(self._NUM_BINS):
            f = self.query('BVAL? %i, %i' % (trace, nbin))
            V = self.query('SPEC? %i, %i' % (trace, nbin))

            self.f[nbin] = float(f)
            self.V[nbin] = float(V)

        return self.f, self.V
