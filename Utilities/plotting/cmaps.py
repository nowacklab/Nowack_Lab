from matplotlib.colors import LinearSegmentedColormap as LSC
import numpy as np

colors = dict(
    blue = (0.230, 0.299, 0.754),
    red = (0.706, 0.016, 0.150),
    purple = (0.436, 0.308, 0.631),
    orange = (0.759, 0.334, 0.046),
    green = (0.085, 0.532, 0.201),
    blue2 = (0.217, 0.525, 0.910),
    tan = (0.677, 0.492, 0.093),
    red2 = (0.758, 0.214, 0.233)
)


def diverging(color1, color2, centercolor=(.865, .865, .865)):
    '''
    Creates a diverging LinearSegmentedColormap from color1 to centercolor to color2.
    All colors specified as RGB tuples.
    centercolor can be 'w' or 'k' as well for white and black. By default it's a convenient grey.
    '''
    if centercolor == 'w':
        centercolor = (1,1,1)
    elif centercolor == 'k':
        centercolor = (0,0,0)

    colors = [color1, centercolor, color2]
    cmap = LSC.from_list('cmap', colors, N=10000)
    return cmap

PurpleOrange = diverging(colors['purple'], colors['orange'])
GreenPurple = diverging(colors['green'], colors['purple'])
BlueTan = diverging(colors['blue2'], colors['tan'])
GreenRed = diverging(colors['green'], colors['red2'])
