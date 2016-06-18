function [up_data, down_data] = plot_mod_slice(varargin) % pass (axis handle, output, data) or (csvfilestring)
%plot_squidIV Summary of this function goes here
%   Detailed explanation goes here

if nargin == 1
    % On Squidward
    dropbox = 'C:\Users\root\Dropbox\TeamData\';
    path = strcat(dropbox, 'Montana\squid_testing\', varargin{1});

    
    % For testing on Mac
%     dropbox = '~/Dropbox (Nowack lab)/TeamData/';
%     path = strcat(dropbox, 'Montana/squid_testing/', varargin{1});

    parampath = strrep(path, 'data', 'params'); %same path name, but with "params" instead of "data"
    [p, ~] = param_parse(parampath); 


    matrix = csvread(path,1,0); % 1,0 gets rid of title row
    output = matrix(:,1);
    data = matrix(:,2);
    figure;
    axes = gca;
elseif nargin==4
    axes = varargin{1};
    output = varargin{2};
    data = varargin{3};
    p = varargin{4};
else
    error('check arguments');
end

plot(axes, output/p.squid.Rbias, data, 'ok'); % 1e6 converts from A to uA
legend(axes,'increasing', 'decreasing', 'Location', 'best');

xlabel(axes,'I_{mod} = V_{mod}/R_{bias} (\mu A)','fontsize',20);
ylabel(axes,'V_{squid} (V)','fontsize',20);

end

