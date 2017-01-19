import numpy as np, os, matplotlib.pyplot as plt, scipy
from datetime import datetime
from scipy.io import loadmat
from scipy.interpolate import interp2d

class Image:
    _dx = 1
    _dy = 1
    _Lx = 1
    _Ly = 1
    ax = None

    def __init__(self, data, real_size=None, pixel_size=None, data_units = None, units='um'):
        '''
        Class containing information and properties useful for image processing.
        input:
            data: 2D numpy array of image data
            units: string with description of units (just for bookkeeping)
            real_size: tuple (Lx, Ly) of real total size of image.
            pixel_size: tuple (dx, dy) of size of pixels in image
        Useful information stored:
            Nx, Ny: number of pixels
            Lx, Ly: real size of image (in specified units)
            dx, dy: pixel size (in specified units)
        '''
        self.data_original = data.copy()
        self.data = data
        self.Nx, self.Ny = data.shape[::-1] # i, j = y, x
        self.data_units = data_units
        self.units = units
        if real_size is not None and pixel_size is not None:
            raise Exception('Only specify real size OR pixel size!')
        elif real_size is not None:
            self.Lx, self.Ly = real_size
        elif pixel_size is not None:
            self.dx, self.dy = pixel_size
        else:
            self.dx, self.dy = (1,1) # calculate using default pixel size of 1x1 units

        self._dx_original = self.dx
        self._dy_original = self.dy

    def __repr__(self):
        return 'Image %ix%i pixels, %.2fx%.2f %s' %(self.Nx, self.Ny, self.Lx, self.Ly, self.units)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.Ny, self.Nx = value.shape
        self.dx, self.dy = self._dx, self._dy # force recalculation of Lx,Ly

    @property
    def Lx(self):
        return self._Lx

    @Lx.setter
    def Lx(self, value):
        self._Lx = value
        self._dx = self._Lx/self.Nx

    @property
    def Ly(self):
        return self._Ly

    @Ly.setter
    def Ly(self, value):
        self._Ly = value
        self._dy = self._Ly/self.Ny

    @property
    def dx(self):
        return self._dx

    @dx.setter
    def dx(self, value):
        self._dx = value
        self._Lx = self._dx*self.Nx

    @property
    def dy(self):
        return self._dy

    @dy.setter
    def dy(self, value):
        self._dy = value
        self._Ly = self._dy*self.Ny

    def center_max(self):
        '''
        Shifts the contents of an array so that its maximum value is located at the center.
        Why do we want to do this?
            If the point spread function is not centered, the deconvolution will be shifted.

        Pads an array using a faded padding, then slices the array to center the maximum.
        '''
        pos_max = np.unravel_index(np.argmax(self.data), self.data.shape) # index of max as a tuple
        shift = [int(self.data.shape[i]/2) - pos_max[i] for i in range(2)] # tuple telling us how many indices to shif the array
        pad_width = [(0,0),(0,0)] # [(l,r),(u,d)]
        slices = [slice(None),slice(None)] # will tell us how to crop the padded array
        for i in range(2):
            if shift[i] < 0:
                pad_width[i] = (0, -shift[i]) # add to one side
                slices[i] = slice(-shift[i], None) # crop off the other side
            elif shift[i] > 0:
                pad_width[i] = (shift[i], 0)
                slices[i] = slice(0, -shift[i])
        padded_data = np.pad(self.data, pad_width, mode='linear_ramp')
        self.data = padded_data[tuple(slices)]


    def deconvolute(self, PSF, kxmax=1, kymax=1, restore_PSF=True):
        '''
        Deconvolute a known point spread function.
        '''
        ## Get this image and the PSF ready
        self.pad() # default = double in size symmetrically and fade

        PSF.pad_to_match(self) # pad the PSF to match this image
        PSF.resample(self.data.shape)
        PSF.center_max() # shift max to center

        ## FFT
        data_k = np.fft.fftshift( # shift so DC is in the center rather than in the corner
                    np.fft.fft2( # 2D fft
                        self.data
                        )
                    )
        PSF_k = np.fft.fftshift( # DC to center
                    np.fft.fft2( # 2D fft
                        np.fft.fftshift( # max to corner
                            PSF.data
                                )
                            )
                        )


        ## K vectors - for Biot-Savart??
        kx = np.linspace(-np.pi/self.dx, np.pi/self.dx, self.Nx, endpoint=False)
        ky = np.linspace(-np.pi/self.dy, np.pi/self.dy, self.Ny, endpoint=False)

        ## Hanning window
        H = hanning_2D(kx, ky, kxmax, kymax)

        ## Inverse Fourier transform back to real space
        self.data = np.fft.ifft2(
                        np.fft.fftshift( ## FFT or IFFT?
                            data_k/PSF_k*H
                        )
                    )

        ## Crop and take real component
