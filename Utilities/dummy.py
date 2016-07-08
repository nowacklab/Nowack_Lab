class Dummy():
    '''
    Dummy class. You can replace any object with a Dummy object, and then any functions or variables in that class will do absolutely nothing.
    This is useful, for example, if you want to run a procedure without actually using any instruments. 
    Could be useful for debugging or replotting data.
    '''
    def __init__(self, *args, **kwargs):
        pass
    def dumb(self, *args, **kwargs):
        pass
    def __getattr__(self, _):
        return self.dumb