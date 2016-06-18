%% Initialize
clear all
close all

%% Add all paths
mainrepopath = '../';
addpath([mainrepopath, 'instrument_drivers']);
addpath([mainrepopath, 'measurement_scripts']);
addpath([mainrepopath, 'modules']);

%% Set Strings for save dir, titles, etc.
doer = 'JKN';
path = 'Z:/data/montana_b69/TuningForkChar/Raw Data/20150925/';
notes = 'canned tuning fork - around 32.76 kHz';
tunForkType = 'canned_32.7k to 32.88k_incr-freq_0.5Hz-step';
voltageSource = '_agilent-source_'; % _lockin-sineout_, _agilent-source_, etc.

%% Create NI daq and SR830 lock-in object
% doer = 'JKN';
% path = 'Z:/data/montana_b69/TuningForkChar/Raw Data/20150925/';
nidaq = NIdaq(doer, path);
%lockin = SR830(); % uncomment if using lock-in's sine out
funcgen = Agilent33250A(doer, path);

%% Set parameters to be used / saved by LoggableObj
% Add and set parameters here! not in the code! if you want more params
% add them here  All of these 'should' be saved ;)
% nidaq.p.gain       = 500;
% nidaq.p.lpf0       = 100;
% nidaq.p.mod_curr   = 70e-6;
% nidaq.p.mod_biasr   = 12e3;
nidaq.p.rate       = 100; % Hz; number of data points (input or output) passed (inward or outward) per second
nidaq.p.range      = 10; % options: 0.1, 0.2, 0.5, 1, 2, 5, 10
%nidaq.p.src_amp    = .001; % in Volts???
nidaq.p.src_numpts = 10; % number of data points to be averaged per freq val
%nidaq.p.squid_biasr  = 5e3;
%nidaq.p.T          = 9.0;
%nidaq.p.Terr       = .060;

%nidaq.notes = 'Si-loaded tuning fork, room temp cured - around 30 kHz';
nidaq.notes = notes;

% Non-savable params - set here!
kevTf = struct();
kevTf.freq_step = .5; % Hz
kevTf.freq_min = 32700; % Hz
kevTf.freq_max = 32880; % Hz
kevTf.timeConstant = 0.1; % s; lock-in time constant
kevTf.sensitivity = 0.01; % V; lock-in sensitivity (max range of input)
kevTf.expand = 1; % lock-in CH1 or 2 output voltage multiplication factor
kevTf.offset = 0; % lock-in CH1 or 2 output voltage offset
kevTf.sourceAmp = 0.01; % V; lock-in/function generator sine output amplitude
kevTf.maxCHVoltRange = 10; % V; max range of lock-in CH1 & 2 BNC outputs
kevTf.inputLockinCH1Num = 0; % DAQ input channel number for lock-in CH1 (voltage X)
kevTf.inputLockinCH2Num = 1; % DAQ input channel number for lock-in CH2 (voltage Y)
%kevTf.outputOpAmpBiasNum = 3; % DAQ output channel number for opamp power voltage < +/- 15 V.
kevTf.dummyNum = 0; % DAQ output channel number for dummy output to control when the DAQ stops sensing input.
nidaq.p.kevTf = kevTf;

% freqSetVals = linspace(kevTf.freq_min, kevTf.freq_max, (kevTf.freq_max-kevTf.freq_min)/kevTf.freq_step + 1) % might be better than the colon operator since will always include endpoints
freqSetVals = kevTf.freq_min:kevTf.freq_step:kevTf.freq_max;

%% Setup scan
nidaq.setrate(nidaq.p.rate);
nidaq.addinput_A ('Dev1', kevTf.inputLockinCH1Num, 'Voltage', nidaq.p.range, 'V-X');
nidaq.addinput_A ('Dev1', kevTf.inputLockinCH2Num, 'Voltage', nidaq.p.range, 'V-Y');
%nidaq.addoutput_A('Dev1', kevTf.outputOpAmpBiasNum, 'Voltage', nidaq.p.range, 'opAmp-Voltage');
nidaq.addoutput_A('Dev1', kevTf.dummyNum, 'Voltage', nidaq.p.range, 'dummy');

