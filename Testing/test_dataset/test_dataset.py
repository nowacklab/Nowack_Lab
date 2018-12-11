import numpy as np
from importlib import reload
import time
import copy

import Nowack_Lab.Utilities.dataset
reload(Nowack_Lab.Utilities.dataset)
from Nowack_Lab.Utilities.dataset import Dataset


def checker(val1,  val2):
    if type(val1) is dict or type(val2) is dict:
        return dictchecker(val1, val2)
    try:
        if val1 == val2:
            return True
    except:
        pass
    try:
        if val1 is val2:
            return True
    except:
        pass
    try:
        if np.all(val1 == val2):
            return True
    except:
        pass
    try:
        if np.all(
                    (val1 == val2) + 
                    (np.isnan(val1) == np.isnan(val2)) * 
                    (np.isnan(val1) + np.isnan(val2))
                ):
            return True
    except:
        pass

    return False

def dictchecker(dict1, dict2):
    overall = True
    for k in dict1.keys():
        try:
            overall = overall and checker(dict1[k], dict2[k])
        except:
            overall = False
    for k in dict2.keys():
        try:
            overall = overall and checker(dict1[k], dict2[k])
        except:
            overall = False

    return overall
    
dataset1 = Dataset('testset_{0:d}.hdf5'.format(int(time.time())))


# checks:
# stores ints, floats, complex
# stores lists of ints, floats, complex, 
# stores lists of ints, floats, complexes, and strings 
#   (everything converted to a string)
# stores numpy ndarray of int, float, complex
# stores numpy ndarray of int, float, complex and strings
#   (everything converted to a string)
# storing np.nan allows for appending properly
# unicode string saves ok
# all ascii characaters save ok
# dictionaries save ok
# nested dictionaries save ok
# 3 intentionally false values to test 
# object saves as string (saved the dataset1 object)

a = 1
b = 1.0
c = time.time()
d = (2j+1)*c
e = 'the quick brown fox jumps over the lazy dog'*100
f = [a,b,c,d]
g = f + [e, 'f']
h = np.random.random((10,11,12))
i = np.full( (10,11,12), np.nan)
j = np.array(g)
k = ('Falsches Üben von Xylophonmusik quält jeden größeren Zwerg' + 
  '(= Wrongful practicing of xylophone music tortures every larger dwarf)'+
  'Zwölf Boxkämpfer jagten Eva quer über den Sylter Deich'+
  '(= Twelve boxing fighters hunted Eva across the dike of Sylt)' + 
  'Heizölrückstoßabdämpfung' + 
  '(= fuel oil recoil absorber)'
  )
l = [chr(i) for i in range(127)]

y = {'a':a, 'b':b, 'c':c, 'd':d, 'e':e,
     'f':f, 'g':g, 'h':h, 'i':i, 'j':j,
     'k':k,
     'l':l}
z = {'a':a, 'b':b, 'c':c, 'd':d, 'e':e,
     'f':f, 'g':g, 'h':h, 'i':i, 'j':j,
     'k':k, 'l':l, 'y':copy.deepcopy(y)}
checks = []

dataset1.append('/a', a) 
dataset1.append('/b', b) 
dataset1.append('/c', c)
dataset1.append('/d', d)
dataset1.append('/e', e) 
dataset1.append('/f', f)
dataset1.append('/g', g)
dataset1.append('/h', h)
dataset1.append('/i', i)
dataset1.append('/j', j) 
dataset1.append('/k', k)
dataset1.append('/l', l)

dataset1.append('/y/', y)
dataset1.append('/z/', z)

checks.append((checker(dataset1.get('/a'), a),1))
checks.append((checker(dataset1.get('/b'), b),2))
checks.append((checker(dataset1.get('/c'), c),3))
checks.append((checker(dataset1.get('/d'), d),4))
checks.append((checker(dataset1.get('/e'), e),5))
checks.append((checker(dataset1.get('/f'), f),6))
checks.append((checker(dataset1.get('/g'), g),7))
checks.append((checker(dataset1.get('/h'), h),8))
checks.append((checker(dataset1.get('/i'), i),9))
checks.append((checker(dataset1.get('/j'), j),10))
checks.append((checker(dataset1.get('/k'), k),11))
checks.append((checker(dataset1.get('/l'), l),12))
checks.append((checker(dataset1.get('/y'), y),13))
checks.append((checker(dataset1.get('/y/a'), a),14))
checks.append((checker(dataset1.get('/y/b'), b),15))
checks.append((checker(dataset1.get('/y/c'), c),16))
checks.append((checker(dataset1.get('/y/d'), d),17))
checks.append((checker(dataset1.get('/y/e'), e),18))
checks.append((checker(dataset1.get('/y/f'), f),19))
checks.append((checker(dataset1.get('/y/g'), g),20))
checks.append((checker(dataset1.get('/y/h'), h),21))
checks.append((checker(dataset1.get('/y/i'), i),22))
checks.append((checker(dataset1.get('/y/j'), j),23))
checks.append((checker(dataset1.get('/y/k'), k),24))
checks.append((checker(dataset1.get('/y/l'), l),25))
checks.append((checker(dataset1.get('/z'), z),26))
checks.append((checker(dataset1.get('/z/y'), y),27))

i[1,:,2] = np.random.random(11)
dataset1.append('/i', i[1,:,2], slc=(1,slice(11),2))
checks.append((checker(dataset1.get('/i'), i),28))

dataset1.append('/y/i', i[1,:,2], slc=(1,slice(11),2))
checks.append((checker(dataset1.get('/y/i'), i),29))

dataset1.append('/z/y/i', i[1,:,2], slc=(1,slice(11),2))
checks.append((checker(dataset1.get('/z/y/i'), i),30))

# making sure I can see a wrong value
z['y']['h'][3,2,1] = 1
checks.append((not checker(dataset1.get('/z'), z),31))
checks.append((checker(dataset1.get('/y'), y), 32))
y['newval'] = 1
checks.append((not checker(dataset1.get('/y'), y),33))

z['y']['dataset'] = dataset1
dataset1.append('/z_/', z)
checks.append((not checker(dataset1.get('/z_'), z),34))
z['y']['dataset'] = str(dataset1)
checks.append((checker(dataset1.get('/z_'), z),35))


# dimension testing, do it manually
dataset1.append('/h_dim0/', np.linspace(0,2,10))
dataset1.append('/h_dim1/', np.linspace(-10,.1,11))
dataset1.append('/h_dim2/', ['a','b','c','d','e','f',
                            'g','h','i','j','k','l'])
dataset1.make_dim('/h/', 0, 'label0', '/h_dim0/', 'dim0')
dataset1.make_dim('/h/', 1, 'label1', '/h_dim1/', 'dim1')
dataset1.make_dim('/h/', 2, 'label0', '/h_dim2/', 'dim1')

dataset1.create_attr('/z/', 'lololabel', 'fred')
dataset1.create_attr('/z/', 'lololabel1', 1)
dataset1.create_attr('/z/', 'lololabel2', 1.0)
dataset1.create_attr('/z/', 'lololabel3', f)

dataset1.create_attr_dict('/z/', y, prefix='_y_')

for c in checks:
    if c[0] == False:
        print(c)
