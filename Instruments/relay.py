class Relay:

    def __init__(self,daq):
        self.relay_states = {1:'Off',2:'Off',3:'Off',4:'Off'}
        self.Vmax = .25
        self.daq = daq
        self.daq.outputs['ao0'].V = 0
        self.daq.outputs['ao1'].V = 0
        self.daq.outputs['ao2'].V = 0
        self.daq.outputs['ao3'].V = 0
        
    def Relay1_Off(self):
        self.daq.outputs['ao0'].V = 0 #Fischer 14
        self.daq.outputs['ao1'].V = self.Vmax #Fischer 15
        print('Flip switches 14 and 15 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao1'].V = 0
        self.relay_states[1] = 'Off'

    def Relay2_Off(self):
        self.daq.outputs['ao0'].V = self.Vmax #Fischer 19
        self.daq.outputs['ao1'].V = 0 #Fischer 20
        print('Flip switches 19 and 20 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao0'].V = 0
        self.relay_states[2] = 'Off'

    def Relay3_Off(self):
        self.daq.outputs['ao2'].V = 0 #Fischer 22
        self.daq.outputs['ao3'].V = self.Vmax #Fischer 21
        print('Flip switches 21 and 22 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao3'].V = 0
        self.relay_states[3] = 'Off'

    def Relay4_Off(self):
        self.daq.outputs['ao2'].V = self.Vmax #Fischer 23
        self.daq.outputs['ao3'].V = 0 #Fischer 24
        print('Flip switches 23 and 24 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao2'].V = 0
        self.relay_states[4] = 'Off'
    
    def All_Off(self):
        self.Relay1_Off()
        self.Relay2_Off()
        self.Relay3_Off()
        self.Relay4_Off()
        
    def On_check(self):
        if self.relay_states[1] == 'On':
            print('Relay/SQUID 1 is currently connected, disconnect it before connecting another relay/SQUID')
            self.Relay1_Off()
        if self.relay_states[2] == 'On':
            print('Relay/SQUID 2 is currently connected, disconnect it before connecting another relay/SQUID')
            self.Relay2_Off()           
        if self.relay_states[3] == 'On':
            print('Relay/SQUID 3 is currently connected, disconnect it before connecting another relay/SQUID')
            self.Relay3_Off()       
        if self.relay_states[4] == 'On':
            print('Relay/SQUID 4 is currently connected, disconnect it before connecting another relay/SQUID')
            self.Relay4_Off()
            
    def Relay1_On(self):
        self.On_check()
        self.daq.outputs['ao0'].V = self.Vmax #Fischer 14
        self.daq.outputs['ao1'].V = 0 #Fischer 15
        print('Flip switches 14 and 15 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao0'].V = 0
        self.relay_states[1] = 'On'

    def Relay2_On(self):
        self.On_check()
        self.daq.outputs['ao0'].V = 0 #Fischer 19
        self.daq.outputs['ao1'].V = self.Vmax #Fischer 20
        print('Flip switches 19 and 20 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao1'].V = 0
        self.relay_states[2] = 'On'

    def Relay3_On(self):
        self.On_check()
        self.daq.outputs['ao2'].V = self.Vmax #Fischer 22
        self.daq.outputs['ao3'].V = 0 #Fischer 21
        print('Flip switches 21 and 22 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao2'].V = 0
        self.relay_states[3] = 'On'

    def Relay4_On(self):
        self.On_check()
        self.daq.outputs['ao2'].V = 0 #Fischer 23
        self.daq.outputs['ao3'].V = self.Vmax #Fischer 24
        print('Flip switches 23 and 24 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao3'].V = 0
        self.relay_states[4] = 'On'