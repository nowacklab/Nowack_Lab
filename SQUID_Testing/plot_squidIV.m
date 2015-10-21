function [up_data, down_data] = plot_squidIV( output, data )
%plot_squidIV Summary of this function goes here
%   Detailed explanation goes here
split_index = int64(length(data)/2); % finds split point between up and down ramps. up and down ramps are equal in size so this should always be an integer

up_out = output(1:split_index); % splits up and down ramps
down_out = output(split_index+1:end);

up_data = data(1:split_index); % splits up and down ramps
down_data = data(split_index+1:end);

figure()
hold all
plot(1e6*up_out, up_data, '-r'); % 1e6 converts from A to uA
plot(1e6*down_out, down_data, '-b');
legend('increasing', 'decreasing', 'Location', 'best');

xlabel('I_{bias} = V_{bias}/R_{bias} (\mu A)','fontsize',20);
ylabel('V_{squid} (V)','fontsize',20);

end

