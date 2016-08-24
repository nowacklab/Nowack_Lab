from ..Utilities import dummy
from ..Instruments import piezos, attocube
from ..Procedures import planefit

class Navigator():
    '''
    Will write this once we have a good sense of directions with attocubes and piezos.
    '''
    def __init__(self, instruments=None, plane=None):
        '''
        Pass in instruments dictionary with at least piezos, attocube, and montana
        '''
        self.instruments = instruments
        if instruments is not None:
            self.piezos = instruments['piezos']
            self.atto = instruments['attocube']
            self.montana = instruments['montana']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.atto = dummy.Dummy(attocube.Attocube)
            self.montana = dummy.Dummy(montana.Montana)

        if plane = None:
            inp = input('We need a plane to be able to navigate. All set to take one now? (Enter to continue, q to quit)')
            if inp =='q':
                raise Exception('Terminated by user.')

            self.plane = planefit.Planefit(self.instruments)
            self.plane.do()
