"""
squidimage.py

author: Katja Nowack
date: 2016-11-26

This module contains a range of functions used for processing images for current
inversion using fast Fourier transforms
"""

import numpy as np
from scipy.interpolate import interp2d

def crop(image, cx, cy):
    """
    input:
        cx, cy: how much to crop left and right and up and down
        the image will be cropped symmetrically(e.g. cx from left and cx
        from right)

    return:
        array that contains the cropped image

    TO DO:
        allow cx, cy to be 2D to enable non-symmetric cropping
        check that we are not cropping too much
    """

    #if len(arr.shape) < 2:
    image_cropped = image[cy:-cy, cx:-cx]
    return image_cropped


def pad_with_zeros(image, px = None, py = None):
    """
    input:
        px, py: how many pixels with zero added to left and right and up and
        down
        pixels will be added symmetrically (i.e. px added to left and px to right)
        Default will pad by half the image size resulting in an image twice as
        large as the original
    return:
        padded image, size Ly+2*py, Lx+2*px
    TO DO:
        allow px, py to be 2D to enable non-symmetric cropping
    """
    Ly, Lx = image.shape
    if px is None:
        px = int(round(Lx/2))
    if py is None:
        py = int(round(Ly/2))
    #add zero padding left and right
    pad_hor = np.zeros([Ly,px])
    image_padded = np.concatenate((pad_hor, image, pad_hor), axis = 1)
    #add zero padding on top and below
    pad_ver = np.zeros([py,Lx+2*px])
    image_padded = np.concatenate((pad_ver, image_padded, pad_ver), axis = 0)
    return image_padded


def pad_with_fading(image,px = None, py = None):
    """
    input:
        px, py: how many pixels added to left and right and up and
        down
        pixels will be added symmetrically(e.g. px added to left and px to right)
        fades the boundary of the image to zero over the pixels added
        Default will pad by half the image size resulting in an image twice as
        large as the original
    return:
        padded image, size Ly+2*py, Lx+2*px
    TO DO:
        allow px, py to be 2D to enable non-symmetric cropping
    """

    Ly, Lx = image.shape
    if px is None:
        px = int(round(Lx/2))
    if py is None:
        py = int(round(Ly/2))

    #add padding left and right
    pad_l = np.fliplr(np.outer(np.squeeze(image[:,0]),fade2zero(px)))
    pad_r = np.outer(np.squeeze(image[:,Lx-1]),fade2zero(px))
    image_padded = np.concatenate((pad_l, image, pad_r), axis = 1)
    #add padding on top and below
    pad_up = np.flipud(np.outer(fade2zero(py),np.squeeze(image[0,:])))
    pad_up_full = np.concatenate((np.zeros([py,px]),pad_up,np.zeros([py,px])), axis = 1)
    pad_down = np.outer(fade2zero(py),np.squeeze(image[Ly-1,:]))
    pad_down_full = np.concatenate((np.zeros([py,px]),pad_down,np.zeros([py,px])), axis = 1)
    image_padded = np.concatenate((pad_up_full, image_padded, pad_down_full), axis = 0)

    return image_padded

def center_max_on_larger_grid(image,Lx_new,Ly_new):
    """
    input:
        Lx_new, Ly_new: dimension of the new image

    return:
        image of size Lx_new, Ly_new that contains the input image with the max centered
        at the center of the new image
    TO DO:
        give error messages, if Lx_new, Ly_new are too small
        assign default to Lx_new, Ly_new
    """
    Ly, Lx = image.shape
    #first find the psoition of the maximum in the image
    pos_max = np.argmax(image)
    pos_max = np.unravel_index(pos_max,image.shape)
    # pos_max = N/2 , N/2 -> 0 = N/2-pos_max
    Ly_new_half = int(round(Ly_new/2))
    Lx_new_half = int(round(Lx_new/2))
    new_image = np.zeros([Ly_new,Lx_new])
    new_image[Ly_new_half - pos_max[0]:Ly_new_half - pos_max[0]+Ly,
    Lx_new_half - pos_max[1]:Lx_new_half - pos_max[1]+Lx] = image

    return new_image
def interpolate_on_new_grid(image,Nx_new,Ny_new):
    """
    input:
        Nx_new, Ny_new: dimension of the new image in number of pixels
    return:
        image with size Nx_new, Ny_new that contains the input image extrapolated on the new grid
        assumption is that the size of the image in real units of length (e.g. um) stays the same
    """

    Ly, Lx = image.shape
    x = np.linspace(0, Lx-1, Lx)
    y = np.linspace(0, Ly-1, Ly)
    f = interp2d(x, y, image, kind='cubic')
    xnew = np.linspace(0, Lx-1, Nx_new)
    ynew = np.linspace(0, Ly-1, Ny_new)
    image_interp = f(xnew, ynew)
    return image_interp

def fade2zero(Length):
    #advantage of defining this function is that we can easily implement to
    #extrapolate to zero in other fashions as well.
    vec = np.linspace(1,0,Length)
    return vec



def hanning_2D(kx,ky,Kmax_x,Kmax_y):
    """
    Calculates a matrix that is used to impose a Hanning window in k-space
    """
    Kmax_x2 = Kmax_x*Kmax_x
    Kmax_y2 = Kmax_y*Kmax_y
    kxx, kyy = np.meshgrid(kx,ky)
    Ke = np.sqrt(kxx*kxx/Kmax_x2+kyy*kyy/Kmax_y2)
    H=(1+np.cos(np.pi*Ke))*0.5
    H[Ke>1] =0
    return H


def BiotSavart_k(Bzk,PSF_k,kx,ky,z,Kmax_x,Kmax_y):
    """
    Calculates the Biot-Savart kernel in 2D in k-space
    """
    mu_0 = 4*np.pi*1e-7
    kxx, kyy = np.meshgrid(kx,ky)
    K_mat = np.sqrt(kxx**2+kyy**2);
    H_mat = hanning_2D(kx,ky,Kmax_x,Kmax_y);
    #d2, kx2, ky2 = d*d, kx*kx, ky*ky
    #j_x = ne.evaluate('-2*1j*ky_mat*exp(K_mat*z)*b_zk*H_mat/(mu_0*K_mat*PSF_k)')
    #j_y = ne.evaluate('2*1j*kx_mat*exp(K_mat*z)*b_zk*H_mat/(mu_0*K_mat*PSF_k)')
    j_x = -2*1j*kyy*np.exp(K_mat*z)*Bzk*H_mat/(mu_0*K_mat*PSF_k)
    j_y = 2*1j*kxx*np.exp(K_mat*z)*Bzk*H_mat/(mu_0*K_mat*PSF_k)

    #Replace diverging elements
    # if ~isempty(zero_x) && ~isempty(zero_y)
    j_x[K_mat==0]=-2*1j*Bzk[K_mat==0]/(mu_0);
    j_y[K_mat==0]=2*1j*Bzk[K_mat==0]/(mu_0);


    #if ~isempty(ind)
    j_x[PSF_k==0]=0;
    j_y[PSF_k==0]=0;

    return j_x, j_y
