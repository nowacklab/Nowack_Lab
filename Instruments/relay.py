import time

class Relay():
    '''
    Controls relay switching on DC dipping probe.
    The NI DAQ outputs should be fed throught the relay box, through the filter box, 
    and the filter box outputs should be connected to BNC ports 15, 19, 21, and 23 on the breakout box
    ** DAQ port ao2 is not working (limited to +/-200mV), so the relay box is the work around to control all 4 
    relays in the cold without it
    '''
    def __init__(self,daq):
        print('Make sure DAQ outputs are fed through relay box, filter box, and siwtches 15, 19, 21, and 23 on the breakout box are switched on')
        self.Vmax = 3.5
        self.daq = daq
        self.daq.outputs['ao0'].V = 0
        self.daq.outputs['ao1'].V = 0
        self.daq.outputs['ao2'].V = 0
        self.daq.outputs['ao3'].V = 0
        self.relay_states = {1:'NA',2:'NA',3:'NA',4:'NA'}
        
    def Switch_Relay(self,relay_num,switch_direction):
        '''
        Sweeps voltage on relay to switch it on or off.
        
        switch_direction = 'on' or 'off'
        '''
        daq_channel = self.Relay_Num_to_Daq_Channel(relay_num)
        switch_voltage = self.Relay_Num_to_Switch_Voltage(relay_num)
        self.Send_Switch_Voltage(switch_voltage)
        self.Send_Voltage(daq_channel,switch_direction)
        self.relay_states[relay_num] = switch_direction
        print('Relay State: ', self.relay_states)
    
    def Relay_Num_to_Daq_Channel(self,relay_num):
        '''
        Convert between relay number and daq output channel
        '''
        if relay_num == 1:
            daq_channel = 'ao0'
        if relay_num == 2:
            daq_channel = 'ao0'
        if relay_num == 3:
            daq_channel = 'ao1'
        if relay_num == 4:
            daq_channel = 'ao1'
        return(daq_channel)
    
    def Relay_Num_to_Switch_Voltage(self,relay_num):
        if relay_num == 1:
            switch_voltage = 10
        if relay_num == 2:
            switch_voltage = -10
        if relay_num == 3:
            switch_voltage = 10
        if relay_num == 4:
            switch_voltage = -10
        return(switch_voltage)
        
        
    def Send_Voltage(self,daq_channel,switch_direction):
        '''
        Outputs voltage from DAQ to switch relays
        '''
        if switch_direction == 'on':
            sign = 1
        if switch_direction == 'off':
            sign = -1
            
        self.daq.sweep({daq_channel:0},{daq_channel:sign*self.Vmax},numsteps = 50);
        time.sleep(.05)
        self.daq.sweep({daq_channel:sign*self.Vmax},{daq_channel:0},numsteps = 50);
        self.daq.outputs[daq_channel].V = 0
        
    def Send_Switch_Voltage(self,switch_voltage):
        daq_channel = 'ao3'
        self.daq.sweep({daq_channel:0},{daq_channel:switch_voltage},numsteps = 50);
        time.sleep(.05)
        self.daq.sweep({daq_channel:switch_voltage},{daq_channel:0},numsteps = 50);
        self.daq.outputs[daq_channel].V = 0
        
        
        