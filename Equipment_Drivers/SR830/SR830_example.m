%% Testing the SR830 drivers 
% author: david low (dhl88)
% change log:
%   2015 08 25: Wrote test cases, found bug that requires
%               2 separate quarries to guarentee SENS functions.
%               I would expect this to be the same for all 
%               quarries!!!!!!!!!!
close all
clear all

amp = SR830();
amp.getparams();
amp.par.sensitivity
amp.sensitivity(9);
amp.par
fprintf('manualON\n');
fprintf(amp.visa, 'SENS?');
fscanf(amp.visa)
fprintf(amp.visa, 'SENS 1');
fprintf(amp.visa, 'SENS?');
one = fscanf(amp.visa)
%pause(1)
fprintf(amp.visa, 'SENS?');
one = fscanf(amp.visa)
pause(1)
fprintf(amp.visa, 'SENS 2');
fprintf(amp.visa, 'SENS?');
two = fscanf(amp.visa)
fprintf(amp.visa, 'SENS?');
two = fscanf(amp.visa)
pause(1)
fprintf(amp.visa, 'SENS 9');
pause(10)
fprintf(amp.visa, 'SENS?');
nine = fscanf(amp.visa)
fprintf(amp.visa, 'SENS?');
nine = fscanf(amp.visa)

fprintf(amp.visa, 'SENS 15');
fprintf(amp.visa, 'SENS?;\n;\n');
fifteen = fscanf(amp.visa)
fprintf(amp.visa, 'SENS?');
fifteen = fscanf(amp.visa)

fprintf(amp.visa, 'SENS 5');
fprintf(amp.visa, 'SENS?');
fprintf(amp.visa, 'SENS?');
five = fscanf(amp.visa)


%amp.snapshot()
amp.delete();