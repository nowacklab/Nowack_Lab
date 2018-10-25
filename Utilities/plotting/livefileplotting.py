import matplotlib.pyplot as plt
import numpy as np
import time
from Nowack_Lab.Utilities.dataset import Dataset

def plot_live(filename, xkey, ykeys, func, updatetime = .1, depth = False):
    '''

    '''
    fig, ax = plt.subplots()
    l, = ax.plot([])
    data = Dataset(filename)

    while True:
        time.sleep(updatetime)
        if depth:
            xdata = data.get(xkey, slice(-depth, -1))
            ydata = [data.get(ykey, slice(-depth, -1)) for ykey in ykeys]
        else:
            xdata = data.get(xkey)
            ydata = [data.get(ykey) for ykey in ykeys]
        ax.set_ylim(bottom = np.min(func(ydata)), top = np.max(func(ydata)))
        ax.set_xlim(left= np.min(xdata), right = np.max(xdata))
        l.set_data(xdata, func(ydata))
        fig.canvas.draw()