#         print(self.data.shape)
        self.data = self.data[int(self.Ny/4):-int(self.Ny/4),int(self.Nx/4):-int(self.Nx/4)].real

        ## Restore PSF
        if restore_PSF:
            PSF.restore()


    def deconvolve(self, *args, **kwargs):
        '''
        For those who prefer grammatical accuracy :)
        '''
        self.deconvolute(*args, **kwargs)


    def match_size(self, image):
        '''
        Change size of image to match another image.
        '''
        pass


    def invert_current(self, PSF=None, z=1.0):
        '''
        Algorithm to do basic current inversion. If not given a PSF, will try to invert current without deconvoluting the PSF.
        '''
        mu_0 = 4*np.pi*1e-7

        ## Get this image and the PSF ready
        self.pad() # default = double in size symmetrically and fade

        if PSF is not None:
            PSF.pad_to_match(self) # pad the PSF to match this image
            PSF.resample(self.data.shape)
            PSF.center_max() # shift max to center

        ## FFT
        data_k = np.fft.fftshift( # shift so DC is in the center rather than in the corner
                    np.fft.fft2( # 2D fft
                        self.data
                        )
                    )
        if PSF is not None:
            PSF_k = np.fft.fftshift( # DC to center
                        np.fft.fft2( # 2D fft
                            np.fft.fftshift( # max to corner
                                PSF.data
                                    )
                                )
                            )
        else:
            PSF_k = 1

        kx = np.linspace(-np.pi/self.dx, np.pi/self.dx, self.Nx, endpoint=False)
        ky = np.linspace(-np.pi/self.dy, np.pi/self.dy, self.Ny, endpoint=False)
        Kx, Ky = np.meshgrid(kx,ky)
        K = np.sqrt(Kx**2+Ky**2)

        H = hanning_2D(kx,ky, 1.4, 1.2)

        jx = -2*1j*Ky*np.exp(K*z)*data_k*H/(mu_0*K*PSF_k)
        jy = 2*1j*Kx*np.exp(K*z)*data_k*H/(mu_0*K*PSF_k)

        #Replace diverging elements
        jx[K==0] = -2*1j*data_k[K==0]/mu_0
        jy[K==0] = 2*1j*data_k[K==0]/mu_0

        if PSF is not None:
            jx[PSF_k==0] = 0
            jy[PSF_k==0] = 0

        ## Inverse Fourier transform
        jx = np.fft.ifft2(
                np.fft.ifftshift( ## FFT or IFFT?
                    jx
                )
            )
        jy = np.fft.ifft2(
                np.fft.ifftshift( ## FFT or IFFT?
                    jy
                )
            )

        x = int(self.Nx/4)
        y = int(self.Ny/4)

        jx = jx[y:-y, x:-x]
        jy = jy[y:-y, x:-x]

        self.jx, self.jy = jx.real, jy.real

    def pad(self, lr = None, ud=None, mode='linear_ramp'):
        '''
        input:
            lr, ud: how many pixels added to (left, right) and (up, down)
                e.g. lr = (50,60) pads 50 to the left, 60 to the right
                or   lr = 50 pads symmetrically
            mode: type of fading. see np.pad documentation
        fades the boundary of the image to zero over the pixels added
        Default will pad by half the image size resulting in an image twice as
        large as the original
        Final image size Ny+2*py, Nx+2*px
        '''
        if lr is None:
            lr = int(self.Nx/2)
        if ud is None:
            ud = int(self.Ny/2)
        if type(lr) is int:
            lr = (lr, lr)
        if type(ud) is int:
            ud = (ud, ud)

        self.data = np.pad(self.data, (ud, lr), mode=mode)

    def pad_to_match(self, image):
        '''
        Pad this image to match the real dimensions of another image
        '''
        if image.Lx < self.Lx or image.Ly < self.Ly:
            raise Exception('Can\'t match an image smaller than the current one!')
        lr = int((image.Lx - self.Lx)/self.dx/2) # difference between sizes divided by pixel size gives number of pixels
        ud = int((image.Ly - self.Ly)/self.dy/2)
        self.pad(lr, ud, mode='constant')

    def plot(self, ax=None, var='data'):
        '''
        Set var = 'jx', 'jy' to plot current
        '''
        self.ax = ax
        if ax is None:
            fig, self.ax = plt.subplots()
        im = self.ax.imshow(getattr(self, var), cmap='cubehelix',
                            extent=(0,self.Lx, 0, self.Ly), origin='lower'
                        )
        plt.colorbar(im)

    def resample(self, num_pixels_new):
        '''
        Change the pixel size to give a different number of pixels but maintain the same real size of the image
        '''
        assert type(num_pixels_new[0]) is int
        assert type(num_pixels_new[1]) is int

        # Set up interpolation function
        x = np.arange(self.Nx)
        y = np.arange(self.Ny)
        f = interp2d(x, y, self.data, kind='cubic')

        # Calculate new pixel size
        self.Ny, self.Nx = num_pixels_new
        self.Lx, self.Ly = self._Lx, self._Ly # force recalculation of dx and dy

        # Get new image
        x = np.linspace(0, x.max(), self.Nx)
        y = np.linspace(0, y.max(), self.Ny)
        self.data = f(x, y)

