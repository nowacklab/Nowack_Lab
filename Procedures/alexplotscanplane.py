import h5py
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import numpy as np
import sys
f = h5py.File(sys.argv[1],'r')
toplot = sys.argv[2:]
fpath = ''.join((sys.argv[1].split('.'))[:-1]) + '_'
ext = np.concatenate((f['/config/xrange'],f['/config/yrange'])))
ims = []
datalocs = []
figs = []
for i in range(len(toplot)):
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        data = f[toplot[i]]
        im = ax.imshow(data, cmap = 'magma', extent = np.concatenate(
                         (f['/config/xrange'],f['/config/yrange'])))
        figs.append(fig)
        ims.append(im)
        datalocs.append(toplot[i])
        #ax.tick_params(right= False,top= False,left= False, bottom= False)
        #ax.tick_params(labelright= False,labeltop= False,labelleft= False, labelbottom= False)
        ax.set_title(toplot[i])
        fig.colorbar(im)
        fig.canvas.set_window_title(toplot[i])

while True:
    for i in range(len(ims)):
        data = f[toplot[i]]
        ims[i].set_data(data)
        figs[i].canvas.draw()
        min = np.nanmin(np.array(data))
        max = np.nanmax(np.array(data))
        ims[i].set_clim(vmin = min, vmax = max)
    if not np.isnan(data).any():
        for i in range(len(toplot)):
            fig = figs[i]
            addendum =  toplot[i].replace('/', '_')
            fig.savefig(fpath + addendum +'.pdf')
        break
    plt.pause(1)
