name = 'LoggableObjectExampleObject';
mainrepopath = '../';
addpath([mainrepopath, 'instrument_drivers']);
addpath([mainrepopath, 'measurement_scripts']);
addpath([mainrepopath, 'modules']);
l = LoggableObj_mock_instrument(name, 'Z:/home/david/codetest/datatrash/'); % create a mock instrument for testing
l.notes = 7;
l.p.param = 1;
l.p.lifeistough = 9e10;


data   = [1,2,3; 4,5,6; 7,8,9];
header = '#x, y, z';

[paramname, savename] = l.savetestdata(data, header);

%derp test so I can commit dl
% l.delete()
% 
% clearvars -except paramname savename name
% 
% 
% 
% load(paramname)
% errors = 0;
% ctr    = 1;
% 
% if((name).notes ~= 7)
%     errors = bitor(errors, ctr);
% end
% ctr = bitshift(ctr,1);
% if(p.param ~= 1)
%     errors = bitor(errors, ctr);
% end
% ctr = bitshift(ctr,1);
% if(p.lifeistough ~= 9e10)
%     errors = bitor(errors, ctr);
% end
% ctr = bitshift(ctr,1);
% if(newprop ~= 10)
%     errors = bitor(errors, ctr);
% end
% ctr = bitshift(ctr,1);
% 
% data1 = csvread(savename);
% if(sum(sum(data1 ~= [1,2,3;4,5,6;7,8,9])))
%     errors = bitor(errors,ctr);
% end
% ctr = bitshift(ctr,1);
% 
% errors