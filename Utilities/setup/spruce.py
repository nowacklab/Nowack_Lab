r"""
Template setup file for handling imports.
Modify for each computer as you see appropriate.
Run using get_ipython().magic('run %s' %setup_path)
to import directly into the IPython Kernel.
"""

import os

from IPython import get_ipython
ip = get_ipython()

here = os.path.dirname(__file__)
path = os.path.join(here, 'template.py')

ip.magic('run %s' %path)
