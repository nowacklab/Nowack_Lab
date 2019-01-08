import numpy as np
from ..Utilities.constants import e, h, eps0
from scipy.stats import linregress

def carrier_density(Vg, rho, Vg_CNP=None, conversion=None,
    t_gate=None, eps_gate=None):
    '''
    For gatesweep data, center the charge neutrality point and calculate carrier
    density (cm^-2) in a few different ways. Relative kwargs listed in [].
    Set all other kwargs to None.
    (1) Provide a direct conversion factor [conversion].
    (2) Estimated from gate capacitance [t_gate, eps_gate]
    (3) (Not written yet): calculate from position and filling factor of
        Landau levels

    Arguments:
    Vg: Array of gate voltages
    resistivity: Array of resistivity (Ohm/sq) values corresponding to Vgs.
    Vg_CNP: The gate voltage equivalent to zero carrier density. If None,
        the maximum of resistivity will correspond to zero carrier density.
    conversion: Direct conversion from gate voltage to carrier density in units
        of cm^-2/V
    t_gate: Thickness of gate dielectric (nm).
    eps_gate: Dielectric constant of gate dielectric. 3.9 for SiO2.
        If you pass in t_gate with no eps_gate, will assume SiO2.

    Returns:
    n: Array of carrier densities (cm^-2)
    '''
    # Find the charge neutrality point
    if Vg_CNP is None:
        idx_CNP = np.where(rho==np.nanmax(rho))[0]
        Vg_CNP = Vg[idx_CNP]
    Vg2 = Vg - Vg_CNP

    # Direct conversion
    if conversion is not None:
        n = conversion*Vg2

    # Geometrical capacitance
    if t_gate is not None:
        if eps_gate is None:
            eps_gate = 3.9 # SiO2
        n = Vg2 * eps0 * eps_gate / (t_gate * 1e-9 * e) / 100 ** 2 # to cm^-2

    return n


def carrier_density_Hall(B, Rxy, Bmax=None):
    '''
    Calculate the carrier density (cm^-2) from the ordinary Hall effect.
    Rxy = B/ne. Slope of Rxy vs B: m = 1/ne. n = 1/me

    Arguments:
    B: array of magnetic field values
    Rxy: array of Hall resistance (Ohm) values corresponding to Bs
    Bmax: largest field to fit (usually this is the onset of the QHE). If None,
        will fit to all fields.

    Returns:
    n: carrier density (cm^-2)
    '''
    if Bmax is None:
        Bmax = np.nanmax(B) # nanmax probably not necessary

    where = np.where(B < Bmax) # cut off data if necessary
    m, b, r, p, err = linregress(B[where], Rxy[where])
    print('R-squared for fit: ', r**2)

    n = 1/(m*e)/100**2 # convert to cm^-2
    return n


def carrier_mobility(n, rho):
    '''
    Calculate carrier mobility (cm^2/(V*s)) from carrier density (cm^-2) and
    resistivity (Ohm/sq).

    sigma = n*e*mu -> mu = 1/(rho*n*e)

    Arguments:
    n: Array of carrier densities.
    rho: Array of resitivity values corresponding to n's.

    Returns:
    mobility: Array of carrier mobilities corresponding to n's.
    '''
    sigma = 1/rho
    mobility = abs(sigma / (n * e))
    return mobility


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
