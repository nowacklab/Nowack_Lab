import matplotlib.animation as animation
from .plotting.plot_mpl import clim
from . import conversions

def scan_gif(scan_list):
    """
    Make a gif from a series of scans.
    Colorscale will use the lowest lower bound and the highest upper bound.
    This will (hopefully) ensure that we can see features on all scans.
    scan_list = A list of files to load
    """
    from ..Procedures.scanplane import Scanplane

    scans = []
    signals = ['V', 'Vac_x', 'Vac_y', 'C']
    lowers = {v:999999 for v in signals}
    uppers = {v:-999999 for v in signals}

    for scan in scan_list:
        scans.append(Scanplane.load(scan))
        for v in signals:
            lowers[v] = min(lowers[v], getattr(scans[-1],v).min())
            uppers[v] = max(uppers[v], getattr(scans[-1],v).max())
    for v in signals:
        if v == 'C': continue
        lowers[v] *= conversions.Vsquid_to_phi0
        uppers[v] *= conversions.Vsquid_to_phi0

    scan = Scanplane()
    scan.setup_plots()
    def frame(num):
        for v in signals:
            setattr(scan, v, getattr(scans[num], v))
        scan.plot()
        clim(scan.im_dc, lowers['V'], uppers['V'])
        clim(scan.im_ac_x, lowers['Vac_x'], uppers['Vac_x'])
        clim(scan.im_ac_y, lowers['Vac_y'], uppers['Vac_y'])
        clim(scan.im_cap, lowers['C'], uppers['C'])

    ani = animation.FuncAnimation(scan.fig, frame, len(scans),
                                   interval=200, blit=True, repeat=False)
    return ani


if __name__=='__main__':
    import glob, os

    full_list = glob.glob('/Volumes/HDD/Dropbox (Nowack lab)/TeamData/Montana/cooldowns/2016-10-07_LSCO_planes/2016-10-1*/*scan.json')
    full_list[40:]
    ani = scan_gif(full_list[40:])
    ani.save('anim.mp4')
