from .mod2D import *
from .navigation import *
from .planefit import *
from .scanplane import *
from .squidIV import *
from .touchdown import *
from .daqspectrum import *

__all__ = ['mod2D','navigation','planefit','scanplane','squidIV','touchdown','daqspectrum']
# import pkgutil

# for loader, module_name, is_pkg in  pkgutil.walk_packages(__path__):
    # __all__.append(module_name)
    # print(module_name)
    # module = loader.find_module(module_name).load_module(module_name)
    # exec('%s = module' % module_name)
    # print(module_name)
