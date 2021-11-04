class Relay:

    def __init__(self,daq):
        self.relay_states = {'Relay1':'Off','Relay2':'Off','Relay3':'Off','Relay4':'Off'}
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
        self.relay_states['Relay1'] = 'Off'
        print(self.relay_states)

    def Relay2_Off(self):
        self.daq.outputs['ao0'].V = self.Vmax #Fischer 19
        self.daq.outputs['ao1'].V = 0 #Fischer 20
        print('Flip switches 19 and 20 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao0'].V = 0
        self.relay_states['Relay2'] = 'Off'
        print(self.relay_states)

    def Relay3_Off(self):
        self.daq.outputs['ao2'].V = 0 #Fischer 22
        self.daq.outputs['ao3'].V = self.Vmax #Fischer 21
        print('Flip switches 21 and 22 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao3'].V = 0
        self.relay_states['Relay3'] = 'Off'
        print(self.relay_states)

    def Relay4_Off(self):
        self.daq.outputs['ao2'].V = self.Vmax #Fischer 23
        self.daq.outputs['ao3'].V = 0 #Fischer 24
        print('Flip switches 23 and 24 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao2'].V = 0
        self.relay_states['Relay4'] = 'Off'
        print(self.relay_states)
    
    def All_Off(self):
        self.Relay1_Off()
        self.Relay2_Off()
        self.Relay3_Off()
        self.Relay4_Off()
        
    def On_check(self):
        if self.relay_states['Relay1'] == 'On':
            print('Relay/SQUID 1 is currently connected, disconnect it before connecting another relay/SQUID')
            self.Relay1_Off()
        if self.relay_states['Relay2'] == 'On':
            print('Relay/SQUID 2 is currently connected, disconnect it before connecting another relay/SQUID')
            self.Relay2_Off()           
        if self.relay_states['Relay3'] == 'On':
            print('Relay/SQUID 3 is currently connected, disconnect it before connecting another relay/SQUID')
            self.Relay3_Off()       
        if self.relay_states['Relay4'] == 'On':
            print('Relay/SQUID 4 is currently connected, disconnect it before connecting another relay/SQUID')
            self.Relay4_Off()
            
    def Relay1_On(self):
        self.On_check()
        self.daq.outputs['ao0'].V = self.Vmax #Fischer 14
        self.daq.outputs['ao1'].V = 0 #Fischer 15
        print('Flip switches 14 and 15 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao0'].V = 0
        self.relay_states['Relay1'] = 'On'
        print(self.relay_states)

    def Relay2_On(self):
        self.On_check()
        self.daq.outputs['ao0'].V = 0 #Fischer 19
        self.daq.outputs['ao1'].V = self.Vmax #Fischer 20
        print('Flip switches 19 and 20 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao1'].V = 0
        self.relay_states['Relay2'] = 'On'
        print(self.relay_states)

    def Relay3_On(self):
        self.On_check()
        self.daq.outputs['ao2'].V = self.Vmax #Fischer 22
        self.daq.outputs['ao3'].V = 0 #Fischer 21
        print('Flip switches 21 and 22 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao2'].V = 0
        self.relay_states['Relay3'] = 'On'
        print(self.relay_states)

    def Relay4_On(self):
        self.On_check()
        self.daq.outputs['ao2'].V = 0 #Fischer 23
        self.daq.outputs['ao3'].V = self.Vmax #Fischer 24
        print('Flip switches 23 and 24 on the breakout box on then off')
        input('Press enter when finished')
        self.daq.outputs['ao3'].V = 0
        self.relay_states['Relay4'] = 'On'
        print(self.relay_states)