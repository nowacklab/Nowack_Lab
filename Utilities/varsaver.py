import dill
import numpy as np
import os
from IPython import get_ipython
ipython = get_ipython()

filename = sys.argv[1]
vars = ipython.magic('who_ls')
localvars = locals()
dictofvars = {}
for name in vars:
    if not name in ['outfile','vars', 'dictofvars','item','localvars']:
        item = localvars[name]
        try:
            with open('temptestfiledonotuse.pkl', 'wb') as outfile:
                dill.dump(item, outfile)
            dictofvars[name] = item
        except:
            pass
os.remove('temptestfiledonotuse.pkl')
with open(filename, 'wb') as outfile:
    dill.dump(dictofvars, outfile)
