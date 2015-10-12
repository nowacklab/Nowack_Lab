%  Agilent 33250 Matlab Drivers 
%  Copyright (C) 2015 David Low, Kevin Nangoi, Nowack Lab
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


classdef Agilent33250A < LoggableObj % {
% NAME
%       Agilent33250A.m  
%
% SYNOPSIS
%       Agilent33250A objecthandle = Agilent33250A();
%
% DESCRIPTION
%       Interface for driving Agilent33250A 
%
%       Create this object to use the Agilent33250A.  Methods you may 
%       care about are:
%
% CHANGE LOG
%       2015 09 14: dhl88: tested applywave
%       2015 09 14: dhl88: created

properties (Access = public)
    visa     %visa object
    
end

methods (Access = public) % {


function this = Agilent33250A(author, savedir)
% NAME
%       NIdaq()
% SYNOPSIS
%       NIdaq objecthandle = NIdaq();
% RETURN
%       Returns a NIdaq object that extends handle.  
%       Handle is used to pass a refere
    this = this@LoggableObj('Agilent33250A',author, savedir);
    this.visa = visa('ni','GPIB0::10::INSTR');

    % this is from the keithley driver... I think it's necessary?
    set(this.visa, 'BoardIndex',             0);
    set(this.visa, 'ByteOrder',              'littleEndian');
    set(this.visa, 'BytesAvailableFcn',      '');
    set(this.visa, 'BytesAvailableFcnCount', 48);
    set(this.visa, 'BytesAvailableFcnMode',  'eosCharCode');
    set(this.visa, 'CompareBits',            8);
    set(this.visa, 'EOIMode',                'on');
    set(this.visa, 'EOSCharCode',            'LF');
    set(this.visa, 'EOSMode',                'read&write');
    set(this.visa, 'ErrorFcn',               '');
    set(this.visa, 'InputBufferSize',        2048); 
    set(this.visa, 'Name',                   'GPIB0-10');
    set(this.visa, 'OutputBufferSize',       2048);
    set(this.visa, 'OutputEmptyFcn',         '');
    set(this.visa, 'PrimaryAddress',         10);
    set(this.visa, 'RecordDetail',           'compact');
    set(this.visa, 'RecordMode',             'overwrite');
    set(this.visa, 'RecordName',             'record.txt');
    set(this.visa, 'SecondaryAddress',       0);
    set(this.visa, 'Tag',                    '');
    set(this.visa, 'Timeout',                10);
    set(this.visa, 'TimerFcn',               '');
    set(this.visa, 'TimerPeriod',            1);
    set(this.visa, 'UserData',               []);
    
    fopen(this.visa);
    
	%fprintf(this.visa, '*RST'); % resets agilent to factory setting
    fprintf(this.visa, '*CLS');
    
end

function delete(this)
%full clean close, including cleaning par
    this.delete@LoggableObj();
    fclose(this.visa);    
    clear this.visa;
end

%%%%%%% Scan methods
function outputz(this, zout... %output impedance in ohms, 1-10k
                )
    this.checkerror();
    %fprintf('outputz\n'); % for debugging purposes
    str = ['OUTP:LOAD ', num2str(zout), '\n'];
    fprintf(this.visa, str);
end

function applywave(this, ...
       funct, ... %"SIN", "SQU"are, "RAMP", "PULS"e, "NOIS"e, DC, "USER"
       freq,  ... %frequency in Hz
       amp,   ... %amplitude in Vpp
       offset... %offset voltage in V V_dc
       )
   %fprintf('applywave\n'); % for debugging purposes
   this.checkerror();
   str = ['APPL:', funct, ' ', num2str(freq),   ' HZ, '];
   str = [str,                 num2str(amp),    ' VPP, ' ];
   str = [str,                 num2str(offset), ' V\n' ];
   fprintf(this.visa, str);
end

function freqOut = getFreq(this) % reads frequency in Hz
   this.checkerror();
   %fprintf('getfreq after check error\n');
   fprintf(this.visa, 'FREQ?'); % DO NOT ADD \n after "FREQ?"!!! Doesn't like it!
   %fprintf('getfreq after this.visa\n');
   freqOut = fscanf(this.visa, '%f');
   %fprintf('somet\n');
end

function setFreq(this, freqVal) % sets frequency in Hz
    this.checkerror();
    fprintf(this.visa, ['FREQ ', num2str(freqVal), '\n']);
end

% function freqsweep(fstart, ...%start freq in Hz
%                    fstop,  ...%stop  freq in Hz
%                    spacing,...%string, "LIN" or "LOG"
%                    time   ...%time of total sweep in sec
%                    )
%     return %incomplete method
% end

end % } END methods

methods(Access = public)
    function checkerror(this)
        while(1)
            %fprintf('inside while checkerror\n')
            fprintf(this.visa,'SYST:ERR?');
            err = fscanf(this.visa, '%f,%255c');
            errnum = err(1);
            if (errnum == 0)
                break;
            else
                fprintf([num2str(err(1)), ' ', char(err(2:end))', ' \n']);
            end
        end
    end
end

end % } END class 
% END OF FILE