#         self.data = scipy.misc.imresize(self.data, num_pixels_new, interp='cubic')
        # Don't use imresize; converts the image to 8-bit

#         self.data = ndimage.zoom(self.data, zoom)
        # Also don't use zoom. It gave seemingly right but wrong results.


    def resize(self, size_new):
        '''
        Change the real image size. Useful if scaling or converting units
        '''
        self.Lx, self.Ly = size_new

    def restore(self):
        '''
        Restore original image data
        '''
        self.data = self.data_original
        self.dx = self._dx_original
        self.dy = self._dy_original

    def scale(self, factor):
        '''
        Scale the real image size by a multiplicative factor.
        '''
        self.Lx *= factor
        self.Ly *= factor

    def unpad(self):
        '''
        Crops a processed image symmetrically to the size of the original.
        '''
        self.data = self.data[round(self.Ny/4):round(-self.Ny/4), round(self.Nx/4):round(-self.Nx/4)]
        try:
            self.jx = self.jx[round(self.Ny/4):round(-self.Ny/4), round(self.Nx/4):round(-self.Nx/4)]
            self.jy = self.jy[round(self.Ny/4):round(-self.Ny/4), round(self.Nx/4):round(-self.Nx/4)]
        except:
            'jx and jy not defined yet! Cannot unpad something that doesn\'t exist!'


def match_PSF_to_image(PSF, image):
    '''
    Takes a PSF, centers it, and changes the number of pixels to match a given image.
    '''
    pos_max = np.unravel_index(np.argmax(PSF), PSF.shape)

    return PSF

def hanning_2D(x, y, xmax, ymax):
    '''
    Creates a Hanning window as a 2D matrix.
    Multiply this window to a matrix in Fourier space to filter out high-frequency components.
    x, y: 1D arrays
    xmax, ymax: cutoffs
    '''
    X, Y = np.meshgrid(x, y)
    R = np.sqrt(X**2/xmax**2 + Y**2/ymax**2)
    H = np.sqrt(1+np.cos(np.pi*R))
    H[R > 1] = 0 # outside the cutoff of one period of the filter
    return H

if __name__ == '__main__':
    ## Load data
    data_dir = './sample_data_matlab'
    data_file = os.path.join(data_dir,'im_HgTe_Inv_g_n1_061112_0447.mat')
    data = loadmat(data_file)
    flux_data = data['scans']['forward'][0][0][::-1, :, 2]
    Vx, Vy = data['range'][0]
    bendy, bendx = 15.6, 14.5 # bender constants in um per V from DAQ
    Dx, Dy = bendx*Vx, bendy*Vy # size of image in microns

    flux = Image(flux_data, real_size=(Dx, Dy))

    ## Load PSF
    PSF_file = os.path.join(data_dir,'scan604_kernel.mat')
    PSF_all = loadmat(PSF_file)
    PSF_data = PSF_all['kernel_structure']['Kernel'][0][0].real
    PSF_data = np.flipud(PSF_data)
    PSF_dx = PSF_all['kernel_structure']['dx'][0][0][0][0]
    PSF_dy = PSF_all['kernel_structure']['dy'][0][0][0][0]

    PSF = Image(PSF_data, pixel_size = (PSF_dx, PSF_dy))

    ## Plot
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(8,8))
    flux.plot(ax1)
    ax1.set_title("original flux")
    PSF.plot(ax2)
    ax2.set_title('PSF')
    plt.show()

    ## Check padding
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(8,8))
    flux.plot(ax1)
    ax1.set_title("original flux")
    flux.pad()
    flux.plot(ax2)
    ax2.set_title('padded')
    plt.show()

    ## Do current reconstruction
    PSF.restore()
    flux.restore()
    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(8,8))
    flux.plot(ax1)
    ax1.set_title("original flux")
    flux.invert_current(PSF)
    flux.plot(ax2, 'jx')
    ax2.set_title('current inversion')
    plt.show()
