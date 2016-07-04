from saver import Saver;
from daqclass import DAQ;
from attoclass import Atto;
from sweepclass import Sweep;

import importtest as it

#class DAQ(Saver):
#    def __init__(self):
#        # call super's constructor
#        super(DAQ, self).__init__();
#        self.a=1;
#        self.b=2;
#        self.attox = 0;
#        self.attoy = 0;
#        self.attoz = 0;

#class Atto(Saver):
#    def __init__(self, direction):
#        super(Atto, self).__init__();
#        self.c = direction;
#
#class Sweep(Saver):
#    def __init__(self):
#        super(Sweep, self).__init__();
#        self.attox = 0;
#        self.attoy = 0;
#        self.attoz = 0;
#        self.daq   = 0;

daq = DAQ();

attox = Atto('x');
attoy = Atto('y');
attoz = Atto('z');

sweep = Sweep();

daq.attox = attox;
daq.attoy = attoy;
daq.attoz = attoz;

sweep.attox = attox;
sweep.attoy = attoy;
sweep.attoz = attoz;
sweep.daq   = daq;

i = it.Foo();

print(daq.__class__);
print(daq.__class__.__name__);
print(i.__class__);
print(i.__class__.__name__);



print('\n[dict2, objlist2] = attox.todict([])');
[dict2, objlist2] = attox.todict([]);
print('dict2: \n' + str(Saver.tocommentjson(dict2)));
print('objlist2: ' + str(objlist2));

print('\n[dict3, objlist3] = attoy.todict([])');
[dict3, objlist3] = attoy.todict([]);
print('dict3: \n' + str(Saver.tocommentjson(dict3)));
print('objlist3: ' + str(objlist3));

print('\n[dict4, objlist4] = attoz.todict([])');
[dict4, objlist4] = attoz.todict([]);
print('dict4: \n' + str(Saver.tocommentjson(dict4)));
print('objlist4: ' + str(objlist4));

print('\n[dict1, objlist1] = daq.todict([])');
[dict1, objlist1] = daq.todict([]);
print('dict1: \n' + str(Saver.tocommentjson(dict1)));
print('objlist1: ' + str(objlist1));

print('\n[dict5, objlist5] = sweep.todict([])');
[dict5, objlist5] = sweep.todict([]);
print('dict5: \n' + str(Saver.tocommentjson(dict5)));
print('objlist5: ' + str(objlist5));

print('\n\nDeleting all, Trying to reconstruct');

del(daq);
del(attox);
del(attoy);
del(attoz);
del(sweep);

sweep_reborn = Sweep();
#print(dict5)
[oldobjdict, missing] = sweep_reborn.linkingload(dict5,{},{});

print("\nprint(sweep_reborn.daq.attox.c);")
print(sweep_reborn.daq.attox.c);
print('\n');

print('\n[oldobjdict, missing] = sweep_reborn.linkingload(dict5,{},{})');
print('oldobjdict: \n' + str(oldobjdict));
print('missing: \n' + str(missing));
print('\n[dict6, objlist6] = sweep_reborn.todict([])');
[dict6, objlist6] = sweep_reborn.todict([]);
print('dict6: \n' + str(Saver.tocommentjson(dict6)));
print('objlist6: ' + str(objlist6));

with open('savertester_dict5.testfile', 'w') as f:
    f.write(str(Saver.tocommentjson(dict5)));
with open('savertester_dict6.testfile', 'w') as f:
    f.write(str(Saver.tocommentjson(dict6)));


