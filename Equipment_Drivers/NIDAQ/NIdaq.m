%  NI DAQ Matlab Drivers 
%  Copyright (C) 2015 David Low, Brian Schaefer, Nowack Lab
%
%   This program is free software: you can redistribute it and/or modify
%   it under the terms of the GNU General Public License as published by
%   the Free Software Foundation, either version 3 of the License, or
%   (at your option) any later version.
%
%   This program is distributed in the hope that it will be useful,
%   but WITHOUT ANY WARRANTY; without even the implied warranty of
%   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
%   GNU General Public License for more details.
%
%   You should have received a copy of the GNU General Public License
%   along with this program.  If not, see <http://www.gnu.org/licenses/>.


classdef NIdaq < LoggableObj % {
% NAME
%       NIdaq.m  
%
% SYNOPSIS
%       NIdaq objecthandle = NIdaq();
%
% DESCRIPTION
%       Interface for driving NIdaq 
%
%       Create this object to use the NI DAQ.  Methods you may 
%       care about are:
%
% CHANGE LOG
%       2015 10 02: dl: reproduced and solved the input/output offset bug 
%       2015 08 26: dl: created

properties (Access = public)
    session     %session object
    sense      %array of input  channels structs (sense)
    source     %array of output channels structs (source)
                % structs defined only in addinput() or addoutput()
end

methods (Access = public) % {


function this = NIdaq(author, savedir)
% NAME
%       NIdaq()
% SYNOPSIS
%       NIdaq objecthandle = NIdaq();
% RETURN
%       Returns a NIdaq object that extends handle.  
%       Handle is used to pass a refere
    this = this@LoggableObj('NIdaq',author, savedir);
    this.session = daq.createSession('ni');
end

function delete(this)
	% set all input / output to zeros
	this.zerothesource();
	
	% clean up
    this.delete@LoggableObj();
    clear this.sense;
    clear this.source;
    release(this.session);
end

%%%%%%% Setup Methods
function setrate(this, rate)
    this.session.Rate = rate;
end

function handle = addinput_A(this, ...
                    devicename, channelnumber, measurementtype, range,...
                    label)
    handle = addAnalogInputChannel(this.session, devicename, ...
                                   channelnumber, measurementtype);
    handle.Range = [-range, range];
    input_s = struct( ...
                'devicename',       devicename,...
                'channelnumber',    channelnumber,...
                'measurementtype',  measurementtype,...
                'range',            range,...
                'handle',           handle,...
                'label',            label...
                );
    this.sense = [this.sense, input_s];
end

function handle = addoutput_A(this, ...
                    devicename, channelnumber, measurementtype, range,...
                    label)
    handle = addAnalogOutputChannel(this.session, devicename, ...
                                   channelnumber, measurementtype);
    handle.Range = [-range, range];
    output_s = struct( ...
                'devicename',       devicename,...
                'channelnumber',    channelnumber,...
                'measurementtype',  measurementtype,...
                'range',            range,...
                'handle',           handle,...
                'label',            label,...
                'data',             []...
                );
    this.source = [this.source, output_s];
    this.source = CSUtils.sortnumname(this.source, 'channelnumber');
end

function setoutputdata(this, channelnumber, data)
%data has 1 more entry at the end than necessary to cope with weirdness
%with data taking.
%format of data can be either a row or column vector, as long as 1D
%TODO (need to check this to make sure it works!!!!)
%DL 151002: Something is definitely wrong!
    i = CSUtils.findnumname(this.source, 'channelnumber', channelnumber);
    this.source(i).data = zeros(length(data)+1,1);
    for j = 1:length(data)
        this.source(i).data(j) = data(j);
    end
    this.source(i).data(length(data)+1) = data(length(data));
end

%%%%%%% Measurement Methods
function [data, time] = run(this, willsave)
	% do not save <=> willsave = 0
    if nargin < 2
        willsave = 1;
    end
    
    datalist = zeros(length(this.source(1).data),length(this.source));
    for i = 1:length(this.source)
        datalist(:,i) = this.source(i).data; %set each column 
    end
    this.session.queueOutputData(datalist);
    [data, time] = this.session.startForeground;
    
    
    
    sourcedata = zeros(length(data), length(this.source));
    for i = 1:length(this.source)
        sourcedata(:,i) = this.source(i).data;
    end
    
    sourcedata(end,:) = [];
    data(1,:) = []; %first data point has output from last time daq ran!
    time(1,:) = []; %measure at the very instant the voltage is changed
    
    tmp = [sourcedata, data, time]; % I don't know why, but this gave no error...
    
    if willsave
        this.saveparams({'sense','source'});
        this.savedata  (tmp, this.savedataheader);
    end
end

function save(this)
    % saves parameters
    this.saveparams({'sense','source'});
end

function zerothesource(this)
	for i = 1:length(this.source)
		this.setoutputdata(this.source(i).channelnumber, zeros(1,10));
	end
	[~,~] = run(this,0);
end

end % } END methods

methods(Access = private)
    function str = savedataheader(this)
        str = ['# ',LoggableObj.timestring(),', ',this.namestring,'\n# '];
        for i = 1:length(this.source) % this is source
            units = '(A), ';
            if(strcmp('Voltage', this.source(i).measurementtype))
                units = '(V), ';
            end
            str = [str, this.source(i).label, ' ', units];
        end
        for i = 1:length(this.sense) % this is sense
            units = '(A), ';
            if(strcmp('Voltage', this.sense(i).measurementtype))
                units = '(V), ';
            end
            str = [str, this.sense(i).label, ' ', units];
        end
        str = [str, 'time (s)\n'];
    end
end

end % } ENE class 
% END OF FILE
