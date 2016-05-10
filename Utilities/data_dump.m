function data_dump( file, path, data, labels )
%DATA_DUMP Summary of this function goes here
%   Detailed explanation goes here
filename = strcat(path,file);
disp(filename);

fid = fopen(filename, 'a');
fprintf(fid, '# ');% add comment char so easy to filter
for i=1:length(labels)
    fprintf(fid, strcat(labels{i},', ')); 
end
fprintf(fid, '\n');

fclose(fid);


dlmwrite(filename, data, '-append', 'precision', '%.6f', 'delimiter', ',');

end

