import Nowack_Lab

def make_instruments(*args):
    instruments = {}
    for arg in args:
        for module_name in Nowack_Lab.Utilities.__all__:
            try:
                if arg.__module__.find(module_name) != -1:
                    instruments[module_name] = arg
            except:
                pass

    return instruments