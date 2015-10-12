classdef CSUtils
% A bunch of static functions that you can use.  add any Computer Science
% UTILitieS to this that you think do not belong with any specific class.
% try and make them as abstract as you can
methods (Static)
    function index = findnumname(array, name, number)
    % int index findnumname (struct array, String name, int number): 
    % struct array: array of structs, each of which have field name that
    % is an integer.  index is the index of the array where number occurs
    % or -1 if not found
        index = -1;
        for i = 1:length(array)
            if(array(i).(name) == number)
                index = i;
                return
            end
        end
    end

    function array = sortnumname(array, name)
        for i = 1:length(array)
            lowest = i;
            for j = i:length(array)
                if(array(i).(name) > array(j).(name))
                    lowest = j;
                end
            end
            tmp = array(i);
            array(i) = array(lowest);
            array(lowest) = tmp;
        end
    end
    
    function str = parsefnameplot(str)
        str = regexprep(str, '_', '\\_');
    end
    
    function savecsv(filename, datamatrix, header)
        file = fopen(filename, 'w');
        fprintf(file, header);
        fclose(file);
        
        dlmwrite(filename, datamatrix, '-append');
    end
    
    function currentcheck(currents, bound)
        for c = currents
            if abs(c) > bound
                error('Current exceeds bounds');
            end
        end
    end
    
    function saveplots(rootdir, filename)
        print('-dpng', [rootdir,'autoplots/',LoggableObj.timestring(),'_', filename,'.png']);
    end
end
end
