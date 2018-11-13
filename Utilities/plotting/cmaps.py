from matplotlib.colors import LinearSegmentedColormap as LSC
import numpy as np

color_dict = dict(
    blue = (0.230, 0.299, 0.754),
    red = (0.706, 0.016, 0.150),
    purple = (0.436, 0.308, 0.631),
    orange = (0.759, 0.334, 0.046),
    green = (0.085, 0.532, 0.201),
    blue2 = (0.217, 0.525, 0.910),
    tan = (0.677, 0.492, 0.093),
    red2 = (0.758, 0.214, 0.233),
    grey = '#7F7F7F'
)


def diverging(color1, color2, centercolor=(.865, .865, .865)):
    '''
    Creates a diverging LinearSegmentedColormap from color1 to centercolor to color2.
    All colors specified as RGB tuples.
    centercolor can be 'w' or 'k' as well for white and black, or an integer grey value.
    By default it's a convenient grey of 0.865
    '''
    if centercolor == 'w':
        centercolor = (1,1,1)
    elif centercolor == 'k':
        centercolor = (0,0,0)
    elif type(centercolor) is float:
        centercolor = (centercolor,)*3

    colors = [color1, centercolor, color2]
    cmap = LSC.from_list('cmap', colors, N=10000)
    return cmap

PurpleOrange = diverging(color_dict['purple'], color_dict['orange'])
GreenPurple = diverging(color_dict['green'], color_dict['purple'])
BlueTan = diverging(color_dict['blue2'], color_dict['tan'])
TanOrange = diverging(color_dict['tan'], color_dict['orange'])
GreenRed = diverging(color_dict['green'], color_dict['red2'])
GreenOrange = diverging(color_dict['green'], color_dict['orange'])
BlueOrange = diverging(color_dict['blue2'], color_dict['orange'], 0.75)

# From list
_iridescent = ['#FEFEB9', '#FCF7D5', '#F5F3C1', '#EAF0B5', '#DDECBF', '#D0E7CA',
 '#C2E3D2', '#B5DDD8', '#A8D8DC', '#9BD2E1', '#8DCBE4', '#81C4E7', '#788CE7',
 '#7EB2E4', '#88A5DD', '#9398D2','#9B8AC4', '#9D7DB2', '#9A709E', '#906388',
  '#805770', '#684957','#46353A']
Iridescent = LSC.from_list('Iridescent', _iridescent)

# Sequences
sns_colorblind = [(0.0, 0.4470588235294118, 0.6980392156862745),
 (0.0, 0.6196078431372549, 0.45098039215686275),
 (0.8352941176470589, 0.3686274509803922, 0.0),
 (0.8, 0.4745098039215686, 0.6549019607843137),
 (0.9411764705882353, 0.8941176470588236, 0.25882352941176473),
 (0.33725490196078434, 0.7058823529411765, 0.9137254901960784),
 ]*3 # allow for some repetition

sns_muted = [(0.2823529411764706, 0.47058823529411764, 0.8117647058823529),
 (0.41568627450980394, 0.8, 0.396078431372549),
 (0.8392156862745098, 0.37254901960784315, 0.37254901960784315),
 (0.7058823529411765, 0.48627450980392156, 0.7803921568627451),
 (0.7686274509803922, 0.6784313725490196, 0.4),
 (0.4666666666666667, 0.7450980392156863, 0.8588235294117647)
 ]*3

sns_deep = [(0.2980392156862745, 0.4470588235294118, 0.6901960784313725),
 (0.3333333333333333, 0.6588235294117647, 0.40784313725490196),
 (0.7686274509803922, 0.3058823529411765, 0.3215686274509804),
 (0.5058823529411764, 0.4470588235294118, 0.6980392156862745),
 (0.8, 0.7254901960784313, 0.4549019607843137),
 (0.39215686274509803, 0.7098039215686275, 0.803921568627451),
 ]*3
