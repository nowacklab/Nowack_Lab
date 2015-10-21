function [ptable, Vsquid] = squidIV()

clear all % MATLAB is complaining but this function will only be run like a script
close all

%% Add paths and define file locations
addpath('C:\Users\root\Nowack_Lab\Equipment_Drivers');
addpath('C:\Users\root\Nowack_Lab\Utilities');

dropbox = 'C:\Users\root\Dropbox\TeamData\';
time = char(datetime('now','TimeZone','local','Format', 'yyyyMMdd_HHmmss'));

paramsavepath = strcat(dropbox, 'Montana\squid_testing\'); % Where the parameters will be saved
datapath = strcat(dropbox, 'Montana\squid_testing\'); % Where the data will be saved
paramsavefile = strcat('squidIV_params_', time, '.csv'); % What the parameters will be called
datafile = strcat('squidIV_data_', time, '.csv'); % What the data will be called

%% Edit before running

% Choose parameter file
paramfile = 'std_params.csv';
parampath = strcat('./Parameters/',paramfile);
[p, ptable] = param_parse(parampath); % use ptable to see parameters in table form

% Git dump? Uncomment if you want a cluttered git.
% git_dump();

%% Send and collect data
nidaq = NI_DAQ(p.daq); % Initializes DAQ parameters
nidaq.set_io('squid'); % For setting input/output channels for measurements done on a SQUID

% Set output data
IsquidR = IVramp(p);
Vmod = p.squid.Imod * p.squid.Rmod * ones(1,length(IsquidR)); % constant mod current

% Check for potential SQUIDicide
check_currents(max(abs(p.squid.Irampmax), abs(p.squid.Irampmin)), abs(p.squid.Imod));

% prep and send output to the daq
output = [IsquidR; Vmod]; % puts Vsquid into first row and Vmod into second row
[Vsquid, ~] = nidaq.run(output); % Sends a signal to the daq and gets data back
Vsquid = Vsquid/p.preamp.gain; % corrects for gain of preamp

%% Save data and parameters
data_dump(datafile, datapath,[IsquidR' Vsquid'],['IsquidR (V)', 'Vsquid (A)']); % 10 is for testing multiple columns
copyfile(parampath, strcat(paramsavepath,paramsavefile)); %copies parameter file to permanent location 

%% Plot
plot_squidIV(IsquidR/p.squid.Rbias, Vsquid); 
title({['Parameter file: ' paramsavefile];['Data file: ' datafile];['Rate: ' num2str(p.daq.rate) ' Hz']; ['Imod: ' num2str(p.squid.Imod) ' A']},'Interpreter','none');
% plot_modIV(data)
% plot_mod2D(data) % different plotting functions for different types of plots

end

%% Sub-functions used in this function/script

% Check currents function - prevents accidental SQUIDicide
function check_currents(Isquid, Imod)
    if Isquid >= 100e-6 || Imod >= 300e-6
        error('Current too high! Don''t kill the squid!')
    end
end

function ramped = IVramp(p)         
    half = p.squid.Irampmin:p.squid.Irampstep:p.squid.Irampmax;
    ramped = [half flip(half)] * p.squid.Rbias; % ramp up then down
end