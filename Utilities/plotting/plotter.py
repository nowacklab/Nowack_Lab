import matplotlib, numpy as np, matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable


class Plotter():
    '''
    Class containing methods useful for plotting data using matplotlib.
    Supports live plotting in jupyter notebook or from the console.
    '''
    fig = None

    def __init__(self):
        pass

    def add_colorbar(self, ax, label=None, **kwargs):
        '''
        Add a colorbar to a set of axes containing an imshow image.
        Creates a colorbar that matches the image height.
        This assumes only one image was plotted on a given set of axes.
        Additional kwargs are passed to the plt.colorbar function.
        '''
        d = make_axes_locatable(ax)
        cax = d.append_axes("right", size=0.1, pad=0.1)
        cbar = plt.colorbar(ax.images[0], cax=cax, **kwargs)
        cbar.set_label(label, rotation=270, labelpad=12)
        cbar.formatter.set_powerlimits((-2,2))
        return cbar


    def plot(self, **kwargs):
        '''
        Update all plots.
        '''
        if self.fig is None:
            self.setup_plots()
        self.plot_update()  # update plot data
        self.plot_draw()  # draw plots


    def plot_draw(self, autoscale=False):
        '''
        Redraw plots after plot data updated.
        '''
        figs = [a for a in self.__dict__.values()
                                    if type(a) is matplotlib.figure.Figure]
        for fig in figs:  # loop over all figures in the object
            # find all colorbars and update them
            for ax in fig.axes:
                for im in ax.images:
                    c = im.colorbar
                    if c is not None:
                        # Adjust colorbar limits for new data
                        data = im.get_array()
                        c.set_clim([np.nanmin(data), np.nanmax(data)])
                        c.draw_all()
            fig.canvas.draw()  # draw the figure

            # Flush events for a GUI backend; not needed for notebook or inline
            if not using_notebook_backend():
                fig.canvas.flush_events()


    def plot_update(self):
        '''
        Update plot data. Best practice here is perhaps to define in each class.
        '''
        pass


    def setup_plots(self):
        '''
        Set up all plots.
        '''
        self.fig, self.ax = plt.subplots() # example: just one figure


    def update_image(self, im, data):
        '''
        Update an image with new data. Masks NaN values.
        '''
        data_masked = np.ma.masked_where(np.isnan(data), data)
        im.set_data(data_masked)


def using_notebook_backend():
    inline = 'module://ipykernel.pylab.backend_inline'
    return matplotlib.get_backend() in ('nbAgg', inline)
