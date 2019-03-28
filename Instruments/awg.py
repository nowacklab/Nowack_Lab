from .instrument import VISAInstrument

class Agilent33521A(VISAInstrument):
    '''
    Agilent 33521A Arbitrary Waveform Generator
    '''
    _label = 'Agilent 33521A'
    _idn = '33521A'

    def __init__(self, usb='USB0::0x0957::0x1607::MY50003805::INSTR'):
        self._init_visa(usb)

    def __getstate__(self):
        if self._loaded:
            return super().__getstate__() # Do not attempt to read new values
        self._save_dict = {'_f': self.f,
                          '_V': self.V,
                          }
        return self._save_dict

    @property
    def f(self):
        self._f = float(self.query('SOURCE1:FREQUENCY?'))
        return self._f

    @f.setter
    def f(self, value):
        self._f = value
        self.write('SOURCE1:FREQUENCY %s' %value)

    @property
    def output(self):
        self._output = bool(int(self.query('OUTP1?')))
        return self._output

    @output.setter
    def output(self, value):
        assert type(value) is bool
        self._output = value
        if value:
            self.write('OUTP1 ON')
        else:
            self.write('OUTP1 OFF')

    @property
    def V(self):
        self._V = float(self.query('SOURCE1:VOLT?'))
        return self._V

    @V.setter
    def V(self, value):
        self._V = value
        self.write('SOURCE1:VOLT %s' %value)
