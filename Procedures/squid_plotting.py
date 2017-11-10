from matplotlib import pyplot as plt
import h5py
import numpy as np
import json
import os
from datetime import datetime, timedelta
import re
import fnmatch
from . import dtools as dt

def makePlots(squidNum, date, file, iv = 0, mod = 0, field = [0,0,0], ivSlope = True):
    if(iv!=0):
        makeIVPlot(iv, squidNum, date, file, ivSlope)
    if(mod!=0):
        makeModPlot(mod, squidNum, date, file)
    if(field != [0,0,0]):
        makeAllFieldPlot(field[0], field[1], field[2], squidNum, file)


def makeIVPlot(timestamp , squidNum, date, file, ivSlope = True):
    os.chdir("\\\\SAMBASHARE\\labshare\\data\\Cactus-PC\\experiments\\"
             + date + "" + file + "\\" + date)
    m = dt.loadMeasurement(date+'_' + timestamp +'_SquidIV.h5')
    fig, ax = plt.subplots(figsize=(4,4))
    ax.plot(m.data.I, m.data.V)
    plt.ylabel('Voltage (mV)')
    plt.xlabel('Current ($\mu$A)')
    ticks = ax.get_xticks()*10**6
    ax.set_xticklabels(ticks)
    ticks = ax.get_yticks()*10**3
    ax.set_yticklabels(ticks)

    if(ivSlope):
        num_pnt = len(m.data.I)

        line1 = np.polyfit(m.data.I[0:int(num_pnt*.25)],
         m.data.V[0:int(num_pnt*.25)], 1)
        f1 = np.poly1d(line1)
        x_new1 = np.linspace(m.data.I[0], m.data.I[int(num_pnt*.25)], 50)
        y_new1 = f1(x_new1)
        ax.plot(x_new1,y_new1)
        slope1 = line1[0]

        line2 = np.polyfit(m.data.I[int(num_pnt*.45):int(num_pnt*.55)],
            m.data.V[int(num_pnt*.45):int(num_pnt*.55)], 1)
        f2 = np.poly1d(line2)
        x_new2 = np.linspace(m.data.I[int(num_pnt*.45)],
            m.data.I[int(num_pnt*.55)], 50)
        y_new2 = f2(x_new2)
        ax.plot(x_new2,y_new2)
        slope2 = line2[0]

        line3 = np.polyfit(m.data.I[int(num_pnt*.75):num_pnt],
            m.data.V[int(num_pnt*.75):num_pnt], 1)
        f3 = np.poly1d(line3)
        x_new3 = np.linspace(m.data.I[int(num_pnt*.75)],
            m.data.I[num_pnt-1], 50)
        y_new3 = f3(x_new3)
        ax.plot(x_new3,y_new3)
        slope3 = line3[0]

        plt.annotate("%.3f" % slope1 + "Ohm", xy=(m.data.I[0] + .00001* num_pnt/400,
         m.data.V[0]),xytext= (m.data.I[0] + .00001* num_pnt/400, m.data.V[0]))

        plt.annotate("%.3f" % slope2 + "Ohm", xy=(m.data.I[int(num_pnt/2)] - .00003*
         num_pnt/400, m.data.V[int(num_pnt/2)] + .00007* num_pnt/400),
         xytext=(m.data.I[int(num_pnt/2)] - .00003* num_pnt/400,
         m.data.V[int(num_pnt/2)] + .00007* num_pnt/400))

        plt.annotate("%.3f" % slope3 + "Ohm",
            xy=(m.data.I[-1] - .00006* num_pnt/400, m.data.V[-1]),
            xytext= (m.data.I[-1] - .00006* num_pnt/400, m.data.V[-1]))

    plt.title("Time Stamp: " +timestamp + "\n" + "SQUID #" + squidNum +"\n" +
        date)
    plt.savefig("C:\\Users\\c2\\Desktop\\Python\\squid_test_graphs\\" +
        timestamp +"_Squid" + squidNum, dpi=500, bbox_inches = "tight")


