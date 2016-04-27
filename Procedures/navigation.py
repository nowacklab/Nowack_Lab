class Goto():
    
    def __init__(self, piezo_x, piezo_y, piezo_z):
        self._x = piezo_x
        self._y = piezo_y
        self._z = piezo_z
        
    def goto(self, x, y, z):
        order = ['x','y','z']
        if z < self._z.V:
            order = ['z','y','x'] #if z is retracting, let it go first
        for i in order:
            piezo_i = getattr(self, '_%s' %i)
            if abs(eval(i)) > piezo_i.Vmax:
                raise Exception('Out of range! Max voltage for %s piezo is %f V' %(i, piezo_i.Vmax))
            else:
                piezo_i.V = eval(i)
                
    def zero(self):
        self.goto(0,0,0)