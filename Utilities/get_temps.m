function [ temps ] = get_temps
%GET_TEMPS Summary of this function goes here
%   Detailed explanation goes here

%Set up communication 
path_to_dll = strcat('C:\Users\root\Documents\GitHub\Nowack_Lab\Utilities','\CryostationComm.dll');
NET.addAssembly(path_to_dll);
cryo = CryostationComm.CryoComm;
cryo.IP_Address = '192.168.69.101'; % 069 does not work!
cryo.Port = 7773;
cryo.Connect;
if (~cryo.CheckConnection)
    error('Toggle "Enable External Control" button in Montana software');
end
    
temps = struct();
which_temps = {'PT','ST'};
% Options: 
% GCP - Get Chamber Pressure
% GPS - Get Platform Stability
% GS1T - Get Stage 1 Temperature
% GS2T - Get Stage 2 Temperature
% GPT - Get Platform Temperature
% GSS - Get Sample Stability
% GST - Get Sample Temperature
% GTSP - Get Temperature Set Point
% GUS - Get User Stability
% GUT - Get User Temperature

for i = 1:size(which_temps,1)+1 % Loops over table "P" to extract parameter names and values
    disp(i)
    [~,temp] = cryo.SendCommandAndGetResponse(char(strcat('G',which_temps(i))), '')
    temps.(char(which_temps(i))) = temp; 
end

cryo.Exit;
cryo.delete;

end

