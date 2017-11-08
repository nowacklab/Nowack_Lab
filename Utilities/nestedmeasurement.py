from ..Utilities.save import Measurement
import time
import types
import datetime
import numpy as np

class NestedMeasurement(Measurement):

    def __init__(self, measurement_constructor, 
                       measurement_constructor_args,
                       measurement_constructor_kwargs,
                       measurement_run_args,
                       measurement_run_kwargs,
                       instrument_to_varry,
                       instrument_parameter,
                       instrument_values,
                       before_fnct,
                       before_fnct_args,
                       wait_fncts,
                       wait_fncts_args,
                       log_fncts,
                       log_fncts_args,
                       pre_run,
                       pre_run_args,
                       post_run,
                       post_run_args,
                       saveinfolder = True,
                       saveinsamefolder = True
                       ):
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
        self.params = np.array(instrument_values)
        self.wait_fncts = wait_fncts
        self.wait_fncts_args = wait_fncts_args
        self.log_fncts = log_fncts
        self.log_fncts_args = log_fncts_args
        self.before_fnct = before_fnct
        self.before_fnct_args = before_fnct_args
        self.pre_run = pre_run
        self.pre_run_args = pre_run_args
        self.post_run = post_run
        self.post_run_args = post_run_args
        self.measurements = []
        self.filenames = []
        self.log = []
        self.saveinfolder = saveinfolder
        self.saveinsamefolder = saveinsamefolder
        self.folderpath_remote = ''
        self.folderpath_local  = ''

        if self.saveinfolder:
            now = datetime.datetime.now()
            self.folder = now.strftime('%Y-%m-%d_%H%M%S')
            self.folder +=  '_' + self.__class__.__name__


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

    def do(self, saveinfolder = True):
        self.before_fnct(self, *self.before_fnct_args)
        for i in range(len(self.params)):
            try:
                setattr(self.inst[i], self.paramname[i], self.params[i])
            except:
                print("Cannot set {0}.{1}={2}".format(
                        repr(self.inst[i]),
                        repr(self.paramname[i]),
                        repr(self.params[i])))
            try:
                self.wait_fncts[i](self, *self.wait_fncts_args[i])
            except:
                print("Cannot sleep, waittimes not properly defined")

            # Construct measurement
            self.measurements.append(self.m_c[i](*self.m_c_args[i], 
                                                 **self.m_c_kwargs[i]))

            # Log measurement
            try:
                self.log.append(self.log_fncts[i](self, 
                                self.measurements[-1], 
                                *self.log_fncts_args[i]))
            except:
                self.log.append('Error')
                pass

            # If folder for this measurement, redefine save
            if saveinfolder:
                NestedMeasurement.saveinfolder(self.folder, 
                                         self.measurements[-1],
                                         localpath = self.folderpath_local,
                                         remotepath= self.folderpath_remote)

            # Prerun
            self.pre_run[i](self, *self.pre_run_args[i])

            # run
            self.measurements[-1].run(*self.m_r_args[i], 
                                      **self.m_r_kwargs[i])

            # store filenames
            self.filenames.append(self.measurements[-1].filename)

            # postrun
            self.post_run[i](self, *self.post_run_args[i])

            if (self.saveinsamefolder and len(self.measurements) == 1):
                self.folderpath_remote = self.measurements[0]._remotepath
                self.folderpath_local  = self.measurements[0]._localpath

        self.pre_run = 'deleted'
        self.post_run = 'deleted'
        self.log_fncts = 'deleted'
        self.wait_fncts = 'deleted'
        self.before_fncts = 'deleted'

        # TODO: fix saving
        # TODO: add 'after' function that does something after loop

    
    @staticmethod
    def saveinfolder(foldername, obj, localpath, remotepath):
        def newsave(self, **kwargs):
            return super(type(obj), obj).save(appendedpath=foldername,
                                              savepath=True,
                                              localpath=localpath,
                                              remotepath=remotepath,
                                              **kwargs)
        obj.save = types.MethodType(newsave, obj)
            
    def setup_plots(self):
        pass

    def plot(self):
        pass

class NestedMeasurement_f(Measurement):

    def __init__(self,
                beforeloop,
                isdone,
                beforechange,
                changeinstr,
                sleeper,
                makemeasurement,
                runmeasurement,
                aftermeasure):
        self.beforeloop = beforeloop
        self.isdone = isdone
        self.beforechange = beforechange
        self.changeinstr = changeinstr
        self.sleeper = sleeper
        self.makemeasurement = makemeasurement
        self.runmeasurement = runmeasurement
        self.aftermeasure = aftermeasure
        self.measurements = []
        self.filenames = []
        self.i =  0

    def __repr__(self):
        return 'NestedMeasurement_functionstyle'

    def __str__(self):
        return ''

    def do(self):
        self.beforeloop(self)
        while(self.isdone(self)):
            self.beforechange[self.i](self)
            self.changeinstr[self.i](self)
            self.sleeper[self.i](self)
            self.makemeasurement[self.i](self)
            self.runmeasurement[self.i](self)
            self.aftermeasure[self.i](self)
            while len(self.filenames) < len(self.measurements):
                self.filenames.append(self.measurements[len(self.filenames)].filename)

    @staticmethod
    def runmeasurement(obj, *args, **kwargs):
        obj.measurements[-1].run(*args, **kwargs)
            
    @staticmethod
    def makemeasurement(obj, measurementconstructor, *args, **kwargs):
        obj.measurements.append(
                measurementconstructor(*args, **kwargs))

    @staticmethod
    def sleeper(obj, time):
        time.sleep(time)

    @staticmethod
    def changeinstr(obj, instr, paramnames, values):
        for p,v in zip(paramnames, values):
            setattr(instr, p, v)


class NestedMeasurements_oneinstr_oneparam(NestedMeasurement_f):

    def __init__(self,
                instr, paramname, vals, 
                beforeloop,
                beforechange,
                sleeper,
                makemeasurement,
                runmeasurement,
                aftermeasurement
                ):
        self.instr = instr
        self.vals = vals
        isdone = lambda obj: obj.i < len(obj.vals)
        changeinstr = [lambda obj: 
                        NestedMeasurements_f.changeinstr(instr, 
                                                         paramname, 
                                                         obj.vals[obj.i])]
        super().__init__(beforeloop,
                         isdone,
                         beforechange,
                         changeinstr,
                         sleeper,
                         makemeasurement,
                         runmeasurement,
                         aftermeasurement)
        

