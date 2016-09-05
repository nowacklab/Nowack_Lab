'''
For random utilities
'''
import json, numpy as np

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


def reject_outliers(data, radius=[None,None], m=2):
    '''
    Rejects outliers from a 2D numpy array (`data`).
    Looks at each point in the array and sees whether it
    is an outlier compared to data in the vicinity.
    `radius` sets the averaging area, it is an array with number of indices in either direction.
    If `radius` is left as None, will use 1/5 of the total size of the array in each dimension.
    `m` is the number of standard deviations we have to stay close to the mean.
    Higher `m` means less stringent.
    '''
    new_data = np.copy(data)

    # Set a radius if None
    radius = [int(shape/5) for shape in new_data.shape]

    for x, y in np.ndindex(data.shape):
        # Set the indices for the area we will average
        xl = x-radius[0] if x-radius[0] > 0 else 0
        xu = x+radius[0]+1
        yl = y-radius[1] if y-radius[1] > 0 else 0
        yu = y+radius[1]+1

        avg_area = data[xl:xu, yl:yu]

        d = data[x,y]
        if not abs(d - np.mean(avg_area)) < m * np.std(avg_area):
            new_data[x,y] = np.nan
    return new_data
