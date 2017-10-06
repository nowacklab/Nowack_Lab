import json
import numpy as np
from IPython import get_ipython
ipython = get_ipython()

filename = sys.argv[1]
vars = ipython.magic('who_ls')
localvars = locals()
dictofvars = {}
for name in vars:
    if not name in ['outfile','vars', 'dictofvars','item','localvars']:
        item = localvars[name]
        if isinstance(item, (str,int,float,list,dict)):
            dictofvars[name] = item
        if isinstance(item, np.ndarray):
            dictofvars[name] = item.tolist()
with open(filename, 'w') as outfile:
    json.dump(dictofvars, outfile)
