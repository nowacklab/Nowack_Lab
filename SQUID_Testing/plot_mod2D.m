function [up_data, down_data] = plot_mod2D(varargin) % pass (axis handle, output, data) or (csvfilestring)
%plot_squidIV Summary of this function goes here
%   Detailed explanation goes here
%

%% NOT TESTED
if nargin == 1  
    % On Squidward
%     dropbox = 'C:\Users\root\Dropbox\TeamData\';
%     path = strcat(dropbox, 'Montana\squid_testing\', varargin{1});

    % For testing on Mac
    dropbox = '~/Dropbox (Nowack lab)/TeamData/';
    path = strcat(dropbox, 'Montana/squid_testing/', varargin{1});

    matrix = csvread(path,1,0); % 1,0 gets rid of title row
    output = matrix(:,1);
    data = matrix(:,2);
    figure;
    axes = gca;
    
%% 
elseif nargin==4
    axes = varargin{1};
    output = varargin{2};
    data = varargin{3};
    Imod = varargin{4};
else
    error('check arguments');
end

% Below is now generalized for 2D array ?
split_index = int64(size(data,2)/2); % finds split point between up and down ramps. up and down ramps are equal in size so this should always be an integer

up_out = output(1:split_index); % splits up and down ramps
down_out = output(split_index+1:end);

up_data = data(:,1:split_index); % splits up and down ramps
down_data = data(:,split_index+1:end);

imagesc(1e6*up_out,1e6*Imod,up_data,'Parent',IVplot); % plots I_squid (uA) on x-axis, I_mod (uA) on y-axis, and V_squid as color

xlabel(axes,'I_{squid} = V_{squid}/R_{bias} (\mu A)','fontsize',20);
ylabel(axes,'I_{mod} = V_{mod}/R_{bias} (\mu A)','fontsize',20);
c = colorbar;
ylabel(c,'V_{squid} (V)','fontsize',20);
end

