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
    if not name in ['outfile', 'filename','vars', 'dictofvars','item',
                    'localvars', 'thingdonotuse', 'datadonotuse']:
        item = localvars[name]
        if isinstance(item, (str,int,float,list,dict, np.ndarray)):
            dictofvars[name] = item
            print(name)
with open(filename, 'wb') as outfile:
    dill.dump(dictofvars, outfile)
