function [up_data, down_data] = plot_squidIV_multiple(varargin) % pass (csvfilestring1, label1, ...) in pairs
%plot_squidIV Summary of this function goes here
%   Detailed explanation goes here
    
    figure;
    axes = gca;
    set(0,'DefaultAxesColorOrder',jet(nargin/2))
    
for i = 1:nargin/2
    % On Squidward
    dropbox = 'C:\Users\root\Dropbox\TeamData\';
    path = strcat(dropbox, 'Montana\squid_testing\', varargin{2*i-1}); %odd arguments are csv file strings
    
    
    % For testing on Mac
    %     dropbox = '~/Dropbox (Nowack lab)/TeamData/';
    %     path = strcat(dropbox, 'Montana/squid_testing/', varargin{1});
    
    parampath = strrep(path, 'data', 'params'); %same path name, but with "params" instead of "data"
    [p, ~] = param_parse(parampath);
    
    matrix = csvread(path,1,0); % 1,0 gets rid of title row
    output = matrix(:,1);
    data = matrix(:,2);
    
    split_index = int64(length(data)/2); % finds split point between up and down ramps. up and down ramps are equal in size so this should always be an integer
    
    up_out = output(1:split_index); % splits up and down ramps
    down_out = output(split_index+1:end);
    
    up_data = data(1:split_index); % splits up and down ramps
    down_data = data(split_index+1:end);
    
    plot(axes, 1e6*up_out/p.squid.Rbias, up_data, 'DisplayName', varargin{2*i}); % 1e6 converts from A to uA
    hold(axes,'on')
end

xlabel(axes,'I_{bias} = V_{bias}/R_{bias} (\mu A)','fontsize',20);
ylabel(axes,'V_{squid} (V)','fontsize',20);
legend('Location', 'Best')

end