def makeModPlot(timestamp , squidNum, date, file):
    os.chdir("\\\\SAMBASHARE\\labshare\\data\\Cactus-PC\\experiments\\" + date
        + "" + file + "\\" + date)
    m = dt.loadMeasurement(date+'_' + timestamp +'_Mod2D.h5')
    fig, ax = plt.subplots(figsize=(5,4))
    Isquid = np.arange(-.000060, .00005999999999, 5e-7)
    X,Y = np.meshgrid(Isquid, m.data.Imod)
    v = m.data.V * 10e-6
    im=ax.pcolor(X, Y, v, cmap="RdBu")
    plt.ylabel('Mod Coil Current (mA)')
    plt.xlabel('Bias Current ($\mu$A)')
    plt.title(date + ": " +timestamp + "\n" + "SQUID #" + squidNum)
    ticks = ax.get_xticks()*10**6
    ax.set_xticklabels(ticks)
    ticks = ax.get_yticks()*10**3
    ax.set_yticklabels(ticks)
    cbar = fig.colorbar(im)
    cbar.set_label("SQUID voltage ($\mu$V)")
    plt.savefig("C:\\Users\\c2\\Desktop\\Python\\squid_test_graphs\\" +
        timestamp + "_Squid" + squidNum, dpi=500, bbox_inches = "tight")

def makeFieldPlot(timestamp , squidNum, date, file, loop):
    os.chdir("\\\\SAMBASHARE\\labshare\\data\\Cactus-PC\\experiments\\" + date
        + "" + file + "\\" + date)
    m = dt.loadMeasurement(date+'_' + timestamp +'_ArraylessMI.h5')
    fig, ax = plt.subplots(figsize=(5,4))
    Imod = np.arange(-m.config.I_mod_f, m.config.I_mod_f - .000000000001, m.config.I_mod_f*2/m.config.num_mod)
    X,Y = np.meshgrid(m.data.field_current, Imod)
    v = m.data.V *10**6
    im=ax.pcolor(X, Y, v, cmap="magma")
    plt.ylabel('Mod Coil Current ($\mu$A)')
    plt.xlabel('Field coil current (mA)')
    plt.title("Time Stamp: " +timestamp + "\n" + "SQUID #" + squidNum +
        "\n"+ loop+ "\n"+ date)
    ticks = ax.get_xticks()*10**3
    ax.set_xticklabels(ticks)
    ticks = ax.get_yticks()*10**6
    ax.set_yticklabels(ticks)
    cbar = fig.colorbar(im)
    cbar.set_label("SQUID voltage ($\mu$V)")
    plt.savefig("C:\\Users\\c2\\Desktop\\Python\\squid_test_graphs\\" +
    timestamp + "_Squid" + squidNum, dpi=500, bbox_inches = "tight")
    plt.show()

def makeAllFieldPlot(timestamp1 ,timestamp2,timestamp3, squidNum, date, file):
    if(timestamp1!=0):
        makeFieldPlot(timestamp1 , squidNum, date, file, 'Entire Loop')

    if(timestamp2!=0):
        makeFieldPlot(timestamp2 , squidNum, date, file, 'Non-Pickup Loop')

    if(timestamp3!=0):
        makeFieldPlot(timestamp3 , squidNum, date, file, 'Pickup Loop')







def makePlots(squidNum, path, ivsmooth = 0, iv = 0, mod = 0, field = [0,0,0]):
    if(iv!=0):
        makeIVPlot(iv, squidNum, path, True)
    if(ivsmooth!=0):
        makeIVPlot(ivsmooth, squidNum, path, False)
    if(mod!=0):
        makeModPlot(mod, squidNum, path)
    if(field != [0,0,0]):
        makeAllFieldPlot(field[0], field[1], field[2], squidNum, date, file)



