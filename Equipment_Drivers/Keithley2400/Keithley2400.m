%  Keithley2400 Matlab Drivers 
%  Copyright (C) 2015 David Low, Nowack Lab
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


classdef Keithley2400 < handle % {
% NAME
%       Keithley2400 Class 
%
% SYNOPSIS
%       Keithley2400 objecthandle = Keithley2400();
%
% DESCRIPTION
%       Interface for driving Keithley2400 SourceMeter by
%       Tektronix using a NI GPIB-USB-HS and the NI 488-2
%       drivers.  It was based heavily from Keithley's 
%       'ki2400iv_w.m' file.
%
%       Create this object to use the Keithley2400.  Methods you may 
%       care about are:
%
%       Keithley2400.scan 
%       Keithley2400.scanarr
%       Keithley2400.fixed
% CHANGE LOG
%       2015 08 13: dhl88: prelim test of scan and scanarr success
%       2015 08 10: dhl88: converted to object oriented
%       2015 08 05: dhl88: combined into 1 file
%       2015 08 05: dhl88: Created

properties 
    visa    %visa object initialized in constructor
end



methods  % {

function this = Keithley2400()
% CLASS.NAME
%       Keithley2400()
%
% SYNOPSIS
%       Keithley2400 objecthandle = Keithley2400();
%
% RETURN
%       Returns a Keithley2400 object that extends handle.
%       Handle is used to pass a reference to the object instead
%       of a copy of the object so that changes to local variables
%       are carried with us.
%
% DESCRIPTION
%       Constructor initializes the visa interface only.  The visa interface
%       is not opened with just the constructor.
    this.visa = visa('ni','GPIB0::24::INSTR');

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
    set(this.visa, 'InputBufferSize',        120000); %(64/4)*2500*3 bytes
    set(this.visa, 'Name',                   'GPIB0-24');
    set(this.visa, 'OutputBufferSize',       2400); % > (64/4)*101 bytes
    set(this.visa, 'OutputEmptyFcn',         '');
    set(this.visa, 'PrimaryAddress',         24);
    set(this.visa, 'RecordDetail',           'compact');
    set(this.visa, 'RecordMode',             'overwrite');
    set(this.visa, 'RecordName',             'record.txt');
    set(this.visa, 'SecondaryAddress',       0);
    set(this.visa, 'Tag',                    '');
    set(this.visa, 'Timeout',                30);
    set(this.visa, 'TimerFcn',               '');
    set(this.visa, 'TimerPeriod',            1);
    set(this.visa, 'UserData',               []);
end

function delete(this)
% The delete function is only used in classes that extends handle.  It does
% all the things necessary to clean up the object upon deletion from other programs.
% We call it to close cleanly when we hit an error.
    delete(this.visa)
    clear this.visa
end



%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%% Measurement Methods %%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

function fixed(this,        ...
               amplitude,   ...
               sourcetype,  ...
               sensetype,   ...
               range,       ...
               compliance   ...
              )
% CLASS.NAME
%       Keithley2400.fixed
% SYNOPSIS
%       void Keithley2400.fixed(double  amplitude,
%                               char    sourcetype,
%                               char    sensetype,
%                               double  range,
%                               double  compliance
%                              )
% PARAMETERS
%       double  amplitude
%               Voltage or current for the meter to source (volts or amps)
%       char    sourcetype
%               Character ('c', 'v') that is used by these scripts 
%               to determine if the keithley should 'source' Current or 
%               Voltage.  Lowercase only.
%       char    sensetype
%               Character ('c', 'v') that is used by these scripts 
%               to determine if the keithley should 'sense' Current or 
%               Voltage.  Lowercase only.
%       double  range
%               Range of the sense measurement in Volts or Amps depending on
%               choice of sensetype.  No auto range used here.
%       double  compliance
%               Compliance level of the measurement in Volts or Amps 
%               depending on choice of sensetype.  Most commonly used
%               for setting current limit.  If we are sourcing a voltage 
%               ramp, we can manually set a current limit to prevent 
%               burning our squid or gate.
% RETURN
%       None
% DESCRIPTION
%       Sends a set voltage / current source.  Senses the current / voltage
%       to ensure compliance.
%
    fprintf('Keithley2400.fixed: Begin\n');
    try
        this.init();
        fprintf('Keithley2400.fixed: Init\n');
        this.sense(sensetype, range, compliance);
        fprintf('Keithley2400.fixed: Compliance set\n');
        switch sourcetype
        case 'c'
            fprintf(this.visa, 'SOUR:FUNC:MODE CURR');   
            fprintf(this.visa, 'SOUR:CURR:MODE FIX');   
            fprintf(this.visa,['SOUR:CURR ', num2str(amplitude)]);
        case 'v'
            fprintf(this.visa, 'SOUR:FUNC:MODE VOLT');   
            fprintf(this.visa, 'SOUR:VOLT:MODE FIX');   
            fprintf(this.visa,['SOUR:VOLT ', num2str(amplitude)]);
        otherwise
            error(['keithley2400_source: Invalid inputtype = ',...
                sourcetype,...
               '. c or v for current or voltage only\n']);
        end
    catch ME
        fprintf('Keithley2400.fixed: Caught error during scan, closing interface\n');
        this.errclose(ME);
    end
    fprintf(this.visa,'OUTP ON');                   % Output on
end

function [time,source,sense] = scan (this,          ...
                                     delay,         ...
                                     start,         ...
                                     stop,          ...
                                     spacing,       ...
                                     points,        ...
                                     direction,     ...
                                     ranging,       ...
                                     complabort,    ...
                                     sourcetype,    ...
                                     sensetype,     ...
                                     range,         ...
                                     compliance     ...
                                    )
% CLASS.NAME
%       Keithley2400.scan
% 
% SYNOPSIS
%       [double *time,
%        double *source, 
%        double *sense ]  Keithley2400.scan (double  delay,
%                                            double  start,
%                                            double  stop,
%                                            char   *spacing,
%                                            int     points,
%                                            char   *direction,
%                                            char   *ranging,
%                                            char   *complabort,
%                                            char    sourcetype,
%                                            char    sensetype,
%                                            double  range,
%                                            double  compliance
%                                           )
% PARAMETERS
%       char   *spacing
%               Select sweep spacing type (LINear, LOGarithmic).  Only accepts
%               either 'LIN' or 'LOG'
%       int     points
%               Specify number of sweep points ( [2,2500], integers only).
%       char   *direction
%               sweep from start to stop ('UP') or from stop to start ('DOWN')
%       char   *ranging
%               select source ranging mode ('BEST','AUTO','FIX'ed).
%       char   *complabort
%               Abort of compliance ('NEV'er, 'EARL'y, 'LATE')
%       double *sourcearr
%               Array of doubles (numbers) that you want outputed by
%               the keithley.  Units are Volts or Amps depending on choice
%               of sourcetype.  The max number of points is 101.
%       char    sourcetype
%               Character ('c', 'v') that is used by these scripts 
%               to determine if the keithley should 'source' Current or 
%               Voltage.  Lowercase only.
%       char    sensetype
%               Character ('c', 'v') that is used by these scripts 
%               to determine if the keithley should 'sense' Current or 
%               Voltage.  Lowercase only.
%       double  range
%               Range of the sense measurement in Volts or Amps depending on
%               choice of sensetype.  No auto range used here.
%       double  compliance
%               Compliance level of the measurement in Volts or Amps 
%               depending on choice of sensetype.  Most commonly used
%               for setting current limit.  If we are sourcing a voltage ramp,
%               we can manually set a current limit to prevent burning 
%               our squid or gate.
%
% RETURN
%       double *time
%               David is not sure what this is yet... It is supposed to
%               be some measure of time.
%       double *source
%               Array of doubles that was source'd by the keithley 
%               meter.  The keithley meter returns the voltages or 
%               currents it outputs.  In units of Volts or Amps.
%       double *sense
%               Array of doubles that was sense'd by the keithley
%               meter.  In units of Volts or Amps.
% 
% DESCRIPTION
%       The Keithley2400.scan function allows user to output or 'source'
%       either a voltage or a current and input or 'sense' a voltage or 
%       a current.  The inputs are a description of the scan you wish to use.
%       The benifit of this method over the array method is you can scan significantly
%       more points.  The function returns the data sensed and sourced.  
%
% TODO
%       fix time feature and number argument check

    time   = [0,0];
    sense  = [0,0];
    source = [0,0];
    outformat = this.formatscan(sourcetype, sensetype);

    %% Try to configure, catch errors safely to allow clean exit.
    try
        fprintf('Keithley2400.scan: Attempting to configure for scan\n');
        this.init       ();
        this.source     (delay, start, stop, spacing, points, ...
                         direction, ranging, complabort, sourcetype);
        this.sense      (sensetype, range, compliance);
        fprintf(this.visa, outformat); % format the data keithley -> comp.
    catch ME
        fprintf('Keithley2400.scan: Error during config, closing interface\n');
        this.errclose(ME);
    end

    fprintf('Keithley2400.scan: Configure Complete.  Scanning\n');

    % Try to run, catch errors to allow clean exit
    try
        [time, sense, source] = this.initscan();
    catch ME
        fprintf('Keithley2400.scan: Caught error during scan, closing interface\n');
        this.errclose(ME);
    end
    this.close();
end

function source(this,       ...
                delay,      ...
                start,      ...
                stop,       ...
                spacing,    ...
                points,     ...
                direction,  ...
                ranging,    ...
                complabort, ...
                sourcetype  ...
               )
% CLASS.NAME
%       Keithley2400.source
% 
% SYNOPSIS
%       void Keithley2400.source(double  delay,
%                                double  start,
%                                double  stop,
%                                char   *spacing,
%                                int     points,
%                                char   *direction,
%                                char   *ranging,
%                                char   *complabort,
%                                char    sourcetype
%                               )
%       
% DESCRIPTION
%       The Keithley2400.source function sets the keithley
%       2400 meter's source features that allows the keithley to
%       output voltages or currents.  
%
%       It takes a VISA object from matlab's visa('vendor','rsrcname') 
%       function and an array of numbers for the output, and the output 
%       type ('c', or 'v' for current or voltage respectively).  
%       
%       There is no return.
%

    fprintf(this.visa, 'SOUR:DEL:AUTO OFF');     % Delay auto off
    fprintf(this.visa,['SOUR:DEL '     , num2str(delay)]);
    fprintf(this.visa,['SOUR:SWE:SPAC ', spacing]);
    fprintf(this.visa,['SOUR:SWE:POIN ', num2str(points)]);
    fprintf(this.visa,['SOUR:SWE:DIR ' , direction]);
    fprintf(this.visa,['SOUR:SWE:RANG ', ranging]);
    fprintf(this.visa,['SOUR:SWE:CAB ' , complabort]);

    switch sourcetype
    case 'c'
        fprintf(this.visa, 'SOUR:FUNC:MODE CURR');   
        fprintf(this.visa, 'SOUR:CURR:MODE SWE');   
        fprintf(this.visa,['SOUR:CURR:STAR ', num2str(start)]);
        fprintf(this.visa,['SOUR:CURR:STOP ', num2str(stop)]);
        fprintf('keithley2400.source: Current Source Mode\n');
    case 'v'
        fprintf(this.visa, 'SOUR:FUNC:MODE VOLT');   % voltage mode
        fprintf(this.visa, 'SOUR:VOLT:MODE SWE');   
        fprintf(this.visa,['SOUR:VOLT:STAR ', num2str(start)]);
        fprintf(this.visa,['SOUR:VOLT:STOP ', num2str(stop)]);
        fprintf('keithley2400.source: Voltage Source Mode\n');
    otherwise 
        error(['keithley2400.source: Invalid inputtype = ',...
               inputtype,...
               '. c or v for current or voltage only\n']);
    end

    srpoints = num2str(ceil((points)^0.5)); %product of arm and trig > points

    fprintf(this.visa, ['ARM:COUN '  , srpoints]); 
    fprintf(this.visa, ['TRIG:COUN ' , srpoints]);  
    fprintf(this.visa, ['TRAC:POIN ' , num2str(points)]);
end

function [time, source, sense] = scanarr(this,       ...
                                         sourcearr,  ...
                                         sourcetype, ...
                                         sensetype,  ...
                                         range,      ...
                                         compliance  ...
                                        )
% CLASS.NAME
%       Keithley2400.scanarr
% 
% SYNOPSIS
%       [double *time,
%        double *source, 
%        double *sense ]  Keithley2400.scanarr (double *sourcearr,
%                                               char    sourcetype,
%                                               char    sensetype,
%                                               double  range,
%                                               double  compliance
%                                              )
% PARAMETERS
%       double *sourcearr
%               Array of doubles (numbers) that you want outputed by
%               the keithley.  Units are Volts or Amps depending on choice
%               of sourcetype.  The max number of points is 101.
%       char sourcetype
%               Character ('c', 'v') that is used by these scripts 
%               to determine if the keithley should 'source' Current or 
%               Voltage.  Lowercase only.
%       char sensetype
%               Character ('c', 'v') that is used by these scripts 
%               to determine if the keithley should 'sense' Current or 
%               Voltage.  Lowercase only.
%       double range
%               Range of the sense measurement in Volts or Amps depending on
%               choice of sensetype.  No auto range used here.
%       double compliance
%               Compliance level of the measurement in Volts or Amps 
%               depending on choice of sensetype.  Most commonly used
%               for setting current limit.  If we are sourcing a voltage ramp,
%               we can manually set a current limit to prevent burning 
%               our squid or gate.
%
% RETURN
%       double *time
%               David is not sure what this is yet... It is supposed to
%               be some measure of time.
%       double *source
%               Array of doubles that was source'd by the keithley 
%               meter.  The keithley meter returns the voltages or 
%               currents it outputs.  In units of Volts or Amps.
%       double *sense
%               Array of doubles that was sense'd by the keithley
%               meter.  In units of Volts or Amps.
% 
% DESCRIPTION
%       The Keithley2400.scanarr function allows user to output or 'source'
%       either a voltage or a current and input or 'sense' a voltage or 
%       a current.  The inputs are arbitrary arrays of numbers.  The 
%       function returns the data sensed and sourced.  
%
% TODO
%       fix time feature and number argument
%       

%    if nargin ~= 4  
%        error(['scanarr: Requires 3+1 inputs, nargin = ',num2str(nargin),...
%               '\n']);
%    end

    if length(sourcearr) > 101
        error(['Keithley2400.scanarr: Max source array length = 101. Length = ',...
               num2str(length(sourcearr))]);
    end

    time   = [0,0];
    sense  = [0,0];
    source = [0,0];
    outformat = this.formatscan(sourcetype, sensetype);

    %% Try to configure, catch errors safely to allow clean exit.
    try
        fprintf('Keithley2400.scanarr: Attempting to configure for scan\n');
        this.init       ();
        this.sourcearr  (sourcearr, sourcetype);
        this.sense      (sensetype, range, compliance);
        fprintf(this.visa, outformat); % format the data keithley -> comp.
    catch ME
        fprintf('Keithley2400.scanarr: Error during config, closing interface\n');
        this.errclose(ME);
    end

    fprintf('Keithley2400.scanarr: Configure Complete.  Scanning\n');

    % Try to run, catch errors to allow clean exit
    try
        [time, sense, source] = this.initscan();
    catch ME
        fprintf('Keithley2400.scanarr: Caught error during scan, closing interface\n');
        this.errclose(ME);
    end

    this.close();

end



function sourcearr(this, inputarr, inputtype)
% CLASS.NAME
%       Keithley2400.sourcearr
% 
% SYNOPSIS
%       void Keithley2400.sourcearr(double    *inputarr, 
%                                char      inputtype
%                               )
%       
% DESCRIPTION
%       The Keithley2400.sourcearr function sets the keithley
%       2400 meter's source features that allows the keithley to
%       output voltages or currents.  
%
%       It takes a VISA object from matlab's visa('vendor','rsrcname') 
%       function and an array of numbers for the output, and the output 
%       type ('c', or 'v' for current or voltage respectively).  
%       
%       There is no return.
%

%    if nargin ~= 3 
%        error('keithley2400_get: Requires 3 input parameters');
%    end

    switch inputtype
    case 'c'
        fprintf(this.visa,'SOUR:FUNC:MODE CURR');   % current mode
        fprintf(this.visa,'SOUR:CURR:MODE LIST');   % list    mode
        fprintf('keithley2400.sourcearr: Current Source Mode\n');
    case 'v'
        fprintf(this.visa,'SOUR:FUNC:MODE VOLT');   % voltage mode
        fprintf(this.visa,'SOUR:VOLT:MODE LIST');   % list    mode
        fprintf('keithley2400.sourcearr: Voltage Source Mode\n');
    otherwise 
        error(['keithley2400.sourcearr: Invalid inputtype = ',...
               inputtype,...
               '. c or v for current or voltage only\n']);
    end

    %inputarr  = round(1e-3 * sin(0:0.1:2*pi),5);
    inputstr   = sprintf(' %5.5f,' , inputarr); %precision arbitrary here
    inputstr   = inputstr(1:end-1);             % strip final comma

    fprintf(this.visa, ['ARM:COUN '      , '20']); %product of arm and trig 
    fprintf(this.visa, ['TRIG:COUN '     , '20']); % >= length(inputarr)
    fprintf(this.visa, ['TRAC:POIN '     , num2str(length(inputarr))]);
    fprintf(this.visa, ['SOUR:LIST:CURR ', inputstr]);

    fprintf(this.visa,'SOUR:DEL:AUTO OFF');     % Delay auto off
    fprintf(this.visa,'SOUR:DEL 0');            % no delay
end






function sense(this, outputtype, range, compliance)
% CLASS.NAME
%       Keithley2400.sense
% 
% SYNOPSIS
%       void Keithley2400.sense(char outputtype,
%                               double range,
%                               double compliance
%                              )
%       
% DESCRIPTION
%       The Keithley2400.sense() function initializes the keithley
%       2400 meter for sensing / reading in data.  ALWAYS use this,
%       as it controls the complianse (current / voltage limiting) 
%       features for protection.
%
%       There is no return.
    switch outputtype
    case 'v'
        fprintf(this.visa,'SENS:FUNC "VOLT"');
        fprintf(this.visa,'SENS:FUNC:CONC ON');
        fprintf(this.visa,['SENS:VOLT:PROT ', num2str(compliance)]);
        fprintf(this.visa,['SENS:VOLT:RANG ', num2str(range)]); %range
        %fprintf(this.visa,'SENS:VOLT:RANG:AUTO ON');
    case 'c'
        fprintf(this.visa,'SENS:FUNC "CURR"');
        fprintf(this.visa,'SENS:FUNC:CONC ON');
        fprintf(this.visa,['SENS:CURR:PROT ', num2str(compliance)]);
        fprintf(this.visa,['SENS:CURR:RANG ', num2str(range)]); %range
        %fprintf(this.visa,'SENS:CURR:RANG:AUTO ON');
    otherwise
       error(['Keithley2400.sense: unknown outputtype = ',...
                   outputtype]);
    end
end


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%% Init / Close Methods %%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


function init(this)
% CLASS.NAME
%       Keithley2400.init
% 
% SYNOPSIS
%       void Keithley2400.init()
%       
% DESCRIPTION
%       The Keithley2400.init() function initializes the keithley
%       2400 meter for use.  It takes a VISA object from matlab's
%       visa('vendor','rsrcname') function and initializes some
%       basic, generally static properties.  There is no return.
%
    % Initialize
    try
        fopen  (this.visa);
    catch ME
        fprintf('Keithley2400.init: visa already open.  continuing\n');
    end
    fprintf(this.visa,'*RST');                   % Restore GPIB Defaults

    % setup the 2400 to generate a Service ReQuest (SRQ) on buffer full 
    fprintf(this.visa,'*CLS');                  % Reset registers / error queues
    fprintf(this.visa,'*ESE 0');                % reset standard event enable reg.
    fprintf(this.visa,'STAT:MEAS:ENAB 512');    % Enable Buffer Full (BFL)
    fprintf(this.visa,'*SRE 1');                % Set Service Request Enable         

    % Setup Scan (not scan specific)
    fprintf(this.visa,'TRAC:FEED:CONT NEVER');  % resolve 800 error for buffer=2400
    fprintf(this.visa,'TRAC:CLE');              % Clear readings from buffer
    fprintf(this.visa,'TRAC:POIN 2400');         % set buffer size
end

function close(this)
% NAME
%       Keithley2400.close
%
% SYNOPSIS
%       void keithley2400.close()
%
% DESCRIPTION
%       Cleanly closes keithley2400 meter.  Sends cleanup signals to
%       keithley and closes the write file to the VISA.  Does not 
%       remove or clear visa handle itself.
%       Reset all the registers & clean up. if the registers are not 
%       properly reset, subsequent runs WILL NOT WORK!
    fprintf(this.visa,'*RST');
    fprintf(this.visa,':*CLS ');
    fprintf(this.visa,':*SRE 0');

    % make sure STB bit is 0
    STB = query(this.visa, '*STB?');

    % Close for Matlab 
    fclose(this.visa);
end


%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%% Helper Methods %%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%


function [time, sense, source] = initscan(this)
% Actually does the scan and takes the data
    fprintf(this.visa,':SENS:VOLT:NPLC 1');        
        % Integration Rate in line cycles
    fprintf(this.visa,':TRIG:DEL 0');                
        % Delay trigger = 0
    fprintf(this.visa,':SYST:AZER:STAT OFF');        
        % Disable auto zero 
    fprintf(this.visa,':SYST:TIME:RES:AUTO ON'); 
        % Enable time stamp when exit idle
    fprintf(this.visa,':TRAC:TST:FORM ABS');         
        % absolute time timestamp
    fprintf(this.visa,':TRAC:FEED:CONT NEXT');       
        % buffer feed mode = next

    % Turn on the machine
    fprintf('Keithley2400.initscan: Begin Scan\n');
    fprintf(this.visa,'OUTP ON');                   % Output on
    fprintf(this.visa,'INIT');                      % initialize scan 

    % Used the serial poll function to wait for SRQ
    val = [1];       % 1st instrument in the gpib object, not the gpib add
    spoll(this.visa,val);  % keep control until SRQ

    % Quary for data
    fprintf('Keithley2400.initscan: PC Request Data\n');
    fprintf(this.visa,'TRAC:DATA?');

    [A,count] = scanstr(this.visa,',','%f');

    fprintf('Keithley2400.initscan: Scan complete \n');

    time   = A(1:3:length(A),:);
    sense  = A(1:3:length(A),:);
    source = A(2:3:length(A),:);
end

function outformat = formatscan(this, sourcetype, sensetype)
% a long switch statement for fixing the output format string.
% helper function to improve readability.
    outformat = 'FORM:ELEM:SENS TIME,';

    switch sourcetype
    case 'v'
        outformat = [outformat, 'VOLT,'];
    case 'c'
        outformat = [outformat, 'CURR,'];
    otherwise
        error(['keithley2400: unknown inputtype = ', sourcetype,'\n']);
    end

    switch sensetype
    case 'v'
        outformat = [outformat, 'VOLT'];
    case 'c'
        outformat = [outformat, 'CURR'];
        otherwise
        sensetype
        error(['Keithley2400.formatscan: unknown outputtype = ', sensetype,'\n']);
    end
end

function errclose(this, ME)
    this.close();
    this.delete();
    rethrow(ME);
end

end % } End methods

end % } class end
% END OF FILE
