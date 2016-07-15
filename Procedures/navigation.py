from ..Utilities import dummy
from ..Instruments import piezos, attocube

class Goto():
    '''
    Will write this once we have a good sense of directions with attocubes and piezos.
    '''
    def __init__(self, instruments):
        if instruments is not None:
            self.piezos = instruments['piezos']
            self.atto = instruments['atto']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.atto = dummy.Dummy(attocube.Attocube)    
