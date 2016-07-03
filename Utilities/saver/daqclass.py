from saver import Saver;

class DAQ(Saver):
    def __init__(self):
        # call super's constructor
        super(DAQ, self).__init__();
        self.a=1;
        self.b=2;
        self.attox = 0;
        self.attoy = 0;
        self.attoz = 0;
