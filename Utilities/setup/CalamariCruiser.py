"""
Template setup file for handling imports.
Modify for each computer as you see appropriate.
Any commands run here run directly in the IPython Kernel.
"""

import os

from IPython import get_ipython
ip = get_ipython()

here = os.path.dirname(__file__)
path = os.path.join(here, 'template.py')

ip.magic('run %s' %path)
