import matplotlib, matplotlib.pyplot as plt, numpy as np

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
    import matplotlib as mpl
    from matplotlib.colors import LinearSegmentedColormap
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


def plotline(ax, x, y, z):
    pass

## NOTE: Still works with MPL 2.0, but plotting is under construction in scanplane.
## We may want to rename this as "our" imshow
## For moving forward, this function should take care of all the non-obvious stuff (e.g. don't need set_xlabel)
def plot2D(ax, x, y, z, cmap='RdBu', interpolation='none', title='', xlabel='',
           ylabel='', clabel='', fontsize=20, equal_aspect=True):
    '''
    Plots a 2D heatmap on axes ax using plt.imshow.
    x,y must be a meshgrid with default indexing, or lists.
    z has to be the same shape.
    Masks Nones and will plot as white.
    Can specify title and axis labels here as well
    Fontsize kwarg will affect title and all labels
    '''

    ## Format axes
    ## NOTE: REMOVE
    ax.set_title(title, fontsize=12)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)

    ## If lists, convert to arrays
    ## NOTE: POSSIBLY REMOVE?
    if type(x) == list:
        x = np.array(x)
    if type(y) == list:
        y = np.array(y)

    ## Convert image to a masked numpy array
    ## NOTE: KEEP
    z = np.array(z, dtype=np.float) # Will convert Nones to nans
    zm = np.ma.masked_where(np.isnan(z), z)

    ## Create the image
    ## NOTE: KEEP, but allow for arbitrary kwargs, include cmap and interpolation here
    im = ax.imshow(
                zm, # not transpose for xy indexing!!
                cmap=cmap,
                interpolation=interpolation,
                origin='lower', ## NOTE: KEEP
                extent=extents(x,y) ## NOTE: KEEP
            )

    ## Make a colorbar
    ## NOTE: KEEP, but maybe just put it in another function?
    cb = plt.colorbar(im, ax=ax)
    cb.formatter.set_powerlimits((-2,2)) # only two decimal places!
    cb.set_label(clabel, fontsize=12)

    ## NOTE: REMOVE
    if equal_aspect:
        aspect(ax, 1, absolute=False) # equal aspect ratio based on data scales

    return im

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

def using_notebook_backend():
    inline = 'module://ipykernel.pylab.backend_inline'
    return matplotlib.get_backend() in ('nbAgg', inline)