%% Setup data
desout = {zeros(1,nidaq.p.src_numpts)};%,...
          %nidaq.p.mod_curr * nidaq.p.mod_biasr *    linspace(1,1   ,nidaq.p.src_numpts)  ...
         %};
%nidaq.setoutputdata(kevTf.outputOpAmpBiasNum,desout{1}); % will be used for opAmp power voltage
nidaq.setoutputdata(kevTf.dummyNum,desout{1}); % dummy output so that DAQ keeps reading input. Outputs nidaq.p.src_numpts data points

%% Run / collect data

pause('on')
bottomFreq = 10000; % for baseline low frequency to set phase = 0 by autophase
funcgen.applywave('SIN',bottomFreq,2*kevTf.sourceAmp,0);
fprintf(['At ',num2str(bottomFreq),' Hz. Please press Autophase at lock in to set phase = 0, then press any key to continue.\n']);
pause() % PRESS AUTOPHASE AT LOW FREQ OF 100 HZ SO THAT THE PHASE IS ZERO AT LOW FREQ!
%fprintf('after initial applywave, before for loop\n')
for i = 1:length(freqSetVals)
	%lockin.setFreq(freqSetVals(i)); % uncomment this & comment below if using lock-in's sine out
    %fprintf('first line in for loop\n')
    funcgen.setFreq(freqSetVals(i)); %uncomment this & comment above if using agilent 33250A
	pause(10*kevTf.timeConstant);
	freqReadVals(i) = funcgen.getFreq();
    %fprintf('in for loop before run\n')
    [data, time] = nidaq.run(0);
	XVals(i) = (mean(data(:,1))/kevTf.maxCHVoltRange/kevTf.expand+kevTf.offset)*kevTf.sensitivity; % READS CH1, VX in Vrms, with appropriate proportionality constant, ON LOCK IN FROM DAQ. Takes the mean of nidaq.p.src_numpts data points. Takes nidaq.p.src_numpts/nidaq.p.rate seconds to read these data points.
	YVals(i) = (mean(data(:,2))/kevTf.maxCHVoltRange/kevTf.expand+kevTf.offset)*kevTf.sensitivity; % READS CH2, VY in Vrms, with appropriate proportionality constant, ON LOCK IN FROM DAQ. Takes the mean of nidaq.p.src_numpts data points. Takes nidaq.p.src_numpts/nidaq.p.rate seconds to read these data points.
    
    %pause(9999) % for debugging purposes
end
%freqReadVals = freqSetVals; % for debugging purposes

%% Plot

fileSaveHeader = [path, datestr(datetime,'yyyymmdd-HHMM')]; % so that timestamp is when just finished taking data; the file naming will be uniform then
ampVals = sqrt(XVals.^2+YVals.^2); % in Vrms
%phaseVals = atan(YVals./XVals)/pi()*180; % in degrees
phaseVals = atan2d(YVals,XVals); % in degrees, but < 0 if b/w 180 & 360
% for i = 1:length(phaseVals)
%     if phaseVals(i) < 0
%         phaseVals = 360+phaseVals;
%     end
% end

[Ax, Line1, Line2] = plotyy(freqReadVals/1000, ampVals*1000, freqReadVals/1000, phaseVals);
%plot(freqReadVals/1000, ampVals)
hold on
title({[upper(nidaq.notes)],...
       ['freqStep = ',           num2str(kevTf.freq_step), ' Hz'],                ...
       ['timeConstant = ',      num2str(kevTf.timeConstant), ' s'],              ...
       ['DAQ rate = ',    num2str(nidaq.p.rate),' Hz'],                          ...
       ['Number of data points averaged per data point shown = ', num2str(nidaq.p.src_numpts)],...
       ['sensitivity = ' num2str(kevTf.sensitivity),' V'],                      ...
       ['expand = '           num2str(kevTf.expand)],                           ...
       ['offset = ' num2str(kevTf.offset), ' V'],                               ...
       ['sourceAmp = ' num2str(kevTf.sourceAmp), ' V'],                         ...
       ['DAQ input channel for lock in CH1 = ' num2str(kevTf.inputLockinCH1Num)],...
       ['DAQ input channel for lock in CH2 = ' num2str(kevTf.inputLockinCH2Num)] ...
       });
