function [ params, table ] = param_parse( csvfile )
%PARAM_PARSE Summary of this function goes here
%   Imports parameters from a parameters file, categorizes them by type
%   (e.g. 'daq', 'squid'), and (WILL EVENTUALLY) convert units to SI

table = readtable(csvfile,'HeaderLines', 1, 'Delimiter',',', 'Format', '%s%f%s%s'); %Table needed because more than just variable name and value
params = struct();

for i = 1:size(table,1) % Loops over table "P" to extract parameter names and values
    params.(char(table{i, {'Type'}})).(char(table{i, {'Name'}})) = table{i, {'Value'}}; 
end



%% OLD
% P = importdata(csvfile); % Read contents of csv file
% params = struct(); % empty struct for parameters
% 
% for i = 1:size(P.data,1) % loop over all parameters
%     
%     params.(char(P.textdata(i))) = P.data(i); % Create parameter with key using text identifier and value using the value
% end

% Following line reads table out again with float as a string for easy
% readout for debugging, etc.
table = readtable(csvfile,'HeaderLines', 1,'Delimiter',',', 'Format', '%s%s%s%s'); %Table needed because more than just variable name and value


end

