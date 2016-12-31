import matplotlib.pyplot as plt
import numpy as np
import math

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


def plotline(ax, x, y, z):
    pass


def plot2D(ax, x, y, z, cmap='RdBu', interpolation='none', title='', xlabel='', ylabel='', clabel='', fontsize=20, equal_aspect=True):
    '''
    Plots a 2D heatmap on axes ax using plt.imshow.
    x,y must be a meshgrid with 'ij' indexing. (list functionality to come?)
    z has to be the same shape.
    Masks Nones and will plot as white.
    Can specify title and axis labels here as well ^.^
    Fontsize kwarg will affect title and all labels
    '''

    ## Format axes
    ax.set_title(title, fontsize=12)
    ax.set_xlabel(xlabel, fontsize=fontsize)
    ax.set_ylabel(ylabel, fontsize=fontsize)

    ## If lists, convert to arrays
    if type(x) == list:
        x = np.array(x)
    if type(y) == list:
        y = np.array(y)

    ## Convert image to a masked numpy array
    z = np.array(z, dtype=np.float) # Will convert Nones to nans
    zm = np.ma.masked_where(np.isnan(z), z)

    ## Create the image
    im = ax.imshow(
                zm, # not transpose for xy indexing!!
                cmap=cmap,
                interpolation=interpolation,
                origin='lower',
                extent=[x.min(), x.max(), y.min(), y.max()]
            )

    ## Make a colorbar
    cb = plt.colorbar(im, ax=ax)
    cb.formatter.set_powerlimits((-2,2)) # only two decimal places!
    cb.set_label(clabel, fontsize=12)

    if equal_aspect:
        aspect(ax, 1, absolute=False) # equal aspect ratio based on data scales

    ## Round ticks to the nearest integer, and only have three ticks per axis
    #try:
    #    xticks = [math.ceil(x.min()), int((x.min()+x.max())/2), math.floor(x.max())]
    #    yticks = [math.ceil(y.min()), int((y.min()+y.max())/2), math.floor(y.max())]

    #    ax.set_xticks(xticks)
    #    ax.set_yticks(yticks)
    #except:
    #    pass # if x and y are nans, this will fail!

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
    if not center_at_zero:
        clim(im, zm.min(), zm.max())
    else:
        clim(im, -abs(zm).max(), abs(zm).max())
