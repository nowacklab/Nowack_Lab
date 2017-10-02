from ..Utilities.save import Measurement
import time

class NestedMeasurement(Measurement):

    def __init__(self, measurement_constructor, 
                       measurement_constructor_args,
                       measurement_constructor_kwargs,
                       measurement_run_args,
                       measurement_run_kwargs,
                       instrument_to_varry,
                       instrument_parameter,
                       instrument_values,
                       wait_fncts,
                       wait_fncts_args,
                       log_fncts,
                       log_fncts_args):
        '''
        inputs:
        measurement_constructor: list of measurement constructors
        measurement_constructor_args: list of arguments for measurement
                                        constructors
        measurement_consructor_kwargs: list of keyward args for 
                                        measurement constroctors
        measurement_run_args: list of args to input into measurement.run
        measurement_run_kwargs: list of kwargs for measurement.run
        instrument_to_varry: instrument instance that you wish to change
                            parameter of
        instrument_parameter: parameter name (string) to varry
        instrument_values: values that you wish to set instrument_parameter
                            to be
        wait_fncts: list of functions executed relating to waiting
        wait_fncts_args: list of arguments to the above functions
        log_fncts: functions performed for logging, first argument is the 
                    measurement obj
        log_fncts_args: arguments to those functions
        '''
        self.m_c = measurement_constructor
        self.m_c_args = measurement_constructor_args
        self.m_c_kwargs = measurement_constructor_kwargs
        self.m_r_args = measurement_run_args
        self.m_r_kwargs= measurement_run_kwargs
        self.inst = instrument_to_varry
        self.paramname = instrument_parameter
        self.params = instrument_values
        self.wait_fncts = wait_fncts
        self.wait_fncts_args = wait_fncts_args
        self.log_fncts = log_fncts
        self.log_fncts_args = log_fncts_args
        self.measurements = []
        self.log = []


    def __repr__(self):
        return 'NestedMeasurement({0}, {1}, {2}, {3}, {4})'.format(
                repr(self.m_c), 
                repr(self.inst),
                repr(self.paramname),
                repr(self.params),
                repr(self.wait_fncts))

    def __str__(self):
        return ['NestedMeasurement doing measurement {0} '.format(
                    str(self.m_c)), 
                'with instrument {0} varying {1} over values {2}'.format(
                    str(self.inst), 
                    str(self.paramname),
                    str(self.params))
                ]

    def do(self):
        for i in range(len(self.params)):
            try:
                setattr(self.inst[i], self.paramname[i], self.params[i])
            except:
                print("Cannot set {0}.{1}={2}".format(
                        repr(self.inst[i]),
                        repr(self.paramname[i]),
                        repr(self.params[i])))
            try:
                self.wait_fncts[i](*self.wait_fncts_args[i])
            except:
                print("Cannot sleep, waittimes not properly defined")

            self.measurements.append(self.m_c[i](*self.m_c_args[i], 
                                                 **self.m_c_kwargs[i]))
            try:
                self.log.append(self.log_fncts[i](self.measurements[-1], *self.log_fncts_args[i]))
            except:
                self.log.append('Error')
                pass

            self.measurements[-1].run(*self.m_r_args[i], 
                                      **self.m_r_kwargs[i])

            
