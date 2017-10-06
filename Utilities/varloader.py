import dill
import sys
thismodule = sys.modules[__name__]
ipython = get_ipython()

filename = sys.argv[1]
with open(filename,"rb") as infile:
    data = dill.load(infile)
for thing in data:
    setattr(thismodule, thing, data[thing])
