
# from .Procedures import *
# from .Instruments import *
# #from . import *
__all__ = ['Procedures', 'Instruments']

# import pkgutil
# # for loader, module_name, is_pkg in  pkgutil.walk_packages(__path__):
    # # __all__.append(module_name)
    # # print(module_name)
    # # module = loader.find_module(module_name).load_module(module_name)
    # # exec('%s = module' % module_name)
    # # print(module_name)

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True}) # will avoid axis labels getting cut off