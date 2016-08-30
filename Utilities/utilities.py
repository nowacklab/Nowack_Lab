'''
For random utilities
'''
import json

def get_nb_kernel():
    '''
    Returns a string with the kernel key for unique identification of a kernel.
    '''
    from ipykernel import get_connection_info
    k = get_connection_info()
    k_dict = json.loads(k)
    return k_dict['key']
