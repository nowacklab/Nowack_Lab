from saver import Saver

class Sweep(Saver):
    def __init__(self):
        super(Sweep, self).__init__();
        self.attox = 0;
        self.attoy = 0;
        self.attoz = 0;
        self.daq   = 0;
