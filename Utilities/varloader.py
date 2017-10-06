import json
import sys
thismodule = sys.modules[__name__]
ipython = get_ipython()

filename = sys.argv[1]
with open(filename,"r") as infile:
    data = json.load(infile)
for thing in data:
    setattr(thismodule, thing, data[thing])
