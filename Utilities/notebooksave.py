import sys
from IPython import get_ipython
thismodule = sys.modules[__name__]
ipython = get_ipython()

class nbsave():

    def sv(self, filename):
         ipython.magic('run -i C:\\Users\PHIL\\Documents'
        + '\\GitHub\\Nowack_Lab\\Utilities\\varsaver.py %s' % filename)
         return filename
    def lv(self, filename):
         ipython.magic('run -i C:\\Users\PHIL\\Documents'
        + '\\GitHub\\Nowack_Lab\\Utilities\\varloader.py %s' % filename)
