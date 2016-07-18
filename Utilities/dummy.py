class Dummy():
    '''
    Make a dummy object with Dummy(Class). You can replace any object of class Class with a Dummy object, and then any functions or variables in that class will do absolutely nothing.
    This is useful, for example, if you want to run a procedure without actually using any instruments.
    Expected uses: debugging or replotting data.
    '''
    def __init__(self, Class):
        '''
        Class is the class that you want to dummify.
        '''
        self.Class = Class
        self.num_returns = None

    def dumb(self, *args, **kwargs):
        '''
        Dumb function that returns Nones based on how many expected returns a function has
        '''
        if self.num_returns == 0:
            pass
        if self.num_returns == 1:
            return None
        else:
            return (None,)*self.num_returns

    def __getattr__(self, attr):
        '''
        Overwrites __getattr__ so that when a method is called, it instead uses the "dumb" function which just returns Nones.
        '''
        try:
            self.num_returns = getattr(self.Class, attr).__code__.co_stacksize
        except:
            return None
        return self.dumb
