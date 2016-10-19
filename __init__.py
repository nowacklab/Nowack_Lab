## Importing commonly used packages
from IPython import get_ipython, display
ip = get_ipython()
ip.kernel.do_execute('''
import numpy as np
import matplotlib.pyplot as plt
from imp import reload
from time import sleep
import sys, os

## For interactive matplotlib plots
from IPython import get_ipython
get_ipython().magic('matplotlib notebook')
del get_ipython # don't need this in the namespace
''', silent=True)

from .Procedures import *
from .Instruments import *
from .Utilities import *

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True}) # will avoid axis labels getting cut off

import warnings
warnings.filterwarnings("ignore") # This was to hide nanmin warnings, maybe not so good to have in general.
