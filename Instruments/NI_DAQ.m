%  NI DAQ Matlab Drivers 
%  Copyright (C) 2015 David Low, Brian Schaefer, Nowack Lab

classdef NI_DAQ < handle % inherits handle because matlab complained
   
    properties (Access = public)
        p % parameters
        in % input devices
        out % output devices
        session     %session object
        sense      %array of input  channels structs (sense)
        source     %array of output channels structs (source)
        ramped_from_zero = false % boolean to check if added ramp at beginning of output
        ramped_to_zero = false % boolean to check if added ramp at end of output
        ramp_zero_numpts = 50 % number of points used to smoothly ramp to/from zero
                            % Fixed number of points, or fixed time with min numpts?
    end    % properties         % structs defined only in addinput() or addoutput()
    
    methods (Access = public)

        %% Initialize
       function this = NI_DAQ(daq_params)
            this.session = daq.createSession('ni'); %creates daq session
            this.p = daq_params; % stores passed parameters
            this.set_params(); % sets daq parameters
       end 
       
       %% Set parameters
       function set_params(this)
           this.session.Rate = this.p.rate;
%            addAnalogInputChannel(this.session, devicename, ...
%                                    channelnumber, measurementtype);
       end
       
       function set_io(this, type)
           switch(type)
               case 'squid'
                   this.out.isquid = addAnalogOutputChannel(this.session, 'Dev1', 0, 'Voltage'); % source current
                   this.out.isquid.Range = [-this.p.range this.p.range];
                   
                   this.in.vsquid = addAnalogInputChannel(this.session, 'Dev1', 0, 'Voltage'); % source current
                   this.in.vsquid.Range = [-this.p.range this.p.range];
                   
                   this.out.vmod = addAnalogOutputChannel(this.session, 'Dev1', 1, 'Voltage'); % source current
                   this.out.vmod.Range = [-this.p.range this.p.range];
           end
       end
       
       function [data, time] = run(this, output)
           for channel = 1:size(output,1) % loops over output channels
               if output(channel, 1) ~= 0
                   output = this.ramp_from_zero(output); % function adds voltage ramp to beginning of output so that daq always starts from zero
               end

               if output(channel, end) ~=0
                   output = this.ramp_to_zero(output); % function adds voltage ramp to end of output so that daq always ends at zero
               end
           end
           
           output = [output output(:,end)]; % duplicating last point because outputting one extra point triggers input from daq (daq sends data back 1 data point behind)
           
           this.session.queueOutputData(output'); % ' switches row to column
           [data, time] = this.session.startForeground; % starts data output and collects input
           data = data'; % change to row vector
           
           % Data post-processing
           data = data(2:end); %First data point is bogus, daq returns data one data point behind
           if (this.ramped_from_zero)
               data = data(this.ramp_zero_numpts+1:end); %removes ramp from zero
           end
           if (this.ramped_to_zero)
               data = data(1:end-this.ramp_zero_numpts); %removes ramp to zero
           end
       end
       
       function ramped = ramp_from_zero(this, signal)  
            this.ramped_from_zero = true;
            
            ramped = [signal(:,1)*sin(linspace(0,pi/2,this.ramp_zero_numpts)) signal]; 
       end
       
       function ramped = ramp_to_zero(this, signal)
            this.ramped_to_zero = true;
            
            ramped = [signal signal(:,end)*sin(linspace(pi/2,0,this.ramp_zero_numpts))]; % f'n not written yet!
       end
       
    end % methods
end  % classdef