def makeIVPlot(timestamp , squidNum, path, ivSlope = True):
    m = dt.loadMeasurement(path + "//" + timestamp+".h5")
    fig, ax = plt.subplots(figsize=(4,4))
    ax.plot(m.data.I, m.data.V)
    plt.ylabel('Voltage (mV)')
    plt.xlabel('Current ($\mu$A)')
    ticks = ax.get_xticks()*10**6
    ax.set_xticklabels(ticks)
    ticks = ax.get_yticks()*10**3
    ax.set_yticklabels(ticks)

    if(ivSlope):
        num_pnt = len(m.data.I)

        line1 = np.polyfit(m.data.I[0:int(num_pnt*.25)],
         m.data.V[0:int(num_pnt*.25)], 1)
        f1 = np.poly1d(line1)
        x_new1 = np.linspace(m.data.I[0], m.data.I[int(num_pnt*.25)], 50)
        y_new1 = f1(x_new1)
        ax.plot(x_new1,y_new1)
        slope1 = line1[0]

        line2 = np.polyfit(m.data.I[int(num_pnt*.45):int(num_pnt*.55)],
            m.data.V[int(num_pnt*.45):int(num_pnt*.55)], 1)
        f2 = np.poly1d(line2)
        x_new2 = np.linspace(m.data.I[int(num_pnt*.45)],
            m.data.I[int(num_pnt*.55)], 50)
        y_new2 = f2(x_new2)
        ax.plot(x_new2,y_new2)
        slope2 = line2[0]

        line3 = np.polyfit(m.data.I[int(num_pnt*.75):num_pnt],
            m.data.V[int(num_pnt*.75):num_pnt], 1)
        f3 = np.poly1d(line3)
        x_new3 = np.linspace(m.data.I[int(num_pnt*.75)],
            m.data.I[num_pnt-1], 50)
        y_new3 = f3(x_new3)
        ax.plot(x_new3,y_new3)
        slope3 = line3[0]

        plt.annotate("%.3f" % slope1 + "Ohm", xy=(m.data.I[0] + .00001* num_pnt/400,
         m.data.V[0]),xytext= (m.data.I[0] + .00001* num_pnt/400, m.data.V[0]))

        plt.annotate("%.3f" % slope2 + "Ohm", xy=(m.data.I[int(num_pnt/2)] - .00003*
         num_pnt/400, m.data.V[int(num_pnt/2)] + .00007* num_pnt/400),
         xytext=(m.data.I[int(num_pnt/2)] - .00003* num_pnt/400,
         m.data.V[int(num_pnt/2)] + .00007* num_pnt/400))

        plt.annotate("%.3f" % slope3 + "Ohm",
            xy=(m.data.I[-1] - .00006* num_pnt/400, m.data.V[-1]),
            xytext= (m.data.I[-1] - .00006* num_pnt/400, m.data.V[-1]))
    plt.title(timestamp + "\n" + "SQUID #" + squidNum)
    plt.savefig("C:\\Users\\Cactus\\Dropbox (Nowack lab)\\TeamData\\DippingProbe\\SQUID_testing_graphs\\" +
        timestamp +"_Squid" + squidNum, dpi=500, bbox_inches = "tight")


def makeModPlot(timestamp , squidNum, path):
    m = dt.loadMeasurement(path + "//" + timestamp +".h5")
    fig, ax = plt.subplots(figsize=(5,4))
    Isquid = np.arange(-.000060, .00005999999999, 5e-7)
    X,Y = np.meshgrid(Isquid, m.data.Imod)
    v = m.data.V * 10e-6
    im=ax.pcolor(X, Y, v, cmap="RdBu")
    plt.ylabel('Mod Coil Current (mA)')
    plt.xlabel('Bias Current ($\mu$A)')
    plt.title(timestamp + "\n" + "SQUID #" + squidNum)
    ticks = ax.get_xticks()*10**6
    ax.set_xticklabels(ticks)
    ticks = ax.get_yticks()*10**3
    ax.set_yticklabels(ticks)
    cbar = fig.colorbar(im)
    cbar.set_label("SQUID voltage ($\mu$V)")
    plt.savefig("C:\\Users\\Cactus\\Dropbox (Nowack lab)\\TeamData\\DippingProbe\\SQUID_testing_graphs\\" +
        timestamp +"_Squid" + squidNum, dpi=500, bbox_inches = "tight")

def makeFieldPlot(timestamp , squidNum, path, loop):
    m = dt.loadMeasurement(path + "//" + timestamp +".h5")
    fig, ax = plt.subplots(figsize=(5,4))
    Imod = np.arange(-m.config.I_mod_f, m.config.I_mod_f - .000000000001, m.config.I_mod_f*2/m.config.num_mod)
    X,Y = np.meshgrid(m.data.field_current, Imod)
    v = m.data.V *10**6
    im=ax.pcolor(X, Y, v, cmap="magma")
    plt.ylabel('Mod Coil Current ($\mu$A)')
    plt.xlabel('Field coil current (mA)')
    plt.title(timestamp + "\n" + "SQUID #" + squidNum +
        "\n"+ loop+ "\n"+ date)
    ticks = ax.get_xticks()*10**3
    ax.set_xticklabels(ticks)
    ticks = ax.get_yticks()*10**6
    ax.set_yticklabels(ticks)
    cbar = fig.colorbar(im)
    cbar.set_label("SQUID voltage ($\mu$V)")
    plt.savefig("C:\\Users\\Cactus\\Dropbox (Nowack lab)\\TeamData\\DippingProbe\\SQUID_testing_graphs\\" +
        timestamp +"_Squid" + squidNum, dpi=500, bbox_inches = "tight")
    plt.show()

def makeAllFieldPlot(timestamp1 ,timestamp2,timestamp3, squidNum, file):
    if(timestamp1!=0):
        makeFieldPlot(timestamp1 , squidNum,path, 'Entire Loop')

    if(timestamp2!=0):
        makeFieldPlot(timestamp2 , squidNum, path, 'Non-Pickup Loop')

    if(timestamp3!=0):
        makeFieldPlot(timestamp3 , squidNum, path, 'Pickup Loop')
