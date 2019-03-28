import matplotlib as mpl, matplotlib.pyplot as plt, numpy as np
from matplotlib.transforms import Bbox
from matplotlib.colors import LinearSegmentedColormap

## NOTE: Aspect handled differently in matplotlib 2.0. Don't need to set it this way!
def aspect(ax, ratio, absolute=True):
    '''
    Sets an absolute (or relative) aspect ratio for the given axes using the axis limits.
    Absolute will make the box aspect ratio equal to the one given, regardless of axis limits.
    Relative will set the aspect ratio based on the data scales.
    '''
    xvals,yvals = ax.get_xlim(), ax.get_ylim()

    xrange = xvals[1]-xvals[0]
    yrange = yvals[1]-yvals[0]

    if absolute:
        ax.set_aspect(ratio*(xrange/yrange), adjustable='box')
    else:
        ax.set_aspect(ratio, adjustable='box')


def clim(im, l, u):
    '''
    Sets colorbar limits for the specified image and redraws it.
    '''
    cb = im.colorbar
    im.set_clim(l,u)
    cb.set_clim(l,u)
    cb.draw_all()
    im.figure.canvas.draw()


def cubehelix(g=1.0, s=0.5, r=-1.0, h=1.5):
    '''
    Returns a "cubehelix", brightness-adjusted colormap.
    Help from https://gist.github.com/gazzar/11369614.
    See examples here http://www.mrao.cam.ac.uk/~dag/CUBEHELIX/cubewedges.html

    g: gamma
    s: start color
    r: number of rgb rotations in color made from start to end
    h: hue (adjust saturation)
    '''
    cdict = mpl._cm.cubehelix(g, s, r, h)
    cm = LinearSegmentedColormap('cubehelix_custom', cdict)
    return cm


def extents(x, y):
    '''
    Returns an extent kwarg for imshow. The extents are set such that the pixels
    on the border of the image are in line with the maxima and minima of the x,y
    data. Assumes step size is constant throughout entire array.

    Arguments
    x, y: 1D or 2D X and Y arrays mapping to imshow matrix.
    '''
    diffsx = np.diff(x, axis=0).flatten() # 2D to 1D
    if np.all(diffsx) == 0: # we chose the wrong axis
        diffsx = np.diff(x, axis=1).flatten()
    diffsy = np.diff(y, axis=0).flatten() # 2D to 1D
    if np.all(diffsy) == 0: # we chose the wrong axis
        diffsy = np.diff(y, axis=1).flatten()

    # Try both first and last differences.
    # This is to account for potential sweeps done in reverse.
    dx = diffsx[0]
    if np.isnan(dx):
        dx = diffsx[-1]
    dy = diffsy[0]
    if np.isnan(dy):
        dy = diffsy[-1]

    return [x.min() - np.abs(dx) / 2,
            x.max() + np.abs(dx) / 2,
            y.min() - np.abs(dy) / 2,
            y.max() + np.abs(dy) / 2
            ]

def no_scientific_notation(ax, which='both', minor=False):
    '''
    Formats ticks using FormatStrFormatter to remove scientific notation for
    small exponents
    ax: axis to format
    which: 'x', 'y', or 'both'
    '''
    x = False
    y = False
    if which in ('x', 'both'):
        x = True
    if which in ('y', 'both'):
        y = True
    if x:
        ax.xaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('%g'))
        if minor:
            ax.xaxis.set_minor_formatter(mpl.ticker.FormatStrFormatter('%g'))
    if y:
        ax.yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('%g'))
        if minor:
            ax.yaxis.set_minor_formatter(mpl.ticker.FormatStrFormatter('%g'))

def plotline(ax, x, y, z):
    pass

