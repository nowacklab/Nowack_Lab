from saver import Saver

class Atto(Saver):
    def __init__(self, direction='x'):
        super(Atto, self).__init__();
        self.c = direction;
