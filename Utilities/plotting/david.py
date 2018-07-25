import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import matplotlib.font_manager as fm
import matplotlib.ticker as ticker
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess

class dplot():
    @staticmethod
    def makecbar(ax, image, formatter=None):
        '''
        Make colorbar
        '''
        d = make_axes_locatable(ax)
        cax = d.append_axes('right', size=.1, pad=.1)
        cbar = plt.colorbar(image, cax=cax, format=formatter)
        #cbar.set_label(label)
        return [cax, cbar]
    
    @staticmethod
    def makecbar_sci(ax, image):
        '''
        Make colorbar with scientific notation as labels
        '''
        formatter = dplot.cbar_sci_formatter()
        return dplot.makecbar(ax, image, formatter)

    @staticmethod
    def cbar_sci_formatter():
        def fmt(x, pos):
            a,b = '{:.2e}'.format(x).split('e')
            b = int(b)
            return r'${} \times 10^{{{}}}$'.format(a,b)

        return ticker.FuncFormatter(fmt)
    
    @staticmethod
    def noaxes(ax):
        '''
        Removes x,y axes
        '''
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
    
    @staticmethod
    def addscalebar(ax, length, label, color, 
                    pos = 'lower left', 
                    frameon=False,
                    size_vertical=1,
                    fontsize=18):
        '''
        remove scalebar by ax.artists[0].remove()
        '''
        fontprops=fm.FontProperties(size=fontsize)
        scalebar = AnchoredSizeBar(ax.transData,
                                   length,
                                   label,
                                   pos,
                                   pad=.1,
                                   color=color,
                                   frameon=frameon,
                                   size_vertical=size_vertical,
                                   fontproperties=fontprops
                                   )
        ax.add_artist(scalebar)
    
    @staticmethod
    def _plotscanplane(data, X, Y, ax, phi0perV = .0565, 
                      x=(-400,400), 
                      y=(-400,400), 
                      cmap='viridis', aspect='equal',
                      vmax=None, vmin=None, sigma=-1, cbarsci=False):
        [xi_i, xf_i, yi_i, yf_i] = dplot.findindicies(X, Y, x,y)

        if sigma != -1:
            mean = np.mean(data[yi_i:yf_i,xi_i:xf_i]*phi0perV)
            std = np.std(data[yi_i:yf_i,xi_i:xf_i]*phi0perV)
            vmax = mean+sigma*std
            vmin = mean-sigma*std

        image = ax.imshow(data[yi_i:yf_i,xi_i:xf_i]*phi0perV, 
                          cmap=cmap,
                          aspect=aspect,
                          extent=(X[0][xi_i],X[0][xf_i],
                                  Y[yi_i][0],Y[yf_i][0]),
                          origin='lower',
                          vmax=vmax,
                          vmin=vmin)
        if cbarsci:
            [cax, cbar] = dplot.makecbar_sci(ax, image)
        else:
            [cax, cbar] = dplot.makecbar(ax, image)

        return [image, cax, cbar, vmin, vmax]

    @staticmethod
    def plotscanplane_smoothed(sp, ax, name='dc', phi0perV=.0565,
                               x=(-400,400), y=(-400,400),
                               cmap='viridis',aspect='equal',
                               vmax=None,vmin=None, sigma=3,
                               cbarsci=False, frac=.01, 
                                minusmean=False, mult=None):
        '''
        Plot scanplane removing sigma 
        '''
        [xi_i, xf_i, yi_i, yf_i] = dplot.findindicies(sp.X, sp.Y, x,y)

        data = np.copy(sp.V[name])
        if minusmean:
            data = data - np.mean(data)

        if mult != None:
            data = data * mult
        
        for i in range(yf_i - yi_i):
            data[yi_i+i,xi_i:xf_i] = dplot.cropbysigma(data[yi_i+i,
                                                            xi_i:xf_i], 
                                                            numsigma=sigma)
            data[yi_i+i,xi_i:xf_i] = dplot.smooth(data[yi_i+i,xi_i:xf_i], 
                                                    sp.X[0][xi_i:xf_i], 
                                                    frac=frac)

        return dplot._plotscanplane(data, 
                             sp.X, sp.Y, ax, phi0perV=phi0perV, 
                             x=x, y=y, cmap=cmap, aspect=aspect,
                             vmax=vmax, vmin=vmin, sigma=-1, 
                             cbarsci=cbarsci)


    @staticmethod
    def plotscanplane(sp, ax, name='dc', phi0perV = .0565, 
                      x=(-400,400), 
                      y=(-400,400), 
                      cmap='viridis', aspect='equal',
                      vmax=None, vmin=None, sigma=-1, cbarsci=False):
        '''
        Plots scanplane

        Params:
        -------
        sp (Scanplane object)
        ax (matplotlib pyplot axes)
        name (string): name of field to plot (dc, acx, acy, cap)
        phi0perV (float): phi_0 / V conversion for this scan
        x (2-ple of float): extent in x direction, in units of V
        y (2-ple of float): extent in y direction, in units of V
        aspect, vmax, vmin: passed straight to imshow
        cbarsci (boolean): if colorbar scale should be in scientific notation

        Returns:
        --------
        [image, cax, cbar]
        image: image = ax.imshow()
        cax: colorbar axes
        cbar: colorbar
        '''
        return dplot._plotscanplane(
                              sp.V[name], sp.X, sp.Y, ax, 
                              phi0perV=phi0perV,
                              x=x, y=y, cmap=cmap, aspect=aspect,
                              vmax=vmax, vmin=vmin,
                              sigma=sigma, cbarsci=cbarsci)

    @staticmethod
    def plotscanspectra(sc, ax, phi0perV = 1/14.4, cmap='viridis', 
                        aspect='equal', vmax=None, vmin=None, sigma=-1,
                        cbarsci=True, deriv=False, derivdir=0, timeav=True):
        psds = np.array(sc.psdAve.reshape(sc.numpts[0],sc.numpts[1],-1))
        vs   = np.array(sc.V.reshape(sc.numpts[0],sc.numpts[1],-1))
        timeaveragev = np.mean(vs, axis=-1)
        freqaveragev = np.mean(psds, axis=-1)

        if deriv:
            if derivdir == 0:
                diff = np.abs(sc.X[0,1] - sc.X[0,0])
            else:
                diff = np.abs(sc.Y[1,0] - sc.Y[0,0])
        if timeav and deriv:
            plotted = np.gradient(timeaveragev, diff, axis=derivdir)
        elif timeav and not deriv:
            plotted = timeaveragev
        elif not timeav and deriv:
            plotted = np.gradient(freqaveragev, diff, axis=derivdir)
        elif not timeav and not deriv:
            plotted = freqaveragev


        extent = (sc.X[0,0],sc.X[-1,-1], sc.Y[0,0], sc.Y[-1,-1])

        if sigma != -1:
            mean = np.mean(plotted)
            std = np.std(plotted)
            vmax = mean+sigma*std
            vmin = mean-sigma*std

        image = ax.imshow(plotted,
                          cmap=cmap,
                          aspect=aspect,
                          extent=extent,
                          origin='lower',
                          vmax=vmax,
                          vmin=vmin)
        if cbarsci:
            [cax, cbar] = dplot.makecbar_sci(ax, image)
        else:
            [cax, cbar] = dplot.makecbar(ax, image)

        return [image, cax, cbar, vmin, vmax]

    @staticmethod
    def dumbimshow(data, ax, extent=None, cmap='viridis',
                    aspect='equal', cbarsci=True, origin='lower',
                    small=False, cbar=True, vmax=None,vmin=None):
        image = ax.imshow(data, cmap=cmap, aspect=aspect,
                          extent=extent, origin=origin,
                          vmax=vmax, vmin=vmin)
        if cbar:
            if cbarsci:
                [cax, cbar] = dplot.makecbar_sci(ax, image)
            else:
                [cax, cbar] = dplot.makecbar(ax, image)

        if small:
            dplot.noaxes(ax)
            if cbar:
                cbar.ax.tick_params(labelsize=5) 
            else:
                cbar=None
                cax=None

        return [image, cax, cbar]
    
    @staticmethod
    def findindicies(X, Y, x=(-400,400), y=(-400,400)):
        xi_i = np.argmin(np.abs(X[0]-x[0]))
        xf_i = np.argmin(np.abs(X[0]-x[1]))
        yi_i = np.argmin(np.abs(Y[:,0]-y[0]))
        yf_i = np.argmin(np.abs(Y[:,0]-y[1]))
        return [xi_i, xf_i, yi_i, yf_i]

    
    @staticmethod
    def plotsigma(ax, data, numsigma=1, color='k', label=''):
        mean = np.mean(data)
        std  = np.std(data)
        ax.axhline(mean+numsigma*std, linestyle=':', color=color, 
                label=label+'+{} sigma'.format(numsigma))
        ax.axhline(mean-numsigma*std, linestyle=':', color=color,
                label=label+'-{} sigma'.format(numsigma))
                                   
    
    @staticmethod
    def croplinesbysigma(data, X, Y, 
                        x=(-400,-400), y=(-400,400), numsigma=1,
                        meanoverx=True):
        meanedata = np.array(data)
        [xi_i, xf_i, yi_i, yf_i] = dplot.findindicides(X,Y,x,y)
        if meanoverx:
            for i in range(yf_i-yi_i):
                thisslice = meandata[xi_i:xf_i,i+yi_i]
                dplot.cropbysigma(thisslice, numsigma)
        else:
            print('Not implemented yet')

        return meandata

    @staticmethod
    def cropbysigma(data, numsigma=1):
        data = np.copy(data)
        mean = np.mean(data)
        std = np.std(data)
        data[np.logical_and(data > mean+numsigma*std,
                            data < mean-numsigma*std)
            ] = np.nan
        return data

    @staticmethod
    def smooth(data, X, frac=.01):
        smoothed = lowess(data, X, frac=frac, return_sorted=False)
        return smoothed


    @staticmethod
    def boundaryplotter(sp, ax, x=(-400,400), y=(-400,400), span_v=30,
                        frac=.01, sigma=3, cmap='viridis', 
                        phi0perV = .0565, minusmean=True,
                        aspect='equal'):
        [xi_i, xf_i, yi_i, yf_i] = dplot.findindicies(sp.X,sp.Y,x,y)
        dcdata = np.copy(sp.V['dc' ][yi_i:yf_i,xi_i:xf_i])
        acdata = np.copy(sp.V['acx'][yi_i:yf_i,xi_i:xf_i])


        if minusmean:
            dcdata = dcdata - np.mean(dcdata)
        
        xleft = 0
        xright = 0
        data = 0
        for i in range(yf_i-yi_i):
            xcenter_i = np.argmin(acdata[i,:])   

            if i == 0:
                xleft_i = np.argmin(np.abs(sp.X[yi_i+i,:] - 
                                    sp.X[yi_i+i][xcenter_i] + span_v))
                xright_i = np.argmin(np.abs(sp.X[yi_i+i,:] - 
                                     sp.X[yi_i+i][xcenter_i] - span_v))
                data = np.full( (yf_i-yi_i,xright_i-xleft_i), np.nan)
                xleft = xcenter_i - xleft_i
                xright = xright_i - xcenter_i
            
            data[i,:] = dcdata[i,xcenter_i-xleft:xcenter_i+xright]
            data[i,:] = dplot.cropbysigma(data[i, :], 
                                          numsigma=sigma)
            data[i,:] = dplot.smooth(data[i,:], sp.X[i,xcenter_i-xleft:
                                                       xcenter_i+xright], 
                                                    frac=frac)
            data[i,:] = dplot.cropbysigma(data[i, :], 
                                          numsigma=sigma)

        #frac = frac * sp.V['dc'].shape[1]/data.shape[1]
        print(data.shape, sp.X[0,xcenter_i-xleft:xcenter_i+xright].shape,
              sp.Y[yi_i:yf_i,0].shape, frac)

        std = np.std(data*phi0perV, axis=1)
        amp = np.max(data*phi0perV, axis=1) - np.min(data*phi0perV, axis=1)

        dplot._plotscanplane(data, sp.X[:,
                                        xcenter_i-xleft:xcenter_i+xright], 
                                   sp.Y[yi_i:yf_i,:], 
                                   ax, phi0perV = phi0perV,
                                   x=x, y=y,
                                   cmap=cmap, aspect=aspect,
                      vmax=None, vmin=None, sigma=-1, cbarsci=True)

        return [std, amp, sp.Y[yi_i:yf_i,0]]

            

