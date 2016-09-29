from .Procedures import *
from .Instruments import *
from .Utilities import *

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True}) # will avoid axis labels getting cut off
del rcParams

import warnings
warnings.filterwarnings("ignore") # This was to hide nanmin warnings, maybe not so good to have in general.
del warnings
