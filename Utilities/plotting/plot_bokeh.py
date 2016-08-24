import bokeh.io, numpy as np

def init_notebook():
    '''
    Tell Bokeh to plot things in the notebook.
    '''
    bokeh.io.output_notebook(hide_banner=True)
