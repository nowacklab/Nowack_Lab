classdef MathUtils
% A bunch of static functions that you can use.  add any Math
% UTILitieS to this that you think do not belong with any specific class.
% try and make them as abstract as you can
methods (Static)
    function angle = arctan(value)
    % returns the angle in the appropriate quadrants from 0 to 2*pi rad
    % of value
        index = -1;
        for i = 1:length(array)
            if(array(i).(name) == number)
                index = i;
                return
            end
        end
    end
    
    function [array,numpts] = span2array(center,span,step)
        numpts = span / step;
        array = linspace(center - span/2, ...
                         center + span/2, ...
                         numpts ); 
    end
    
    function array = smoothrmp_lo2hi(rawarray, ramppts)
    %smoothly ramps from 0 -> rawarray -> rawarray backwards -> 0
    %the transitions from 0 <-> rawarray(1) is sin(0), sin(pi/2)
        ramp = rawarray(1) * sin(linspace(0,pi/2,ramppts));
        array = [ramp, rawarray, rawarray(end:-1:1), ramp(end:-1:1)];
    end
    
    function array = striprmp_1(rawarray, ramplen, rawlength)
    % strips the ramp out of data, returns the 1st data set
        array = rawarray(ramplen + 1 : ramplen + rawlength);
    end
    
    function array = striprmp_2(rawarray, ramplen, rawlength)
    % strips the ramp out of the data, returns the 2nd data set
    % 1st and 2nd determined by order
        array = rawarray(ramplen + rawlength + 1 : ...
                         ramplen + rawlength + rawlength);
    end
    
    function index = hist_detect(array, trigger, range)
    % histogram detection, returns index of 1st instance of 
    % array that falls within range of trigger.
        index = 0;
        if (trigger > 0)
            upperbound = trigger + trigger*range/2;
            lowerbound = trigger - trigger*range/2;
        else
            upperbound = trigger - trigger * range/2;
            lowerbound = trigger + trigger * range/2;
        end
        for a = array
            index = index + 1;
            if(a < upperbound && a > lowerbound)
                break;
            end
        end
    end
    

end % END METHODS
end % END CLASS
