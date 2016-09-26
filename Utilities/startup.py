## Importing commonly used packages
import numpy as np
import matplotlib.pyplot as plt
from imp import reload
from Nowack_Lab import *
from IPython import get_ipython
from time import sleep
import sys, os

## For interactive matplotlib plots
get_ipython().magic('matplotlib notebook')

del get_ipython # don't need this in the namespace
