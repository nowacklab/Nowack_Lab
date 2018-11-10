import matplotlib.pyplot as plt
import numpy as np
import time
import math
from Nowack_Lab.Utilities.dataset import Dataset

def plot_live(filename, xkey, xlabel, funcs, updatetime = .1, depth = False):
    '''
    Each element of funcs must be a 3 element list, where the first element is
    a list of keys for arguments of the second element, a function which returns
    a single number. The third element shall be a string, to be put on the
    y-axis.
    '''
    plt.ion()
    fig, axs = plt.subplots(len(funcs),1, sharex = True,figsize = (8,8))
    lines = [ax.plot([])[0] for ax in axs]
    data = Dataset(filename)
    texts = []
    for i in range(len(funcs)):
        ylabel = funcs[i][2]
        axs[i].set_ylabel(ylabel)
        texts.append(axs[i].text(0,0,''))
    axs[-1].set_xlabel(xlabel)
    activebeg = 0
    activeend = -1
    allfunceddata = [np.array([]) for i in range(len(funcs))]
    allxdata = np.array([])
    while True:
        time.sleep(updatetime)
        xdata = data.get(xkey,slice(activebeg,activeend))
        xnanpos = next(i for i in range(len(xdata)) if np.isnan(xdata[i]))
        xdata = xdata[0:xnanpos]
        allxdata = np.concatenate((allxdata, xdata))
        for i in range(len(funcs)):
            func = funcs[i][1]
            ykeys = funcs[i][0]
            ydata = [data.get(ykey,slice(activebeg,activeend)) for ykey in ykeys]
            ydata = [onedata[0:xnanpos] for onedata in ydata]
            funceddata = [func(y) for y in np.transpose(ydata)]
            allfunceddata[i] = np.concatenate((allfunceddata[i], funceddata))
            if depth:
                xdataplt = allxdata[-depth:]
                funceddataplt = (allfunceddata[i])[-depth:]
            else:
                xdataplt = allxdata
                funceddataplt = allfunceddata[i]
            upperlim = np.max(funceddataplt)
            lowerlim = np.min(funceddataplt)
            xlowerlim= np.min(xdataplt)
            xupperlim= np.max(xdataplt)
            axs[i].set_xlim(left= xlowerlim, right = xupperlim)
            axs[i].set_ylim(bottom = lowerlim - .1*(upperlim-lowerlim), top = upperlim + .2*(upperlim-lowerlim))
            lines[i].set_data(xdataplt, funceddataplt)
            texts[i].set_position((xlowerlim +.05*(xupperlim-xlowerlim),upperlim + .01*(upperlim-lowerlim)))
            texts[i].set_text('%s : %.2E' %(funcs[i][2], funceddataplt[-1]))
        activebeg += xnanpos
        activeend += math.floor(2.5*xnanpos) #makes it so it grabs 150% of what was required to get everything this time
        fig.canvas.draw()
