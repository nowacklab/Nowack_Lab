import h5py as h5
from contextlib import ExitStack
from Nowack_Lab.Utilities.datasaver import Saver

class Files():
    '''
    Convenient multiple-file context manager for saving data files.
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

    def __enter__(self):
        return super().__getattribute__('')

    def __exit__(self, type, value, traceback):
        self.__getattribute__('close')()
        return self.filenames

    def close(self):
        for x in super().__getattribute__(''):
            x.close()


