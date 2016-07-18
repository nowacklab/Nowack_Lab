import matplotlib.pyplot as plt
import numpy as np

def aspect(ax, ratio):
    '''
    Sets an absolute aspect ratio for the given axes using the axis limits.
    '''
    xvals,yvals = ax.get_xlim(), ax.get_ylim()

    xrange = xvals[1]-xvals[0]
    yrange = yvals[1]-yvals[0]
    ax.set_aspect(ratio*(xrange/yrange), adjustable='box')


def clim(im, l, u):
    '''
    Sets colorbar limits for the specified image and redraws it.
    '''
    cb = im.colorbar
    im.set_clim(l,u)
    cb.set_clim(l,u)
    cb.draw_all()


def plot2D(ax, x, y, z, cmap='RdBu', interpolation='none', title='', xlabel='', ylabel='', clabel='', fontsize=12):
    '''
    Plots a 2D heatmap on axes ax using plt.imshow.
    x and y can either be meshgrids or linear arrays.
    z must be 2D (obviously).
    Masks Nones and will plot as white.
    Can specify title and axis labels here as well ^.^
    Fontsize kwarg will affect title and all labels
    '''

    ## Format axes
    ax.set_title(title, fontsize=fontsize)
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
                zm,
                cmap=cmap,
                interpolation=interpolation,
                origin='lower',
                extent=[x.min(), x.max(), y.min(), y.max()]
            )

    ## Make a colorbar
    cb = plt.colorbar(im, ax=ax)
    cb.formatter.set_powerlimits((-2,2)) # only two decimal places!
    cb.set_label(clabel, fontsize=20)

    aspect(ax, 1) # equal aspect ratio

    return im


def update2D(im, z, center_at_zero=False):
    '''
    Update image data of a 2D plot.
    Pass in the image returned by plot2D.
    Can choose to center the colorbar at zero.
    '''
    ## Convert image to a masked numpy array
    z = np.array(z, dtype=np.float) # Will convert Nones to nans
    zm = np.ma.masked_where(np.isnan(z), z)

    ## Set the new image
    im.set_array(zm)

    ## Fix aspect ratio
    aspect(im.axes, 1) # equal aspect ratio

    ## Adjust colorbar limits accordingly
    if not center_at_zero:
        clim(im, zm.min(), zm.max())
    else:
        clim(im, -abs(zm).max(), abs(zm).max())
