import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
import matplotlib.font_manager as fm
import matplotlib.ticker as ticker
import numpy as np
from statsmodels.nonparametric.smoothers_lowess import lowess
from matplotlib.colors import LogNorm
from matplotlib.colors import LinearSegmentedColormap

class dplot():
    @staticmethod
    def makecbar(ax, image, formatter=None):
        '''
        Make colorbar
        '''
        d = make_axes_locatable(ax)
        cax = d.append_axes('right', size=.1, pad=.1)
        cbar = plt.colorbar(image, cax=cax, format=formatter)
        #cbar.formatter.set_powerlimits((-0,0))
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

    @staticmethod
    def vibplot_image(ax, image, aspect='auto', extent=None, 
                     cmap='viridis', vmax=None, vmin=None, 
                     label=r'm$\Phi_0$'):
        im = ax.imshow(image, cmap=cmap, aspect=aspect, extent=extent,
                        origin='lower', vmax=vmax, vmin=vmin, 
                        norm=LogNorm(vmin=vmin, vmax=vmax))

        [cax, cbar] = dplot.makecbar(ax, im)
        cbar.set_label(label)

        dplot.noaxes(ax)

        return im

    def vibplot_image_2(ax, image, aspect='auto', extent=None, 
                     cmap='viridis', vmax=None, vmin=None, 
                     label=r'm$\Phi_0$'):
        im = ax.imshow(image, cmap=cmap, aspect=aspect, extent=extent,
                        origin='lower', vmax=vmax, vmin=vmin, 
                        norm=LogNorm(vmin=vmin, vmax=vmax),
                        )

        [cax, cbar] = dplot.makecbar(ax, im)
        cbar.set_label(label)

        dplot.noaxes(ax)

        return [im, cbar, cax]

    def vibplot_image_3(ax, image, aspect='auto', extent=None, 
                     cmap='viridis', vmax=None, vmin=None, 
                     label=r'm$\Phi_0$'):
        im = ax.imshow(image, cmap=cmap, aspect=aspect, extent=extent,
                        origin='lower', vmax=vmax, vmin=vmin, 
                        )

        [cax, cbar] = dplot.makecbar(ax, im)
        cbar.set_label(label)

        dplot.noaxes(ax)

        return [im, cbar, cax]
    
    def vibplot_image_4(ax, image, cax, aspect='auto', extent=None, 
                     cmap='viridis', vmax=None, vmin=None, 
                     label=r'm$\Phi_0$'):
        im = ax.imshow(image, cmap=cmap, aspect=aspect, extent=extent,
                        origin='lower', vmax=vmax, vmin=vmin, 
                        norm=LogNorm(vmin=vmin, vmax=vmax),
                        )

        cbar = plt.colorbar(im, cax=cax, format=None)
        cbar.set_label(label)

        dplot.noaxes(ax)

        return [im, cbar, cax]

    def updatecbar(ax, cax, image_data, image, label):
        im_min = float(image_data.min().values)
        im_max = float(image_data.max().values)
        cax.cla()
        cbar = plt.colorbar(image, cax=cax, format=None)
        cbar.set_label(label)

        
    diverging_bkr_55_10_c35 = [\
        [0.097481, 0.50736, 0.98205],
        [0.1033, 0.50389, 0.97428],
        [0.10863, 0.50041, 0.96653],
        [0.11369, 0.49694, 0.9588],
        [0.11841, 0.49348, 0.95107],
        [0.12275, 0.49002, 0.94336],
        [0.12692, 0.48657, 0.93566],
        [0.13089, 0.48312, 0.92796],
        [0.1346, 0.47968, 0.92028],
        [0.13811, 0.47624, 0.91262],
        [0.14143, 0.4728, 0.90497],
        [0.14458, 0.46938, 0.89732],
        [0.14758, 0.46594, 0.88969],
        [0.15043, 0.46252, 0.88207],
        [0.15312, 0.45912, 0.87446],
        [0.15574, 0.4557, 0.86687],
        [0.1582, 0.4523, 0.85929],
        [0.16051, 0.4489, 0.85172],
        [0.16277, 0.44549, 0.84416],
        [0.16488, 0.44211, 0.83662],
        [0.16693, 0.43871, 0.82909],
        [0.16886, 0.43534, 0.82157],
        [0.17068, 0.43197, 0.81406],
        [0.17242, 0.42859, 0.80657],
        [0.17409, 0.42522, 0.79909],
        [0.17566, 0.42185, 0.79162],
        [0.17718, 0.41849, 0.78417],
        [0.17862, 0.41515, 0.77672],
        [0.17995, 0.4118, 0.76929],
        [0.18122, 0.40846, 0.76187],
        [0.18243, 0.40512, 0.75448],
        [0.18359, 0.40179, 0.74709],
        [0.18468, 0.39847, 0.73972],
        [0.18572, 0.39515, 0.73235],
        [0.18665, 0.39183, 0.725],
        [0.18758, 0.38852, 0.71767],
        [0.18841, 0.38521, 0.71034],
        [0.18918, 0.38191, 0.70304],
        [0.1899, 0.37862, 0.69574],
        [0.19058, 0.37533, 0.68847],
        [0.1912, 0.37204, 0.68119],
        [0.19177, 0.36878, 0.67395],
        [0.1923, 0.3655, 0.6667],
        [0.19277, 0.36224, 0.65948],
        [0.1932, 0.35896, 0.65228],
        [0.19358, 0.35572, 0.64508],
        [0.19393, 0.35246, 0.6379],
        [0.19422, 0.34922, 0.63074],
        [0.19446, 0.34597, 0.62359],
        [0.19466, 0.34276, 0.61645],
        [0.19481, 0.33953, 0.60933],
        [0.19492, 0.33629, 0.60222],
        [0.19499, 0.33309, 0.59513],
        [0.19502, 0.32988, 0.58805],
        [0.19502, 0.32665, 0.58099],
        [0.19497, 0.32346, 0.57394],
        [0.19489, 0.32028, 0.56692],
        [0.19477, 0.31708, 0.55991],
        [0.19462, 0.31391, 0.5529],
        [0.19442, 0.31074, 0.54593],
        [0.19419, 0.30755, 0.53895],
        [0.19391, 0.30439, 0.532],
        [0.1936, 0.30123, 0.52507],
        [0.19325, 0.29808, 0.51815],
        [0.19288, 0.29493, 0.51124],
        [0.19247, 0.29181, 0.50436],
        [0.19202, 0.28867, 0.49749],
        [0.19154, 0.28553, 0.49064],
        [0.19103, 0.28244, 0.48379],
        [0.19049, 0.27932, 0.47697],
        [0.18992, 0.27622, 0.47017],
        [0.18932, 0.27311, 0.46338],
        [0.18869, 0.27002, 0.45661],
        [0.18804, 0.26691, 0.44986],
        [0.18733, 0.26385, 0.44313],
        [0.18658, 0.26076, 0.43641],
        [0.18585, 0.25769, 0.42971],
        [0.18505, 0.25465, 0.42302],
        [0.18421, 0.25159, 0.41637],
        [0.18335, 0.24855, 0.40972],
        [0.18247, 0.24548, 0.40309],
        [0.18156, 0.24245, 0.39648],
        [0.18062, 0.23944, 0.38989],
        [0.17967, 0.23642, 0.38333],
        [0.17869, 0.23338, 0.37678],
        [0.17768, 0.23038, 0.37023],
        [0.17659, 0.2274, 0.36372],
        [0.17551, 0.22438, 0.35724],
        [0.17442, 0.22142, 0.35076],
        [0.17327, 0.21845, 0.34429],
        [0.17211, 0.21547, 0.33785],
        [0.17093, 0.21251, 0.33143],
        [0.16973, 0.20955, 0.32503],
        [0.16847, 0.20663, 0.31867],
        [0.16721, 0.20368, 0.3123],
        [0.16588, 0.20071, 0.30599],
        [0.16458, 0.1978, 0.29967],
        [0.16324, 0.1949, 0.29336],
        [0.16187, 0.19198, 0.28708],
        [0.16042, 0.18908, 0.28083],
        [0.15902, 0.1862, 0.27461],
        [0.15755, 0.18329, 0.26841],
        [0.1561, 0.18041, 0.26222],
        [0.15456, 0.17758, 0.25605],
        [0.15302, 0.17471, 0.2499],
        [0.15147, 0.17184, 0.24379],
        [0.14991, 0.16902, 0.23772],
        [0.14827, 0.16616, 0.23164],
        [0.14665, 0.16336, 0.22559],
        [0.14505, 0.16051, 0.21957],
        [0.14339, 0.15773, 0.21357],
        [0.14175, 0.15496, 0.20763],
        [0.14009, 0.1522, 0.20171],
        [0.13851, 0.14952, 0.19588],
        [0.13692, 0.1468, 0.19008],
        [0.13541, 0.14419, 0.18437],
        [0.134, 0.14163, 0.17876],
        [0.13268, 0.1391, 0.17324],
        [0.1315, 0.1367, 0.16787],
        [0.13053, 0.13444, 0.16268],
        [0.12973, 0.13226, 0.15764],
        [0.12916, 0.13028, 0.15284],
        [0.12891, 0.12842, 0.1483],
        [0.12899, 0.12676, 0.14407],
        [0.12945, 0.12536, 0.14011],
        [0.13031, 0.12415, 0.13652],
        [0.13151, 0.12321, 0.13332],
        [0.13315, 0.12253, 0.13051],
        [0.13523, 0.12211, 0.12804],
        [0.13775, 0.12196, 0.126],
        [0.14065, 0.12206, 0.12429],
        [0.14394, 0.12241, 0.12299],
        [0.14762, 0.12299, 0.12205],
        [0.15161, 0.12379, 0.12145],
        [0.15595, 0.12478, 0.12115],
        [0.1605, 0.12596, 0.12111],
        [0.16531, 0.1272, 0.12131],
        [0.17036, 0.12863, 0.12171],
        [0.17553, 0.13018, 0.12228],
        [0.18085, 0.13174, 0.12299],
        [0.1863, 0.13339, 0.12382],
        [0.1918, 0.1351, 0.12474],
        [0.19738, 0.13681, 0.12575],
        [0.20301, 0.13858, 0.12675],
        [0.20867, 0.14035, 0.12784],
        [0.21437, 0.14214, 0.12891],
        [0.2201, 0.14394, 0.13008],
        [0.22584, 0.14575, 0.13119],
        [0.23158, 0.14753, 0.13232],
        [0.23735, 0.14933, 0.13347],
        [0.24308, 0.15109, 0.13464],
        [0.24887, 0.15287, 0.13574],
        [0.25465, 0.15465, 0.13692],
        [0.26041, 0.15645, 0.1381],
        [0.26621, 0.15821, 0.1392],
        [0.27198, 0.15993, 0.14038],
        [0.27781, 0.16174, 0.14154],
        [0.28361, 0.16349, 0.14269],
        [0.28944, 0.16518, 0.14384],
        [0.29526, 0.16697, 0.14501],
        [0.30109, 0.16869, 0.14614],
        [0.30695, 0.17041, 0.1473],
        [0.3128, 0.17212, 0.14842],
        [0.31867, 0.17385, 0.14962],
        [0.32454, 0.17555, 0.15074],
        [0.33043, 0.17728, 0.15189],
        [0.33632, 0.17898, 0.15304],
        [0.34224, 0.18066, 0.1542],
        [0.34815, 0.18235, 0.15536],
        [0.35407, 0.18405, 0.15654],
        [0.36001, 0.18576, 0.15766],
        [0.36596, 0.18743, 0.15884],
        [0.3719, 0.18909, 0.15995],
        [0.37787, 0.19075, 0.16115],
        [0.38385, 0.19241, 0.16231],
        [0.38983, 0.1941, 0.16346],
        [0.39584, 0.19573, 0.1646],
        [0.40184, 0.19738, 0.16573],
        [0.40786, 0.19901, 0.16693],
        [0.41389, 0.20064, 0.16806],
        [0.41994, 0.20228, 0.16925],
        [0.42598, 0.20394, 0.17038],
        [0.43206, 0.20555, 0.17153],
        [0.43813, 0.20718, 0.17269],
        [0.44421, 0.20879, 0.17385],
        [0.4503, 0.2104, 0.17502],
        [0.4564, 0.21202, 0.17614],
        [0.46251, 0.21361, 0.17734],
        [0.46864, 0.2152, 0.1785],
        [0.47479, 0.21681, 0.17964],
        [0.48092, 0.21839, 0.18078],
        [0.48709, 0.21998, 0.18194],
        [0.49325, 0.22155, 0.1831],
        [0.49943, 0.22314, 0.18427],
        [0.50562, 0.22468, 0.18546],
        [0.51182, 0.22628, 0.18659],
        [0.51804, 0.22784, 0.18779],
        [0.52426, 0.22938, 0.18892],
        [0.53049, 0.23094, 0.19008],
        [0.53674, 0.23249, 0.19123],
        [0.54299, 0.23403, 0.1924],
        [0.54925, 0.23559, 0.19357],
        [0.55552, 0.23713, 0.19474],
        [0.56181, 0.23863, 0.19589],
        [0.5681, 0.24016, 0.19706],
        [0.57441, 0.2417, 0.1982],
        [0.58073, 0.2432, 0.19936],
        [0.58705, 0.24472, 0.20052],
        [0.59339, 0.24623, 0.20169],
        [0.59974, 0.24776, 0.20286],
        [0.60609, 0.24925, 0.20405],
        [0.61246, 0.25075, 0.20519],
        [0.61885, 0.25225, 0.20639],
        [0.62523, 0.25374, 0.20753],
        [0.63163, 0.25524, 0.20869],
        [0.63803, 0.25671, 0.20986],
        [0.64445, 0.25817, 0.21103],
        [0.65088, 0.25967, 0.21221],
        [0.65732, 0.26113, 0.21335],
        [0.66377, 0.2626, 0.21453],
        [0.67023, 0.26407, 0.21571],
        [0.6767, 0.26552, 0.21688],
        [0.68317, 0.26696, 0.21804],
        [0.68966, 0.26842, 0.21921],
        [0.69616, 0.26988, 0.22039],
        [0.70267, 0.27131, 0.22154],
        [0.70919, 0.27274, 0.22272],
        [0.71571, 0.27418, 0.22387],
        [0.72224, 0.27563, 0.22504],
        [0.72879, 0.27705, 0.22624],
        [0.73535, 0.27847, 0.2274],
        [0.74191, 0.27988, 0.22858],
        [0.74849, 0.28129, 0.22972],
        [0.75508, 0.28272, 0.23091],
        [0.76167, 0.28411, 0.23209],
        [0.76827, 0.28551, 0.23324],
        [0.77488, 0.28691, 0.23444],
        [0.78151, 0.28831, 0.23561],
        [0.78814, 0.28971, 0.23679],
        [0.79478, 0.2911, 0.23795],
        [0.80143, 0.29248, 0.23912],
        [0.80809, 0.29385, 0.24028],
        [0.81476, 0.29523, 0.24148],
        [0.82144, 0.29662, 0.24264],
        [0.82812, 0.29797, 0.24381],
        [0.83482, 0.29935, 0.24499],
        [0.84153, 0.3007, 0.24617],
        [0.84824, 0.30205, 0.24736],
        [0.85497, 0.30341, 0.24855],
        [0.8617, 0.30477, 0.2497],
        [0.86845, 0.30613, 0.25089],
        [0.8752, 0.30745, 0.25208],
        [0.88196, 0.30881, 0.25325],
        [0.88873, 0.31015, 0.25444],
        [0.8955, 0.31147, 0.25561],
        [0.90229, 0.31279, 0.25679],
    ]

    bkr = LinearSegmentedColormap.from_list('david_bkr',
        diverging_bkr_55_10_c35)

    diverging_bky_60_10_c30 = [\
        [0.056674, 0.57959, 0.98121],
        [0.066107, 0.57547, 0.97345],
        [0.074463, 0.57135, 0.9657],
        [0.081994, 0.56724, 0.95796],
        [0.088742, 0.56314, 0.95024],
        [0.09499, 0.55904, 0.94252],
        [0.10067, 0.55495, 0.93482],
        [0.10603, 0.55086, 0.92713],
        [0.11098, 0.54678, 0.91945],
        [0.1156, 0.54271, 0.91178],
        [0.11993, 0.53864, 0.90413],
        [0.12401, 0.53457, 0.89649],
        [0.1279, 0.53052, 0.88886],
        [0.13155, 0.52647, 0.88124],
        [0.135, 0.52241, 0.87363],
        [0.13827, 0.51838, 0.86604],
        [0.14137, 0.51435, 0.85845],
        [0.1443, 0.51031, 0.85088],
        [0.14707, 0.50628, 0.84333],
        [0.14975, 0.50227, 0.83578],
        [0.15224, 0.49827, 0.82825],
        [0.15465, 0.49426, 0.82073],
        [0.15694, 0.49026, 0.81323],
        [0.15911, 0.48626, 0.80573],
        [0.1612, 0.48228, 0.79826],
        [0.16316, 0.4783, 0.79079],
        [0.16499, 0.47433, 0.78334],
        [0.1668, 0.47036, 0.77589],
        [0.16848, 0.46639, 0.76846],
        [0.17009, 0.46243, 0.76105],
        [0.1716, 0.45849, 0.75365],
        [0.17304, 0.45455, 0.74626],
        [0.17442, 0.45061, 0.73889],
        [0.17569, 0.44668, 0.73153],
        [0.17693, 0.44275, 0.72418],
        [0.17811, 0.43883, 0.71685],
        [0.17917, 0.43493, 0.70953],
        [0.18019, 0.43102, 0.70222],
        [0.18114, 0.42712, 0.69493],
        [0.18204, 0.42322, 0.68765],
        [0.18288, 0.41934, 0.68038],
        [0.18367, 0.41546, 0.67314],
        [0.1844, 0.41158, 0.6659],
        [0.18509, 0.40772, 0.65868],
        [0.18571, 0.40387, 0.65148],
        [0.18626, 0.40001, 0.64428],
        [0.18676, 0.39617, 0.6371],
        [0.18724, 0.39232, 0.62994],
        [0.18767, 0.3885, 0.62279],
        [0.18804, 0.38466, 0.61565],
        [0.18835, 0.38086, 0.60854],
        [0.18861, 0.37705, 0.60143],
        [0.18884, 0.37323, 0.59434],
        [0.18902, 0.36944, 0.58727],
        [0.18916, 0.36565, 0.58021],
        [0.18925, 0.36187, 0.57317],
        [0.18931, 0.3581, 0.56614],
        [0.18932, 0.35433, 0.55913],
        [0.18929, 0.35058, 0.55214],
        [0.18923, 0.34682, 0.54515],
        [0.18912, 0.34307, 0.53819],
        [0.18898, 0.33934, 0.53124],
        [0.1888, 0.3356, 0.52431],
        [0.18859, 0.33187, 0.51739],
        [0.18833, 0.32815, 0.51049],
        [0.18805, 0.32444, 0.5036],
        [0.18772, 0.32075, 0.49673],
        [0.18734, 0.31705, 0.48988],
        [0.18692, 0.31337, 0.48305],
        [0.18649, 0.3097, 0.47624],
        [0.18603, 0.30603, 0.46945],
        [0.18554, 0.30234, 0.46265],
        [0.18499, 0.2987, 0.45589],
        [0.1844, 0.29505, 0.44915],
        [0.18379, 0.29142, 0.44242],
        [0.18315, 0.28778, 0.43571],
        [0.18248, 0.28416, 0.429],
        [0.18178, 0.28053, 0.42232],
        [0.18105, 0.27695, 0.41567],
        [0.18029, 0.27335, 0.40903],
        [0.1795, 0.26977, 0.4024],
        [0.1787, 0.26618, 0.39581],
        [0.17786, 0.26261, 0.38922],
        [0.17694, 0.25905, 0.38265],
        [0.176, 0.25549, 0.37611],
        [0.17509, 0.25195, 0.36958],
        [0.17411, 0.24842, 0.36307],
        [0.1731, 0.24486, 0.35659],
        [0.17207, 0.24136, 0.35012],
        [0.17101, 0.23785, 0.34366],
        [0.16994, 0.23435, 0.33724],
        [0.16882, 0.23085, 0.33082],
        [0.16766, 0.22737, 0.32443],
        [0.16649, 0.22389, 0.31807],
        [0.16526, 0.22045, 0.31171],
        [0.16408, 0.21698, 0.3054],
        [0.16281, 0.21352, 0.29909],
        [0.16154, 0.21009, 0.2928],
        [0.16017, 0.20669, 0.28653],
        [0.15887, 0.20325, 0.28029],
        [0.15748, 0.19982, 0.27408],
        [0.15612, 0.19646, 0.26786],
        [0.15467, 0.19306, 0.26171],
        [0.15321, 0.18968, 0.25556],
        [0.15174, 0.18632, 0.24942],
        [0.15026, 0.18294, 0.2433],
        [0.14871, 0.17961, 0.23725],
        [0.14718, 0.17625, 0.23118],
        [0.14564, 0.17295, 0.22512],
        [0.14403, 0.16968, 0.21913],
        [0.14243, 0.16638, 0.21314],
        [0.14084, 0.16314, 0.20723],
        [0.13919, 0.15988, 0.2013],
        [0.13765, 0.15674, 0.19547],
        [0.13602, 0.15358, 0.18968],
        [0.13455, 0.15054, 0.18396],
        [0.13306, 0.14756, 0.17836],
        [0.13167, 0.14469, 0.1728],
        [0.13042, 0.14192, 0.16741],
        [0.12922, 0.13927, 0.16217],
        [0.12825, 0.13686, 0.15706],
        [0.12743, 0.13466, 0.15217],
        [0.12685, 0.13265, 0.14756],
        [0.12655, 0.13093, 0.14317],
        [0.12652, 0.12946, 0.13905],
        [0.12678, 0.12834, 0.1353],
        [0.12737, 0.12752, 0.13186],
        [0.12833, 0.12704, 0.12874],
        [0.12961, 0.12694, 0.12604],
        [0.13123, 0.12718, 0.12362],
        [0.13318, 0.1278, 0.12159],
        [0.13545, 0.1287, 0.11992],
        [0.13807, 0.12997, 0.11861],
        [0.14093, 0.13147, 0.11751],
        [0.14404, 0.13325, 0.11674],
        [0.14739, 0.13526, 0.11622],
        [0.15092, 0.1375, 0.11588],
        [0.15463, 0.13984, 0.11572],
        [0.15851, 0.14242, 0.11571],
        [0.16247, 0.14511, 0.11584],
        [0.16652, 0.14785, 0.11606],
        [0.17065, 0.15069, 0.11635],
        [0.17485, 0.15359, 0.11668],
        [0.17908, 0.15658, 0.11705],
        [0.18333, 0.15955, 0.11747],
        [0.18766, 0.16261, 0.11793],
        [0.19194, 0.16563, 0.11839],
        [0.19628, 0.16874, 0.11884],
        [0.20058, 0.17182, 0.11927],
        [0.20495, 0.17495, 0.11971],
        [0.2093, 0.17808, 0.12015],
        [0.21365, 0.18116, 0.12058],
        [0.21802, 0.18431, 0.12101],
        [0.22237, 0.18748, 0.12142],
        [0.22675, 0.19061, 0.12183],
        [0.23112, 0.19379, 0.12224],
        [0.23551, 0.19696, 0.12264],
        [0.23987, 0.20011, 0.12303],
        [0.24425, 0.20332, 0.12341],
        [0.24867, 0.20654, 0.12378],
        [0.25306, 0.20972, 0.12415],
        [0.25746, 0.21292, 0.12451],
        [0.26188, 0.21617, 0.12486],
        [0.2663, 0.21939, 0.12521],
        [0.27074, 0.22263, 0.12555],
        [0.27516, 0.22588, 0.12587],
        [0.2796, 0.22912, 0.12618],
        [0.28403, 0.23239, 0.12646],
        [0.28849, 0.23566, 0.12673],
        [0.29294, 0.23892, 0.12701],
        [0.29741, 0.24221, 0.12728],
        [0.30187, 0.24549, 0.12756],
        [0.30637, 0.24881, 0.12782],
        [0.31086, 0.25212, 0.12807],
        [0.31534, 0.25543, 0.1283],
        [0.31985, 0.25875, 0.12852],
        [0.32434, 0.26208, 0.12872],
        [0.32887, 0.26541, 0.12892],
        [0.33339, 0.26877, 0.12911],
        [0.3379, 0.27209, 0.12931],
        [0.34245, 0.27548, 0.12949],
        [0.34699, 0.27884, 0.12967],
        [0.35153, 0.28221, 0.12983],
        [0.35609, 0.28557, 0.12998],
        [0.36064, 0.28897, 0.13012],
        [0.36522, 0.29236, 0.13024],
        [0.36979, 0.29575, 0.13035],
        [0.37439, 0.29917, 0.13045],
        [0.37897, 0.30257, 0.13053],
        [0.38358, 0.30601, 0.13061],
        [0.38818, 0.30944, 0.13067],
        [0.39279, 0.31285, 0.13073],
        [0.39741, 0.31631, 0.13077],
        [0.40203, 0.31975, 0.1308],
        [0.40668, 0.3232, 0.13082],
        [0.41131, 0.32665, 0.13083],
        [0.41596, 0.33013, 0.13082],
        [0.42062, 0.3336, 0.13081],
        [0.42529, 0.33708, 0.13078],
        [0.42996, 0.34056, 0.13075],
        [0.43464, 0.34404, 0.1307],
        [0.43932, 0.34756, 0.13063],
        [0.44402, 0.35106, 0.13056],
        [0.44872, 0.35457, 0.13047],
        [0.45341, 0.35808, 0.13037],
        [0.45813, 0.3616, 0.13025],
        [0.46284, 0.36513, 0.13012],
        [0.46758, 0.36867, 0.12998],
        [0.47231, 0.3722, 0.12981],
        [0.47705, 0.37575, 0.12963],
        [0.4818, 0.3793, 0.12943],
        [0.48655, 0.38286, 0.12922],
        [0.49133, 0.38642, 0.129],
        [0.49608, 0.38999, 0.12877],
        [0.50086, 0.39357, 0.12854],
        [0.50564, 0.39715, 0.1283],
        [0.51043, 0.40075, 0.12803],
        [0.51523, 0.40433, 0.12773],
        [0.52003, 0.40793, 0.1274],
        [0.52484, 0.41154, 0.12707],
        [0.52966, 0.41515, 0.12674],
        [0.53448, 0.41876, 0.12641],
        [0.53931, 0.42238, 0.12606],
        [0.54415, 0.42601, 0.12567],
        [0.549, 0.42965, 0.12524],
        [0.55385, 0.43328, 0.12481],
        [0.5587, 0.43694, 0.12436],
        [0.56357, 0.44058, 0.1239],
        [0.56844, 0.44424, 0.12341],
        [0.57332, 0.44789, 0.12291],
        [0.5782, 0.45157, 0.1224],
        [0.58309, 0.45524, 0.12186],
        [0.58798, 0.45892, 0.12131],
        [0.5929, 0.46259, 0.12074],
        [0.5978, 0.46628, 0.12015],
        [0.60272, 0.46998, 0.11954],
        [0.60765, 0.47367, 0.11893],
        [0.61257, 0.47738, 0.11828],
        [0.61751, 0.48108, 0.11755],
        [0.62245, 0.48479, 0.11685],
        [0.6274, 0.48852, 0.11615],
        [0.63236, 0.49224, 0.11536],
        [0.63732, 0.49596, 0.11454],
        [0.64229, 0.4997, 0.11378],
        [0.64726, 0.50344, 0.11298],
        [0.65224, 0.50719, 0.1121],
        [0.65724, 0.51093, 0.11121],
        [0.66223, 0.5147, 0.11031],
        [0.66723, 0.51846, 0.10936],
        [0.67223, 0.52221, 0.10832],
        [0.67725, 0.52599, 0.10736],
        [0.68226, 0.52976, 0.10634],
        [0.68729, 0.53353, 0.10521],
        [0.69232, 0.53733, 0.10412],
        [0.69735, 0.54111, 0.103],
        [0.7024, 0.54491, 0.1018],
        ]

    bky = LinearSegmentedColormap.from_list('david_bky',
            diverging_bky_60_10_c30)