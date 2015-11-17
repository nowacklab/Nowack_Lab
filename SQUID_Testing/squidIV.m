function [ptable, Vsquid] = squidIV()

clear all % MATLAB is complaining but this function will only be run like a script
close all
%% Add paths 
addpath('C:\Users\root\Nowack_Lab\Equipment_Drivers');
addpath('C:\Users\root\Nowack_Lab\Utilities');

%% Edit before running

% If testing without a squid, for wiring, etc
no_squid = false;

% Choose parameter file
paramfile = 'std_params_warm3k_davidplay.csv';
parampath = strcat('./Parameters/',paramfile);
[p, ptable] = param_parse(parampath); % use ptable to see parameters in table form

% Git dump? Uncomment if you want a cluttered git.
% git_dump();

%% Define file locations
dropbox = 'C:\Users\root\Dropbox\TeamData\';
time = char(datetime('now','TimeZone','local','Format', 'yyyyMMdd_HHmmss'));

paramsavepath = strcat(dropbox, 'Montana\squid_testing\'); % Where the parameters will be saved
paramsavefile = strcat('squidIV_params_', time, '.csv'); % What the parameters will be called

datapath = strcat(dropbox, 'Montana\squid_testing\'); % Where the data will be saved
datafile = strcat('squidIV_data_', time, '.csv'); % What the data will be called

plotpath = strcat(dropbox, 'Montana\squid_testing\');
plotfile = strcat('squidIV_plot_IV_', time, '.pdf');
plotfile2 = strcat('squidIV_plot_IV_', time, '.png');

%% Ask the user for information
% Check parameters
param_prompt(paramfile);

% Double check no squid
squid_prompt(no_squid);

% Ask for notes
notes = input('Notes about this run: ','s');

%% Some initial checks

% Check for potential SQUIDicide
if ~no_squid
    check_currents(max(abs(p.squid.Irampmax), abs(p.squid.Irampmin)), abs(p.mod.I));
end

% Check to make sure preamp doesn't filter out your signal
if p.preamp.rolloff_high < p.daq.rate
    error('You''re filtering out your signal -____-');
end


%% Send and collect data
nidaq = NI_DAQ(p.daq); % Initializes DAQ parameters
nidaq.set_io('squid'); % For setting input/output channels for measurements done on a SQUID

% Set output data
IsquidR = IVramp(p.squid);
Vmod = p.mod.I * p.mod.Rbias * ones(1,length(IsquidR)); % constant mod current

% prep and send output to the daq
output = [IsquidR; Vmod]; % puts Vsquid into first row and Vmod into second row
[Vsquid, ~] = nidaq.run(output); % Sends a signal to the daq and gets data back
Vsquid = Vsquid/p.preamp.gain; % corrects for gain of preamp

%% Save data, parameters, and notes
data_dump(datafile, datapath,[IsquidR' Vsquid'],{'IsquidR (V)', 'Vsquid (V)'}); % pass cell array to prevent concatentation
copyfile(parampath, strcat(paramsavepath,paramsavefile)); %copies parameter file to permanent location 
fid = fopen(strcat(paramsavepath,paramsavefile), 'a+');
fprintf(fid, '%s', strcat('notes',notes,'none','notes'));
fclose(fid);

%% Plot
figure;
plot_squidIV(gca, IsquidR, Vsquid, p); 
title({['Parameter file: ' paramsavefile];['Data file: ' datafile];['Rate: ' num2str(p.daq.rate) ' Hz']; ['Imod: ' num2str(p.mod.I) ' A']},'Interpreter','none');

print('-dpdf', strcat(plotpath, plotfile));
print('-dpng', strcat(plotpath, plotfile2));

end
