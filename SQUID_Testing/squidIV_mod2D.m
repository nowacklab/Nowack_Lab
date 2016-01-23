function [ptable, Vsquid] = squidIV_mod2D()

clear all % MATLAB is complaining but this function will only be run like a script
close all

%% Add paths
addpath('C:\Users\root\Documents\GitHub\Nowack_Lab\Equipment_Drivers');
addpath('C:\Users\root\Documents\GitHub\Nowack_Lab\Utilities');

%% Edit before running
% If testing without a squid, for wiring, etc
no_squid = false;

% Choose parameter file
paramfile = 'mod2D_params.csv';
parampath = strcat('.\Parameters\',paramfile);
[p, ptable] = param_parse(parampath); % use ptable to see parameters in table form


% Git dump? Uncomment if you want a cluttered git.
% git_dump();


%%  Define file locations
dropbox = 'C:\Users\root\Dropbox\TeamData\';
time = char(datetime('now','TimeZone','local','Format', 'yyyyMMdd_HHmmss'));

paramsavepath = strcat(dropbox, 'Montana\squid_testing\'); % Where the parameters will be saved
paramsavefile = strcat('mod2D_params_', time, '.csv'); % What the parameters will be called

datapath = strcat(dropbox, 'Montana\squid_testing\'); % Where the data will be saved
datafile = strcat('mod2D_data_', time, '.csv'); % What the data will be called

plotpath = strcat(dropbox, 'Montana\squid_testing\');
plotfile = strcat('mod2D_plot_2D_', time, '.pdf');
plotfile2 = strcat('mod2D_plot_2D_', time, '.png');


%% Ask the user for information
% Check parameters
param_prompt(paramfile);

% Double check no squid
squid_prompt(no_squid);

% Ask for notes
notes = input('Notes about this run: ','s');
% if notes==''
%     notes = 'no notes given -_____-';
% end
fid = fopen('tempnotes.csv', 'w');
fprintf(fid, '%s', notes);
fclose(fid);

%% Some initial checks

% Check for potential SQUIDicide
if ~no_squid
    check_currents(max(abs(p.squid.Irampmax), abs(p.squid.Irampmin)), max(abs(p.squid.Irampmax), abs(p.mod.Irampmin)));
end

% Check to make sure preamp doesn't filter out your signal
if p.preamp.rolloff_high < p.daq.rate
    error('You''re filtering out your signal -____-');
end


%% Setup
nidaq = NI_DAQ(p.daq); % Initializes DAQ parameters
nidaq.set_io('squid'); % For setting input/output channels for measurements done on a SQUID

% Set output data
IsquidR = IVramp(p.squid);
Vmod = IVramp(p.mod, false); % false: do not ramp down
%Save output before running
% cannot cat two arrays of different length.  length(IsquidR) !=
% length(Vmod)
data_dump(datafile, datapath,IsquidR,{'Next row: ', 'IsquidR (V)'}); % pass cell array to prevent concatentation     
data_dump(datafile, datapath,Vmod,   {'Next row: ', 'Vmod (V)'}); % pass cell array to prevent concatentation

% Set up input variables
Vsquid = zeros(length(Vmod), length(IsquidR));

% Set up figures
figure('units','normalized','position',[.1 .1 .5 .5]);

IVplot = subplot(121);
axis square

twoDplot = subplot(122);
axis square
hold(twoDplot, 'on')
ylim(twoDplot, 1e6*[Vmod(1)/p.mod.Rbias,Vmod(end)/p.mod.Rbias]) %converts to uA
xlim(twoDplot, 1e6*[p.squid.Irampmin, p.squid.Irampmax]) %converts to uA

%% Set up stop button
uicontrol(gcf,'style','pushbutton',...
                                 'string','End',...
                                 'callback',@Button_Callback...
                                );
global STOP
STOP = false;
function Button_Callback(~,~,~)
    STOP=true;
end
                            
%% prep and send output to the daq
for i = 1:length(Vmod) % cycles over all mod currents
    Vmodstep = Vmod(i); 
    output = [IsquidR; Vmodstep * ones(1,length(IsquidR))]; % puts Vsquid into first row and array of Vmods into second row
    [Vsquidstep, ~] = nidaq.run(output); % Sends a signal to the daq and gets data back
    Vsquid(i,:) = Vsquidstep/p.preamp.gain; % corrects for gain of preamp and saves data into master array
    
    % Make plots
    hold(IVplot,'off')
    plot_squidIV(IVplot, IsquidR/p.squid.Rbias, Vsquidstep, p);
    title(IVplot,'last IV trace');
    
    plot_mod2D(twoDplot, IsquidR/p.squid.Rbias, Vsquid, Vmod/p.mod.Rbias);
    if STOP
        break
    end
    
    
end

%% Save data, parameters, and notes
% CAN BE LARGE DATA FILE: ~70 MB with some "reasonable" parameters. Takes a long time to save.
data_dump(datafile, datapath,Vsquid,{'Vsquid (V): rows are for each Imod, columns are for each IsquidR'});

copyfile('tempnotes.csv', strcat(paramsavepath,paramsavefile)); %copies parameter file to permanent location % changed to following line
disp(['copy tempnotes.csv + ', ...
        parampath, ' ', ...
        strcat(paramsavepath,paramsavefile), ' /b'])
system(['copy tempnotes.csv + ', ...
        parampath, ' ', ...
        strcat(paramsavepath,paramsavefile), ' /b']); 
    %prepends notes and saves parameter file in permanent location
% fid = fopen(strcat(paramsavepath,paramsavefile), 'a+'); %moved up above
% fprintf(fid, '%s', strcat('notes',notes,'none','notes'));
% fclose(fid);
delete('tempnotes.csv');

%% Finalize plots
close all
figure;
axis square
colormap(coolwarm)

plot_mod2D(gca, IsquidR/p.squid.Rbias, Vsquid, Vmod/p.mod.Rbias); %No subplot this time
title({['Parameter file: ' paramsavefile];['Data file: ' datafile];['Rate: ' num2str(p.daq.rate) ' Hz']},'Interpreter','none');
set(gca,'YDir','normal')

print('-dpdf', strcat(plotpath, plotfile));
print('-dpng', strcat(plotpath, plotfile2));
end