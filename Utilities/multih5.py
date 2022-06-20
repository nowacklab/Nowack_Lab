import h5py as h5
from contextlib import ExitStack
from Nowack_Lab.Utilities.datasaver import Saver

# Welcome to the hall of black magic. We hope you enjoy your stay.

class File():
    '''
    Wrapper for h5 and datasaver that allows logical access to several
    duplicate h5 files in one interface.
    '''
    def __init__(self, name='', *args, **kwargs):
        super().__setattr__('filenames', [d.filename
            for d in Saver(name).datasets.values()])
        files = []
        with ExitStack() as cm:
            for f in self.filenames:
                files.append(cm.enter_context(h5.File(f, *args, **kwargs)))
            cm.pop_all()
        super().__setattr__('', files)

    def wrapcallable(xs):
        if callable(xs[0]):
            return lambda *args, **kwargs: [x(*args, **kwargs) for x in xs]
        else:
            return xs

    def __getattr__(self, attr, *args, **kwargs):
        attrs = [x.__getattribute__(attr, *args, **kwargs)
                for x in super().__getattribute__('')]
        return wrapcallable(attrs)

    def __getitem__(self, item, *args, **kwargs):
        items = [x.__getitem__(item, *args, **kwargs)
                for x in super().__getattribute__('')]
        return wrapcallable(items)

    def __setattr__(self, attr, *args, **kwargs):
        for x in super().__getattribute__(''):
            setattr(x, attr, *args, **kwargs)

    def __setitem__(self, item, *args, **kwargs):
        for x in super().__getattribute__(''):
            x.__setitem__(item, *args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.__getattribute__('close')()

    def close(self):
        for x in super().__getattribute__(''):
            x.close()