## NOTE: Still works with MPL 2.0, but plotting is under construction in scanplane.
## We may want to rename this as "our" imshow
## For moving forward, this function should take care of all the non-obvious stuff (e.g. don't need set_xlabel)
def plot2D(ax, x, y, z, cmap='RdBu', interpolation='none', title='', xlabel='',
           ylabel='', clabel='', fontsize=20, equal_aspect=True, cbar=True):
    '''
    Plots a 2D heatmap on axes ax using plt.imshow.
    x,y must be a meshgrid with default indexing, or lists.
    z has to be the same shape.
    Masks Nones and will plot as white.
    Can specify title and axis labels here as well
    Fontsize kwarg will affect title and all labels
    cbar (bool): include colorbar
    '''

    # Format axes
    # NOTE: REMOVE
    ax.set_title(title, fontsize=12)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)

    # If lists, convert to arrays
    # NOTE: POSSIBLY REMOVE?
    if type(x) == list:
        x = np.array(x)
    if type(y) == list:
        y = np.array(y)

    # Convert image to a masked numpy array
    # NOTE: KEEP
    z = np.array(z, dtype=np.float) # Will convert Nones to nans
    zm = np.ma.masked_where(np.isnan(z), z)

    # Create the image
    # NOTE: KEEP, but allow for arbitrary kwargs, include cmap and interpolation here
    im = ax.imshow(
                zm, # not transpose for xy indexing!!
                cmap=cmap,
                interpolation=interpolation,
                origin='lower', ## NOTE: KEEP
                extent=extents(x,y) ## NOTE: KEEP
            )

    # Make a colorbar
    # NOTE: KEEP, but maybe just put it in another function?
    if cbar:
        cb = plt.colorbar(im, ax=ax)
        cb.formatter.set_powerlimits((-2,2)) # only two decimal places!
        cb.set_label(clabel, fontsize=12)

    # NOTE: REMOVE
    if equal_aspect:
        aspect(ax, 1, absolute=False) # equal aspect ratio based on data scales

    return im

def save_subplot(fig, ax, *args, **kwargs):
    '''
    Save a subplot on axis ax.
    args and kwargs are passed directly to fig.savefig
    '''

    def full_extent(ax, pad=0.0):
        '''
        Get the full extent of an axes, including axes labels, tick labels, and
        titles.
        '''
        items = ax.get_xticklabels() + ax.get_yticklabels()
        items += [ax.get_xaxis().get_label(), ax.get_yaxis().get_label()]
        items += [ax, ax.title]

        bbox = Bbox.union([item.get_window_extent() for item in items])

        return bbox.expanded(1.0 + pad, 1.0 + pad)

    extent = full_extent(ax).transformed(fig.dpi_scale_trans.inverted())

    kwargs['bbox_inches'] = extent
    fig.savefig(*args, **kwargs)


def set_size(w, h, fig=None, ax=None, mm=False):
    '''
    Resize a set of axes to (w,h) given in inches
    mm: if True, (w,h) in mm
    '''
    if mm:
        w /= 25.4
        h /= 25.4
    if not fig: fig = plt.gcf()
    if not ax: ax = plt.gca()
    for i in range(3): # Gives the best results
        fig.tight_layout()
        l = ax.figure.subplotpars.left
        r = ax.figure.subplotpars.right
        t = ax.figure.subplotpars.top
        b = ax.figure.subplotpars.bottom
        figw = float(w)/(r-l)
        figh = float(h)/(t-b)
        ax.figure.set_size_inches(figw, figh)

def set_size_axes_divider(w, h, d, fig, ax, mm=False):
    '''
    Resize a set of axes to (w,h) given in inches.
    Pass in an axis divider object created when making a colorbar.
    '''
    if mm:
        w /= 25.4
        h /= 25.4
    for i in range(3): # Gives the best results
        fig.tight_layout()
        l, b, r, t = d.get_position()
        figw = float(w)/(r-l)
        figh = float(h)/(t-b)
        ax.figure.set_size_inches(figw, figh)

def update2D(im, z, center_at_zero=False, equal_aspect=True):
    '''
    Update image data of a 2D plot.
    Pass in the image returned by plot2D.
    Can choose to center the colorbar at zero.
    '''
    ## Convert image to a masked numpy array
    z = np.array(z, dtype=np.float) # Will convert Nones to nans
    zm = np.ma.masked_where(np.isnan(z), z)

    ## Set the new image
    im.set_array(zm) # no transpose if xy indexing!!

    ## Fix aspect ratio
    if equal_aspect:
        aspect(im.axes, 1, absolute=False) # equal aspect ratio

    ## Adjust colorbar limits accordingly
    ## NOTE: Instead of center_at_zero, check if colormap is diverging. Suggested first line replacement below.
    # if not cmap_is_diverging(im.cmap):
    if not center_at_zero:
        clim(im, zm.min(), zm.max())
    else:
        clim(im, -abs(zm).max(), abs(zm).max())
