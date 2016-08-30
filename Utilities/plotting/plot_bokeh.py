import bokeh.io, numpy as np, os, datetime
import IPython.display as disp
from ..utilities import get_nb_kernel

NB_HANDLE = {}

def init_notebook():
    '''
    Tell Bokeh to plot things in the notebook.
    Not necessary if you use the show function defined here.
    '''
    bokeh.io.output_notebook(hide_banner=True)


def cmap(cmap_name):
    '''
    Converts a matplotlib colormap to bokeh palette
    '''
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    colormap = plt.cm.get_cmap(cmap_name)
    palette = [mpl.colors.rgb2hex(m) for m in colormap(np.arange(colormap.N))]
    return palette


def figure(title=None, xlabel=None, ylabel=None):
    '''
    Sets up a bokeh figure.
    '''
    ## Set up the figure
    import bokeh.plotting as bplt
    fig = bplt.figure(plot_width=400,
                plot_height=400,
                title=None,
                tools='pan,reset,save,box_zoom,wheel_zoom,resize'
                )

    ## Add data hover tool
    from bokeh.models import HoverTool
    hover = HoverTool(
        tooltips=[
            ('index', '$index'),
            ('x', '$x'),
            ('y', '$y'),
            ('name', '@name') # add this key in ColumnDataSource data dict
        ]
    )
    fig.add_tools(hover)

    ## Set up title and axis labels
    fig.xaxis.axis_label = xlabel
    fig.yaxis.axis_label = ylabel
    fig.title.text = title

    return fig


def plot_html(fig):
    '''
    Plots a bokeh figure.
    Will save plot as html in a subdirectory named bokeh_plots
    Will then show the plot in an iframe in the notebook.
    This is done so plots show up again when reopening a notebook.
    You may have to "File > Trust" the notebook to see plots
    '''

    ## Set up directory for the plot files
    plots_dir = os.path.join('.','Bokeh_plots')
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)
    filename = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')+'.html'
    figfile = os.path.join(plots_dir, filename)

    ## Save and show figure
    bokeh.io.output_file(figfile)
    bokeh.io.save(fig)
    show_html(figfile)

    fig.name = figfile


def show(fig):
    '''
    Show a bokeh plot using the normal show function.
    Uses the current kernel's ID as a dictionary key for NB_HANDLE.
    Should allow module to be used by two notebooks simultaneously.
    '''
    global NB_HANDLE
    NB_HANDLE[get_nb_kernel()] = bokeh.io.show(fig, notebook_handle=True)


def show_html(figfile, width=700, height=700):
    '''
    Shows a bokeh html figure in the notebook.
    This shouldn't be necessary after bokeh 0.12.2dev8
    '''
    disp.display(disp.HTML('<iframe src=%s width=%i height=%i></iframe>' %(figfile, width, height)))


def update():
    '''
    Replots a bokeh figure if it has been changed.
    '''
    bokeh.io.push_notebook(handle=NB_HANDLE[get_nb_kernel()])
