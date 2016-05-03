class Goto():
    
    def __init__(self, piezos):
        self._piezos = piezos
        
    def check_range(self, x, y, z):
        for i in ['x','y','z']:
            if abs(eval(i)) > self._piezos.Vmax[i]:
                raise Exception('Out of range! Max voltage for %s piezo is %f V' %(i, self._piezos.Vmax[i]))
        
    def goto_seq(self, x, y, z):
        """ Sequential goto: in case we want to move z out of the way first """
        if x == None:
            x = self._piezos.V['x']
        if y == None:
            y = self._piezos.V['y']
        if z == None:
            z = self._piezos.V['z']
        self.check_range(x,y,z)
        
        order = ['x','y','z']
        if z < self._piezos.V['z']:
            order = ['z','y','x'] #if z is retracting, let it go first

        for i in order:
            self._piezos.V = {i: eval(i)}
                
    def goto(self, x, y, z):
        if x == None:
            x = self._piezos.V['x']
        if y == None:
            y = self._piezos.V['y']
        if z == None:
            z = self._piezos.V['z']
        self.check_range(x,y,z)
        self._piezos.V = {'x': x, 'y': y, 'z': z}
              
    def zero(self):
        self.goto(0,0,0)