function [ptable, Vsquid] = mod_slice()

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
paramsavefile = strcat('mod_slice_params_', time, '.csv'); % What the parameters will be called

datapath = strcat(dropbox, 'Montana\squid_testing\'); % Where the data will be saved
datafile = strcat('mod_slice_data_', time, '.csv'); % What the data will be called

plotpath = strcat(dropbox, 'Montana\squid_testing\');
plotfile = strcat('mod_slice_plot_', time, '.pdf');
plotfile2 = strcat('mod_slice_plot_', time, '.png');

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
    check_currents(abs(p.squid.I), max(abs(p.mod.Irampmin), abs(p.mod.Irampmax)));
end

% Check to make sure preamp doesn't filter out your signal
if p.preamp.rolloff_high < p.daq.rate
    error('You''re filtering out your signal -____-');
end


%% Send and collect data
nidaq = NI_DAQ(p.daq); % Initializes DAQ parameters
nidaq.set_io('squid'); % For setting input/output channels for measurements done on a SQUID

% Set output data 
Vmod = IVramp(p.mod, false); % false: do not ramp down
IsquidR = p.squid.I * p.squid.Rbias * ones(1,length(Vmod)); % constant squid current

% prep and send output to the daq
output = [IsquidR; Vmod]; % puts Vsquid into first row and Vmod into second row
[Vsquid, ~] = nidaq.run(output); % Sends a signal to the daq and gets data back
Vsquid = Vsquid/p.preamp.gain; % corrects for gain of preamp

%% Save data, parameters, and notes
data_dump(datafile, datapath,[Vmod' Vsquid'],{'Vmod (V)', 'Vsquid (V)'}); % pass cell array to prevent concatentation
copyfile(parampath, strcat(paramsavepath,paramsavefile)); %copies parameter file to permanent location 
fid = fopen(strcat(paramsavepath,paramsavefile), 'a+');
fprintf(fid, '%s', strcat('notes',notes,'none','notes'));
fclose(fid);

%% Plot
figure;
plot_mod_slice(gca, Vmod, Vsquid,p); 
title({['Parameter file: ' paramsavefile];['Data file: ' datafile];['Rate: ' num2str(p.daq.rate) ' Hz']; ['Isquid: ' num2str(p.squid.I) ' A']},'Interpreter','none');

print('-dpdf', strcat(plotpath, plotfile));
print('-dpng', strcat(plotpath, plotfile2));

end
