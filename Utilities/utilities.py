'''
For random utilities
'''
import json, numpy as np, os
from numpy.linalg import lstsq

class AttrDict(dict):
    '''
    Class that behaves exactly like a dict, except that you can access values as
    if the keys were attributes of the dictionary class. For example:
        >> d = AttrDict(a = 1, b = 2, c = 3)
        >> d['a'] == d.a
        True
    This is useful in an interactive console so that you can easily see all
    attributes of a value of the dictionary by typing "d." and pressing tab.

    Idea from http://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute-in-python
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self


def fit_plane(x,y,z):
    '''
    Calculates plane parameters a, b, and c for 2D data.
    z = ax + by + c
    '''
    X = x.flatten()
    Y = y.flatten()
    Z = z.copy()
    Z = Z.flatten()

    if type(X) is np.ma.MaskedArray: # used when doing edges only
        if np.ma.is_masked(X):
            mask = X.mask.copy() # mask will be different after next line!
            X = X[np.invert(mask)] # removes masked values
            Y = Y[np.invert(mask)] # removes masked values
            Z = Z[np.invert(mask)] # use X mask in case reject outliers modified mask

    if type(Z) is np.ma.MaskedArray: # from rejected outliers:
        if np.ma.is_masked(Z):
            mask = Z.mask.copy()
            X = X[np.invert(mask)]
            Y = Y[np.invert(mask)]
            Z = Z[np.invert(mask)]


    A = np.vstack([X, Y, np.ones(len(X))]).T
    return lstsq(A, Z)[0] # a,b,c


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


def get_computer_name():
    '''
    Gets the computer's name. Should hopefully be unique!
    '''
    return os.uname()[1]


def get_nb_kernel():
    '''
    Returns a string with the kernel key for unique identification of a kernel.
    '''
    from ipykernel import get_connection_info
    k = get_connection_info()
    k_dict = json.loads(k)
    return k_dict['key']


def get_superclasses(obj):
    '''
    Get a tuple of names of all superclasses of an object.
    '''
    return [c.__name__ for c in obj.__class__.__mro__]


def nanmin(data):
    result = np.nanmin(data)
    return result if not np.isnan(result) else 0


def nanmax(data):
    result = np.nanmax(data)
    return result if not np.isnan(result) else 0


def reject_outliers(data, radius=[None,None], m=2):
    '''
    Rejects outliers from a 2D numpy array (`data`).
    Looks at each point in the array and sees whether it
    is an outlier compared to data in the vicinity.
    `radius` sets the averaging area, it is an array with number of indices in either direction.
    If `radius` is left as None, will use 1/5 of the total size of the array in each dimension.
    `m` is the number of standard deviations we have to stay close to the mean.
    Higher `m` means less stringent.
    This takes a long time... might just want to do this occasionally.
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
        if not abs(d - np.nanmean(avg_area)) < m * np.nanstd(avg_area):
            new_data[x,y] = np.nan
    return new_data


def reject_outliers_plane(z, m=2):
    '''
    Reject outliers from 2D data that lies mainly on a plane.
    '''
    x = np.array(range(z.shape[1])) # xy indexing!!!
    y = np.array(range(z.shape[0]))
    X, Y = np.meshgrid(x,y)

    a,b,c = fit_plane(X,Y,z)
    Zplane = a*X + b*Y + c
    Zdiff = z - Zplane

    mean =  np.nanmean(Zdiff)
    std = np.nanstd(Zdiff)
    Z_no_outliers = np.ma.masked_where(abs(Zdiff - mean) > m*std, Zdiff)

    return Z_no_outliers + Zplane # this should be original data with outliers removed, considering that the data lie on a plane


def reject_outliers_quick(data, m=2):
    '''
    Quicker way to reject outlier using a masked array
    '''
    mean =  np.nanmean(data)
    std = np.nanstd(data)
    new_data = np.ma.masked_where(abs(data - mean) > m*std, data)
    return new_data


def hide_code_button():
    '''
    Generates an HTML button that toggles on and off the code cells in the notebook.
    '''
    from IPython.display import HTML

    HTML('''<script>
    code_show=true;
    function code_toggle() {
     if (code_show){
     $('div.input').hide();
     } else {
     $('div.input').show();
     }
     code_show = !code_show
    }
    $( document ).ready(code_toggle);
    </script>
    <form action="javascript:code_toggle()"><input type="submit" value="Click here to toggle on/off the raw code."></form>''')
