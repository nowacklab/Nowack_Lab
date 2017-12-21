import dill
import sys
thismodule = sys.modules[__name__]
ipython = get_ipython()

filename = sys.argv[1]
with open(filename,"rb") as infile:
    datadonotuse = dill.load(infile)
for thingdonotuse in datadonotuse.keys():
    setattr(thismodule, thingdonotuse, datadonotuse[thingdonotuse])
    print(thingdonotuse)
