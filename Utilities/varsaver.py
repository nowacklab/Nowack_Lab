import dill
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
        try:
            with open('temptestfile.pkl', 'wb') as outfile:
                dill.dump(item, outfile)
            dictofvars[name] = item
        except:
            pass
print(dictofvars)
with open(filename, 'wb') as outfile:
    dill.dump(dictofvars, outfile)
