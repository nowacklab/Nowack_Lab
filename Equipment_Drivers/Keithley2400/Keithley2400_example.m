%% Testing the keithley 2400 drivers with a 4 point measurement
% author: david low (dhl88)
% change log:
%   2015 08 13: Tested OO version of Keithley2400.  success.
currlist = round(1e-3*sin(0:0.1:2*pi),5);

meter = Keithley2400();
[time, source, sense] = meter.scan(0,     ...%delay
                                   -10.0, ...%start
                                    10.0, ...%stop
                                   'LIN', ...%spacing
                                    2400, ...%points
                                   'UP',  ...%direction
                                   'BEST',...%ranging
                                   'EARL',...%complabort
                                   'v',   ...%sourcetype
                                   'c',   ...%sourcetype
                                    0.001,...%range
                                    0.002 ...%compliance
                                   );

figure(1);
plot(time, source, 'ro');
xlabel('time');
ylabel('source (A)');
figure(2);
plot(time, sense, 'bs');
xlabel('time');
ylabel('sense (V)'); 
figure(3);
plot(source, sense, ':bo');
xlabel('source (A)');
ylabel('sense (V)');

[time, source, sense] = meter.scanarr(currlist,...%source array
                                      'c',     ...%sourcetype
                                      'v',     ...%sensetype
                                      10,      ...%range
                                      15       ...%compliance
                                     );
                                 
figure(4);
plot(time, source, 'ro');
xlabel('time');
ylabel('source (A)');
figure(5);
plot(time, sense, 'bs');
xlabel('time');
ylabel('sense (V)'); 
figure(6);
plot(source, sense, ':bo');
xlabel('source (A)');
ylabel('sense (V)');                                
