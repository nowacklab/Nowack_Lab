from Nowack_Lab.datasaver import Saver

class plotscanplane():

    def __init__(self, filename):
        self.filename  = filename
        self.Saver = (filename, addtimestamp=False)
        contents = self.Saver.get('/')
        self.plottabledata = {}
        self.config = {}
        self.extent = list(self.saver.get('config/xrange'))+
                                        list(self.saver.get('config/yrange')])
        for key in contents.keys():
            if key == 'config':
                pass
            elif type(contents[key]) == np.ndarray:
                self.plottabledata[key] = contents[key]
            else:
                print('Data stored under key %s is not plottable' % key)

    def plot(self, whattoplot):
        '''
        Plot the data
        '''
        # Use the aspect ratio of the image set subplot size.
        # The aspect ratio is Xspan/Yspan
        if whattoplot = 'all':
            whattoplot = self.plottabledata.keys()
        elif isinstance(whattoplot, str):
            whattoplot = [whattoplot]
        fig1data = self.plottabledata[whattoplot[0]]
        aspect = fig1data.shape[0] / fig1data.shape[1]
        numplots = len(whattoplot)
        # If X is longer than Y we want 2 columns of wide plots
        if aspect > 1:
            num_row = int(np.ceil(numplots / 2))
            num_col = 2
            width = 14
            # Add 1 to height for title/axis labels
            height = min(width, width / aspect) + 1
        # If Y is longer than X we want 2 rows of tall plots
        else:
            num_row = 2
            num_col = int(np.ceil(numplots / 2))
            height = 10
            # Pad the plots for the colorbars/axis labels
            width = min(height, height * aspect) + 4

        self.fig, self.axes = plt.subplots(num_row,
                                           num_col,
                                           figsize=(width, height))
        self.axes = self.axes.flatten()
        # Plot the DC signal, capactitance and AC signal on 2D colorplots
        for i in range(len(whattoplot):
            dataname = whattoplot[i]
            ax =  self.axes[i]

            image = ax.imshow(plottabledata, cmap='magma', origin="lower",
                              extent=self.extent)

            # Create a colorbar that matches the image height
            d = make_axes_locatable(ax)
            cax = d.append_axes("right", size=0.1, pad=0.1)
            cbar = plt.colorbar(image, cax=cax)
            cbar.set_label(dataname, rotation=270, labelpad=12)
            cbar.formatter.set_powerlimits((-2, 2))
            self.im[chan] = image
            self.cbars[chan] = cbar

            # Label the axes - including a timestamp
            ax.set_xlabel("X Position (V)")
            ax.set_ylabel("Y Position (V)")
            title = ax.set_title(self.filename, size="medium", y=1.02)
            # If the title intersects the exponent label from the colorbar
            # shift the title up and center it

        self.fig.tight_layout()


        self.fig.canvas.draw()
