function data_dump( file, path, data, labels )
%DATA_DUMP Summary of this function goes here
%   Detailed explanation goes here
filename = strcat(path,file);
fid = fopen(filename, 'w');

labelstring = '';
for i = 1:length(labels)
    strcat(labelstring,labels(i));
    strcat(labelstring,','); %not adding commas, test this
end 
fprintf(fid, strcat(labels,'\n'));
fclose(fid);

dlmwrite(filename, data, '-append', 'precision', '%.6f', 'delimiter', ',');

end

