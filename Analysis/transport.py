import numpy as np
from ..Utilities.constants import e, h

def mean_free_path(n=None, rho=None, mu=None):
    '''
    Calculate mean free path (in micron) of a 2D system, given at least two of:
    - carrier density, n, in cm^-2
    - longitudinal resistivity, rho, in Ohm/square
    - mobility, mu, in cm^2/V*s

    Lmfp = h/(2e^2*rho*sqrt(pi*n))

    '''
    if n is None:
        assert rho is not None
        assert mu is not None
        n = 1/(rho*e*mu) # in cm^-2
    elif rho is None:
        assert n is not None
        assert mu is not None
        rho = 1/(abs(n)*e*mu) # in Ohm/sq
    return h/(2*e**2*np.sqrt(np.pi*abs(n)*100**2)*rho)*1e6 # in um

def van_der_Pauw(Ra, Rb, Rguess=100):
    '''
    Calculate van der Pauw resistivity given the resistances of the two contact configurations.

    1     2
     \ _ /
      |_|
     /   \
    4     3
    Ra: V_{43}/I_{12}
    Rb: V_{23}/I_{14}
    Rguess: Best guess of the expected sheet resistance. Default 100 Ohm
    '''
    from scipy.optimize import fsolve
    f = lambda rho, ra, rb: np.exp(-np.pi*ra/rho) + np.exp(-np.pi*rb/rho) - 1
    return float(fsolve(f, Rguess, args=(Ra, Rb)))

def interpolate_2D_map(x, y, z, numpts=(1000,1000), plot=False, kind='linear'):
    '''
    Returns an interpolated 2D map from a coarse 2D map.

    x: X axis values for 2D map
    y: Y axis values for 2D map
    z: Z(X,Y) values for 2D map
    numpts: (tuple) number of points in (x,y) dimensions
    plot: (bool) Plot the result.
    kind: Kind of interpolation. See scipy.interpolate.interp2d.
    '''
    from scipy.interpolate import interp2d
    f = interp2d(x,y,z.T, kind=kind)

    X = np.linspace(x.min(), x.max(), numpts[0])
    Y = np.linspace(y.min(), y.max(), numpts[1])
    Z = f(X,Y)

    if plot:
        fig, ax = plt.subplots()
        ax.imshow(Z, origin = 'lower')

    return Z
