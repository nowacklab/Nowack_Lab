from ..Utilities import dummy
from ..Instruments import piezos, attocube

def move(instruments, plane, x, y):
    """
    Moves attocubes relatively safely. First sweeps the z piezo down,
    then moves the attocubes and updates the plane with a single touchdown.
    """
    instruments['piezos'].z.V = -400
    instruments['attocube'].x.move(x)
    instruments['attocube'].y.move(y)
    plane.update_c()
