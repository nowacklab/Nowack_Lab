import numpy as np
from ..Utilities.constants import e, h

def mean_free_path(n=None, rho=None, mu=None):
    """
    Calculate mean free path (in micron) of a 2D system, given at least two of:
    - carrier density, n, in cm^-2
    - longitudinal resistivity, rho, in Ohm/square
    - mobility, mu, in cm^2/V*s

    Lmfp = h/(2e^2*rho*sqrt(pi*n))

    """
    if n is None:
        assert rho is not None
        assert mu is not None
        n = 1/(rho*e*mu) # in cm^-2
    elif rho is None:
        assert n is not None
        assert mu is not None
        rho = 1/(abs(n)*e*mu) # in Ohm/sq
    return h/(2*e**2*np.sqrt(np.pi*abs(n)*100**2)*rho)*1e6 # in um
