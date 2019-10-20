import numpy as np
import csv
from matplotlib import pyplot as plt
import os

def loadTrace(fname):
    with open(fname, newline=None) as f:
        reader = csv.reader(f)
        labels = next(reader) # read labels in csv
        units = next(reader) # load units and time spacing
        timeStep = float(units[4])
        time = []
        ch1 = []
        ch2 = []
        # load data row by row
        for row in reader:
            timeVal = float(row[0])
            ch1Val = float(row[1])
            ch2Val = float(row[2])

            time = np.append(time, timeVal)
            ch1 = np.append(ch1, ch1Val)
            ch2 = np.append(ch2, ch2Val)
        time = time * timeStep  # scale the time axis by the timeStep

    return time, ch1, ch2

def plotTrace(fname, dpi):
    time, ch1, ch2 = loadTrace(fname)
    # plot CH1
    fig, ax1 = plt.subplots(figsize=(8,4))
    ax1.plot(time, ch1, color='r')
    ylim = ax1.get_ylim()
    ax1.set_yticks(np.linspace(ylim[0], ylim[1], 5))
    ax1.set_ylabel('Voltage (V)', color='r')
    ax1.set_xlabel('Time (s)')
    for t1 in ax1.get_yticklabels():
        t1.set_color('r')
    # plot CH2 on the second y-axis
    ax2 = ax1.twinx()
    ax2.plot(time, ch2, color='b')
    ylim = ax2.get_ylim()
    ax2.set_yticks(np.linspace(ylim[0], ylim[1], 5))
    ax2.set_xlim(time[0], time[-1])
    ax2.set_ylabel('Voltage (V)', color='b')
    for t2 in ax2.get_yticklabels():
        t2.set_color('b')
    # generate the file path from the input file
    path = os.path.splitext(fname)[0] + '.png'
    plt.savefig(path, dpi=300)
    return path