xlabel('Frequency (kHz)','fontsize',20);
%ylabel('Amplitude (Vrms)','fontsize',20);
ylabel(Ax(1),'Amplitude (mVrms)','fontsize',20);
ylabel(Ax(2),'Phase (deg)','fontsize',20);

%tunForkType = 'roomTempSi_20k to 35k_0.1V-source';

%print('-dpdf',[path, datestr(datetime,'yyyymmdd-HHMM'), voltageSource, tunForkType, '.pdf'])
print('-dpdf',[fileSaveHeader, voltageSource, tunForkType, '.pdf'])
% csvwrite([path, datestr(datetime,'yyyymmdd-HHMM'), '_agilent-source_',tunForkType,'_X.csv'],XVals)
% csvwrite([path, datestr(datetime,'yyyymmdd-HHMM'), '_agilent-source_',tunForkType,'_Y.csv'],YVals)
% csvwrite([path, datestr(datetime,'yyyymmdd-HHMM'), '_agilent-source_',tunForkType,'_freqs.csv'],freqReadVals)
% csvwrite([path, datestr(datetime,'yyyymmdd-HHMM'), '_agilent-source_',tunForkType,'_amps.csv'],ampVals)
% csvwrite([path, datestr(datetime,'yyyymmdd-HHMM'), '_agilent-source_',tunForkType,'_phase.csv'],phaseVals)
allDataPts = [freqReadVals' XVals' YVals' ampVals' phaseVals'];
%csvwrite([path, datestr(datetime,'yyyymmdd-HHMM'), voltageSource, tunForkType, '_all.csv'],allDataPts)
csvwrite([fileSaveHeader, voltageSource, tunForkType, '_all.csv'],allDataPts)

wannaSaveXY = 2;
while(wannaSaveXY ~= 1 & wannaSaveXY ~= 0)
    wannaSaveXY = input('Want plots of X & Y vs freq? 1 for yes, 0 for no.\n');
end
if(wannaSaveXY)
    hold off
    [Ax, Line1, Line2] = plotyy(freqReadVals/1000, XVals*1000, freqReadVals/1000, YVals*1000);
    hold on
    title({[upper(nidaq.notes)],...
       ['freqStep = ',           num2str(kevTf.freq_step), ' Hz'],                ...
       ['timeConstant = ',      num2str(kevTf.timeConstant), ' s'],              ...
       ['DAQ rate = ',    num2str(nidaq.p.rate),' Hz'],                          ...
       ['Number of data points averaged per data point shown = ', num2str(nidaq.p.src_numpts)],...
       ['sensitivity = ' num2str(kevTf.sensitivity),' V'],                      ...
       ['expand = '           num2str(kevTf.expand)],                           ...
       ['offset = ' num2str(kevTf.offset), ' V'],                               ...
       ['sourceAmp = ' num2str(kevTf.sourceAmp), ' V'],                         ...
       ['DAQ input channel for lock in CH1 = ' num2str(kevTf.inputLockinCH1Num)],...
       ['DAQ input channel for lock in CH2 = ' num2str(kevTf.inputLockinCH2Num)] ...
       });
    xlabel('Frequency (kHz)','fontsize',20);
    ylabel(Ax(1),'X (mVrms)','fontsize',20);
    ylabel(Ax(2),'Y (mVrms)','fontsize',20);
    hold off;
    print('-dpdf',[fileSaveHeader, voltageSource, tunForkType, '_X&Y.pdf'])
end
    
nidaq.delete();
%lockin.delete(); % uncomment if using lock-in's sine out
funcgen.delete();