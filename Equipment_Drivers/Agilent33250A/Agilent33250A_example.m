% testing agilent33250A
% works as of 15 09 16

fgen = Agilent33250A('Z:/home/david/codetest/datatrash');

fgen.outputz(50);
fgen.applywave('SIN', 2000, 1, 0);
fgen.delete();