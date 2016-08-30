__all__ = ['Procedures', 'Instruments', 'Utilities']


from matplotlib import rcParams
rcParams.update({'figure.autolayout': True}) # will avoid axis labels getting cut off

from .Utilities.plotting.plot_bokeh import init_notebook
init_notebook()
