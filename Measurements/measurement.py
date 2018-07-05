import numpy as np, matplotlib.pyplot as plt, time, traceback
from ..Utilities.plotting.plotter import Plotter
from ..Utilities.save import Saver

class Measurement(Saver, Plotter):
    _daq_inputs = [] # DAQ input labels expected by this class
    _daq_outputs = [] # DAQ output labels expected by this class
    instrument_list = []
    interrupt = False # boolean variable used to interrupt loops in the do.

    def __init__(self, instruments = {}):
        super(Measurement, self).__init__()
        self._load_instruments(instruments)


    def _load_instruments(self, instruments={}):
        '''
        Loads instruments from a dictionary.
        '''
        self.instruments = instruments
        for instrument in instruments:
            setattr(self, instrument, instruments[instrument])
            if instrument == 'daq':
                for ch in self._daq_inputs:
                    if ch not in self.daq.inputs:
                        raise Exception('Need to set daq input labels! \
                                        Need a %s' %ch)
                for ch in self._daq_outputs:
                    if ch not in self.daq.outputs:
                        raise Exception('Need to set daq output labels! \
                                        Need a %s' %ch)


    def check_instruments(self):
        '''
        Check to make sure all required instruments (specified in instrument
        list) are loaded.
        '''
        for i in self.instrument_list:
            if not hasattr(self, i):
                raise Exception('Instrument %s not loaded. Cannot run Measurement!' %i)


    def do(self):
        '''
        Do the main part of the measurement. Write this function for subclasses.
        run() wraps this function to enable keyboard interrupts.
        run() also includes saving and elapsed time logging.
        '''
        pass


    @classmethod
    def load(cls, filename=None, instruments={}):
        '''
        Call Saver's load method and then load instruments from a dictionary.
        '''
        obj = cls._load(filename)
        try:
            obj._load_instruments(instruments)
        except:  # in case we loaded as a Saver
            pass
        return obj


    def run(self, plot=True, **kwargs):
        '''
        Wrapper function for do() that catches keyboard interrrupts
        without leaving open DAQ tasks running. Allows scans to be
        interrupted without restarting the python instance afterwards

        Keyword arguments:
            plot: boolean; to plot or not to plot?

        Check the do() function for additional available kwargs.
        '''
        self.interrupt = False
        done = None

        # Before the do.
        if plot:
            self.setup_plots()
        time_start = time.time()

        self.check_instruments()

        # The do.
        try:
            done = self.do(**kwargs)
        except KeyboardInterrupt:
            print('interrupting kernel, please wait...\n')
            self.interrupt = True
            self._exception_info = traceback.format_exc()
        except:
            self._exception_info = traceback.format_exc()

        # After the do.
        time_end = time.time()
        self.time_elapsed_s = time_end-time_start

        if self.time_elapsed_s < 60: # less than a minute
            t = self.time_elapsed_s
            t_unit = 'seconds'
        elif self.time_elapsed_s < 3600: # less than an hour
            t = self.time_elapsed_s/60
            t_unit = 'minutes'
        else:
            t = self.time_elapsed_s/3600
            t_unit = 'hours'
        # Print elapsed time e.g. "Scanplane took 2.3 hours."
        print('%s took %.1f %s.' %(self.__class__.__name__, t, t_unit))

        self.save()

        # If this run is in a loop, then we want to raise the KeyboardInterrupt
        # to terminate the loop.
        if self.interrupt:
            raise KeyboardInterrupt

        return done


class FakeMeasurement(Measurement):
    '''
    Fake measurement to test methods a real measurement would have.
    '''
    def __init__(self):
        self.x = np.linspace(-10,10,20)
        self.y = np.full(self.x.shape, np.nan)

    def do(self):
        for i in range(len(self.x)):
            time.sleep(.1)
            self.y[i] = self.x[i]**2
            self.plot()

    def plot(self):
        super().plot()
        self.line.set_data(self.x, self.y)
        self.fig.tight_layout()

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.plot_draw()

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.line = self.ax.plot(self.x, self.y)[0]
        self.ax.set_xlabel('x')
        self.ax.set_ylabel('y')
