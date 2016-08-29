import bokeh.io, numpy as np, os, datetime
from IPython.display import HTML, display

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


def plot(fig):
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
    show(figfile)

    fig.name = figfile


def show(figfile, width=700, height=700):
    '''
    Shows a bokeh html figure in the notebook
    '''
    display(HTML('<iframe src=%s width=%i height=%i></iframe>' %(figfile, width, height)))

def update(fig):
    '''
    Replots a bokeh figure if it has been changed.
    '''
    bokeh.io.output_file(fig.name)
    bokeh.io.save(fig)

    ## NEED TO FIGURE OUT HOW TO PLOT THIS IN IFRAME
