function [ data, time ] = run_daq(the_daq, output )
%RUN_DAQ Summary of this function goes here
%   Detailed explanation goes here
the_daq.queueOutputData(output);
[data, time] = this.session.startForeground;

end

