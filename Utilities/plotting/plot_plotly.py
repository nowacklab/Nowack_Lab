import plotly.offline as pyo
import plotly.graph_objs as go
import plotly.tools as tls
pyo.init_notebook_mode(connected=True)

def plot2D_plotly(x, y, z, cmap='RdBu', title='', xlabel='', ylabel='', clabel='', fontsize=20):
    '''
    NOT YET COMPLETE... maybe never will be.
    
    Plots a 2D heatmap on axes ax using plt.imshow.
    x,y must be a meshgrid with 'ij' indexing. (list functionality to come?)
    z has to be the same shape.
    Masks Nones and will plot as white.
    Can specify title and axis labels here as well ^.^
    Fontsize kwarg will affect title and all labels
    '''

    heatmap = go.Heatmap(
        x=x,
        y=y,
        z=z,
        colorbar=dict(
            title=clabel,
            titlefont=dict(size=fontsize)
        ),
        colorscale=cmap
    )
    layout = dict(
        title=title,
        titlefont=fontsize,
        xaxis=dict(
            title=xlabel,
            titlefont=dict(size=fontsize)
        ),
        yaxis = dict(
            title=ylabel,
            titlefont=dict(size=fontsize)
        )
    )
    fig = go.Figure(data=heatmap, layout=layout)
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
                zm.T, # need to transpose the array if use 'ij' indexing in meshgrid!
                cmap=cmap,
                interpolation=interpolation,
                origin='lower',
                extent=[x.min(), x.max(), y.min(), y.max()]
            )

    ## Make a colorbar
    cb = plt.colorbar(im, ax=ax)
    cb.formatter.set_powerlimits((-2,2)) # only two decimal places!
    cb.set_label(clabel, fontsize=20)

    aspect(ax, 1, absolute=False) # equal aspect ratio based on data scales

    return im
