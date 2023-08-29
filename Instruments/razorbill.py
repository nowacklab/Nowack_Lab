import visa
import numpy as np
import time
from .instrument import Instrument, VISAInstrument

class Razorbill(VISAInstrument):
    '''
    For controlling the Razorbill RP100 power souce, which provides power to the Razorbill strain cell.
    '''
    _label = 'razorbill'

    def __init__(self, montana=None, gpib_address=''):
        '''
        Pass montana = montana.Montana().
        This will check the temperature to see what voltage we can go.
        If montana is not available, we stay at room temperature limit.
        '''
        self.montana = montana
        if type(gpib_address) is int:
            gpib_address = 'GPIB::%02i::INSTR' %gpib_address
        self.gpib_address= gpib_address
        self._init_visa(gpib_address, termination='\n')

    def checkV(self, V):
        if self.montana == None:
            low = -20
            up = 120
        else:
            T = self.montana.temperature['platform']
            low = np.piecewise(T, [T < 10, ((T<100)&(T>10)), ((T<250)&(T>100)), T >= 250], [-200, -200+5/3*(T-10), -50+(T-100)/5, -20])
            up = np.piecewise(T, [T < 10, ((T<100)&(T>10)), T >= 100], [200, 200-8/9*(T-10), 120])
        if V>up:
            return up
        elif V<low:
            return low
        else:
            return V

    def __getstate__(self):
        self._save_dict = {
            'tension output': self.output_tension,
            'compression output': self.output_compression,
            'tension slew rate': self.slewrate_tension,
            'compression slew rate': self.slewrate_compression,
            'tension voltage': self.Vtension_measured,
            'compression voltage': self.Vcompression_measured,
            'tension current': self.Itension,
            'compression current': self.Icompression
        }
        return self._save_dict

    @property
    def is_done(self):
        '''
        Return 1 when both channels have ramped to the set voltage.
        Otherwise, return 0.
        '''
        if self.Vtension_now == self.Vtension and self.Vcompression_now == self.Vcompression:
            return int(1)
        else:
            return int(0)

    def wait_for(self):
        while self.is_done != 1:
            time.sleep(0.05)

    @property
    def output_tension(self):
        '''
        Check if the tension output is enbaled.
        If it's enabled, it is connected to the source.
        Otherwise, it's connected to ground via a resistor.
        '''
        connection = {
                0: "disabled",
                1: "enabled"}
        return connection[int(self.ask('OUTP1?'))]

    @output_tension.setter
    def output_tension(self, connection):
        '''
        Enable or disable the tension output.
        Input 'enable' or 'disable'
        '''
        option = {
                "disable": 0,
                0: 0,
                "False": 0,
                "enable": 1,
                1: 1,
                "True": 1}
        if {'disabled': 0, 'enabled': 1}[self.output_tension] != option[connection]:
            self.write('SOUR1:VOLT 0')
            self.wait_for()
        self.write('OUTP1 %s' %option[connection])

    @property
    def output_compression(self):
        '''
        Check if the compression output is enbaled.
        If it's enabled, it is connected to the source.
        Otherwise, it's connected to ground via a resistor.
        '''
        connection = {0: 'disabled', 1: 'enabled'}
        return connection[int(self.ask('OUTP2?'))]

    @output_compression.setter
    def output_compression(self, connection):
        '''
        Enable or disable the compression output.
        Input is 'enable' or 'disable'
        '''
        option = {
                "disable": 0,
                0: 0,
                "False": 0,
                "enable": 1,
                1: 1,
                "True": 1}
        if {'disabled': 0, 'enabled': 1}[self.output_compression] != option[connection]:
            self.write('SOUR2:VOLT 0')
            self.wait_for()
        self.write('OUTP2 %s' %option[connection])

    @property
    def output(self):
        pass

    @output.setter
    def output(self, connection):
        '''
        Set connection of both output channels at once.
        '''
        self.output_tension = connection
        self.output_compression = connection

    @property
    def Vtension(self):
        '''
        Get the tension source voltage. This is the voltage the source is set to ramp to.
        '''
        return float(self.ask('SOUR1:VOLT?'))

    @property
    def Vcompression(self):
        '''
        Get the compression source voltage. This is the voltage the source is set to ramp to.
        '''
        return float(self.ask('SOUR2:VOLT?'))


    @Vtension.setter
    def Vtension(self, V):
        '''
        Set the tension source voltage.
        '''
        V = self.checkV(V)
        self.write('SOUR1:VOLT %s' %V)

    @Vcompression.setter
    def Vcompression(self, V):
        '''
        Set the tension source voltage.
        '''
        V = self.checkV(V)
        self.write('SOUR2:VOLT %s' %V)

    @property
    def slewrate_tension(self):
        '''
        Get the tension source slew rate.
        '''
        return float(self.ask('SOUR1:VOLT:SLEW?'))

    @property
    def slewrate_compression(self):
        '''
        Get the compression source slew rate.
        '''
        return float(self.ask('SOUR2:VOLT:SLEW?'))

    @slewrate_tension.setter
    def slewrate_tension(self, rate):
        '''
        Set the tension source slew rate. Max slew rate is 100V/s.
        '''
        if rate > 100:
            rate = 100
        self.write('SOUR1:VOLT:SLEW %s' %rate)

    @slewrate_compression.setter
    def slewrate_compression(self, rate):
        '''
        Set the compression source slew rate. Max slew rate is 100V/s.
        '''
        if rate > 100:
            rate = 100
        self.write('SOUR2:VOLT:SLEW %s' %rate)

    @property
    def slewrate(self):
        pass

    @slewrate.setter
    def slewrate(self, rate):
        '''
        Set slew rate of both source channels at once.
        '''
        self.slewrate_tension = rate
        self.slewrate_compression = rate

    @property
    def Vtension_now(self):
        '''
        Get the current tension source voltage. This is the voltage the source is currently set to.
        '''
        return float(self.ask('SOUR1:VOLT:NOW?'))

    @property
    def Vcompression_now(self):
        '''
        Get the current compression source voltage. This is the voltage the source is currently set to.
        '''
        return float(self.ask('SOUR2:VOLT:NOW?'))

    @property
    def Vtension_measured(self):
        '''
        Get the currently measured tension source voltage.
        '''
        return float(self.ask('MEAS1:VOLT?'))

    @property
    def Vcompression_measured(self):
        '''
        Get the currently measured compression source voltage.
        '''
        return float(self.ask('MEAS2:VOLT?'))

    @property
    def Itension(self):
        '''
        Get the tension source current.
        '''
        return float(self.ask('MEAS1:CURR?'))

    @property
    def Icompression(self):
        '''
        Get the compression source current.
        '''
        return float(self.ask('MEAS2:CURR?'))