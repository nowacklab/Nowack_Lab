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


def get_browser_height():
    '''
    THIS DOESN'T WORK RELIABLY
    Get the height of the current notebook browser window (in pixels).
    Doesn't actually return anything,
    but the value of the height will be stored in the variable "height".
    '''
    from IPython.core.display import Javascript, display
    display(Javascript("""function getHeight() {
      if (self.innerHeight) {
        return self.innerHeight;
      }

      if (document.documentElement && document.documentElement.clientHeight) {
        return document.documentElement.clientHeight;
      }

      if (document.body) {
        return document.body.clientHeight;
      }
    }
    IPython.notebook.kernel.execute('height = '+getHeight())"""))


def get_browser_width():
    '''
    THIS DOESN'T WORK RELIABLY
    Get the width of the current notebook browser window (in pixels).
    Doesn't actually return anything,
    but the value of the width will be stored in the variable "width".
    '''
    from IPython.core.display import Javascript, display
    display(Javascript("""function getWidth() {
      if (self.innerWidth) {
        return self.innerWidth;
      }

      if (document.documentElement && document.documentElement.clientWidth) {
        return document.documentElement.clientWidth;
      }

      if (document.body) {
        return document.body.clientWidth;
      }
    }
    IPython.notebook.kernel.execute('width = '+getWidth())"""))
