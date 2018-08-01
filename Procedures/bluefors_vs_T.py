import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import time

from ..Utilities.save import Measurement
from ..Utilities.utilities import AttrDict
from ..Instruments.lakeshore import Lakeshore372


class Bluefors_vs_T(Measurement):
    '''
    Log some parameter repsect to temperature in bluefors
    '''

    instrument_list=['lakeshore']

    def __init__(self, instruments={}):
        super().__init__(instruments=instruments)

class R_vs_T(Bluefors_vs_T):
    '''
    Log resistances vs bluefors temperature using two lockins
    '''

    instrument_list=['lockin_I', 'lockin_V', 'lakeshore']

    def __init__(self, 
                 instruments={},
                 lakeshore_channel=6,
                 meas_dur = 43200,  # duration in secs
                 timestep = 10,     # time between samples in sec
                ):
        '''
        Log resistance vs bluefors temperature with 2 lockins.
        Made for a 4 point resistance measurement with SR830s

        arguments:
            instruments:    instrument dictionary.  requires 
                                'lockin_I' : lockin for current SR830
                                'lockin_V' : lockin for voltage SR830
                                'lakeshore': bluefors Lakeshore372

        returns:
            none
        '''
        super().__init__(instruments=instruments)

        for arg in ['lakeshore_channel',
                    'meas_dur',
                    'timestep'
                   ]:
            setattr(self,arg,eval(arg))
        
    def do(self):
        '''
        '''
        # setup scan
        self.starttime  = datetime.now()
        self.endtime    = self.starttime + timedelta(seconds=self.meas_dur)
        self.numsteps   = int(np.ceil(self.meas_dur/self.timestep))

        self.lockinI_X   = np.zeros(self.numsteps)
        self.lockinI_Y   = np.zeros(self.numsteps)
        self.lockinV_X   = np.zeros(self.numsteps)
        self.lockinV_Y   = np.zeros(self.numsteps)
        self.temperature = np.zeros(self.numsteps)
        self.sleeptimes  = np.zeros(self.numsteps)


        for i in range(self.numsteps):
            lastmeastime = datetime.now();

            self.lockinI_X[i]   = self.lockin_I.X
            self.lockinI_Y[i]   = self.lockin_I.Y
            self.lockinV_X[i]   = self.lockin_V.X
            self.lockinV_Y[i]   = self.lockin_V.Y
            self.temperature[i] = self.lakeshore.T[self.lakeshore_channel]

            print('At {0}K: Rx={1}'.format(self.temperature[i], 
                    self.lockinV_X[i]/self.lockinI_X[i]))

            # live plotting
            self.plot(i)

            # ensure constant measure interval
            # maybe do something so that will measure faster 
            # if resistance is changing faster?
            sleeptime = ( self.timestep - 
                          (lastmeastime-datetime.now()).total_seconds()
                        ) 
            self.sleeptimes[i]  = sleeptime

            if sleeptime > 0:
                time.sleep(sleeptime)

        self.lakeshore.setchsettings(prev_lakeshore_settings)

        #HACK FIXME
        del self.lakeshore.__dict__['_visa_handle']
            
    def setup_plots(self):
        '''
        '''
        self.fig = plt.figure(figsize=(12,6))
        self.ax = AttrDict()
        self.ax['X'] = self.fig.add_subplot(121)
        self.ax['Y'] = self.fig.add_subplot(122)
        
        self.ax['X'].set_ylabel('Resistance X (ohm)')
        self.ax['Y'].set_ylabel('Resistance Y (ohm)')

        self.notes = "{0}\nch={1}\n[timestep,meas_dur]=[{2},{3}]".format(
                        self.timestamp, self.lakeshore_channel,
                        self.timestep, self.meas_dur)

        for ax in self.ax.values():
            ax.set_xlabel('Temperature (K)')
            ax.annotate(self.notes,
                    xy=(.02,.98), xycoords='axes fraction',ha='left',va='top',
                    fontsize=10, family='monospace')

        self._points = AttrDict()
        self._points['X'] = self.ax['X'].plot([],[],
                                             marker='o', markersize=2, 
                                             linestyle='-')[0]
        self._points['Y'] = self.ax['Y'].plot([],[],
                                             marker='o', markersize=2, 
                                             linestyle='-')[0]

    def plot(self, plotindex=0):
        '''
        Live plotting
        '''

        # update plot
        self._points['X'].set_xdata(self.temperature[:plotindex])
        self._points['X'].set_ydata(self.lockinV_X[:plotindex]/
                                    self.lockinI_X[:plotindex])
        self._points['Y'].set_xdata(self.temperature[:plotindex])
        self._points['Y'].set_ydata(self.lockinV_Y[:plotindex]/
                                    self.lockinI_Y[:plotindex])
        plt.pause(0.01)
        for ax in self.ax.values():
            ax.relim()
            ax.autoscale_view(True,True,True)
        self.fig.tight_layout()
        self.fig.canvas.draw()

class R_vs_T_ac(Bluefors_vs_T):
    instrument_list = ['lakeshore', 'lockin']
    def __init__(self,
                 instruments,
                 current,
                 gain,
                 duration = 10000,
                 timestep=10):
        super().__init__(instruments=instruments)
        self.duration = duration
        self.timestep = timestep
        self.current = current
        self.gain = gain
        self.T = []
        self.Vx = []
        self.Vy = []

    def do(self):
        start = time.time()
        try:
            print("starting")
            while ((time.time() - start) < self.duration):
                time.sleep(self.timestep)
                self.Vx.append(self.lockin.X)
                self.Vy.append(self.lockin.Y)
                self.T.append(self.lakeshore.chan6.T)
        except KeyboardInterrupt:
            print("interrupting.")
            
        self.Vx = np.array(self.Vx) / self.gain
        self.Vy = np.array(self.Vy) / self.gain
        self.T = np.array(self.T)
        self.R = self.Vx / self.current
        
                 
                 
                 
        
class R_vs_T_dc(Bluefors_vs_T):
    '''
    Log resistances vs bluefors temperature DC
    '''

    instrument_list=['preamp', 'lakeshore', 'keithley']

    def __init__(self, 
                 instruments={},
                 lakeshore_channel=6,
                 meas_dur = 43200,  # duration in secs
                 timestep = 10,     # time between samples in sec
                 dcbiascurrents = [1e-3],
                 rampptsleep = .01
                ):
        '''

        arguments:
            instruments:    instrument dictionary.  requires 
                                'lakeshore': bluefors Lakeshore372

        returns:
            none
        '''
        super().__init__(instruments=instruments)

        for arg in ['lakeshore_channel',
                    'meas_dur',
                    'timestep',
                    'dcbiascurrents',
                    'rampptsleep'
                   ]:
            setattr(self,arg,eval(arg))
        
    def do(self, daqchannel=''):
        '''
        daqchannel is an Nowack_Lab.Instruments.nidaq.InputChannel 
        like daq.ai7
        '''
        # disable other channels so can update fast!
        #prev_lakeshore_settings = self.lakeshore.getchsettings()
        self.lakeshore.enable_only(self.lakeshore_channel)

        # store lakeshore channel settings
        # self.lakeshoreparams = self.lakeshore.getchsettings()

        # setup scan
        self.starttime  = datetime.now()
        self.endtime    = self.starttime + timedelta(seconds=self.meas_dur)
        self.numsteps   = int(np.ceil(self.meas_dur/self.timestep))

        self.Vs   = np.zeros((self.numsteps, len(self.dcbiascurrents)))
        self.Is   = np.zeros((self.numsteps, len(self.dcbiascurrents)))
        self.Ts   = np.zeros(self.numsteps)
        self.Rfits= np.zeros((self.numsteps, 2))
        self.covar= np.zeros((self.numsteps, 2, 2))
        self.sleeptimes = np.zeros(self.numsteps)
        

        for i in range(self.numsteps):
            lastmeastime = datetime.now();
            self.Is[i] = self.dcbiascurrents
            self.Ts[i] = self.lakeshore.T[self.lakeshore_channel]

            for j in range(len(self.Is[i])):

                self.keithley.Iout = self.Is[i][j]
                time.sleep(self.rampptsleep)
                
                self.Vs[i][j] = daqchannel.V/self.preamp.gain #FIXME

            for j in range(len(self.Is[i])):
                self.keithley.Iout = self.Is[i][-j]
                time.sleep(self.rampptsleep)

            [p, covar] = np.polyfit(self.Is[i], self.Vs[i], deg=1, cov=True)
            self.Rfits[i] = p
            self.covar[i] = covar
            
            print(r'At {0:2.2f}K: R={1:2.2e}+/-{2:2.2e}, offset={3:2.2e}'.format(
                    self.Ts[i], 
                    self.Rfits[i][0], np.sqrt(self.covar[i][0][0]),
                    self.Rfits[i][1]))

            # live plotting
            #self.plot(i)

            # ensure constant measure interval
            # maybe do something so that will measure faster 
            # if resistance is changing faster?
            sleeptime = ( self.timestep - 
                          (lastmeastime-datetime.now()).total_seconds()
                        ) 
            self.sleeptimes[i]  = sleeptime

            if sleeptime > 0:
                time.sleep(sleeptime)

        self.lakeshore.enable_all()

    def setup_plots(self):
        '''
        '''
        pass
#        self.fig, self.ax = plt.subplots()
#        
#        self.ax.set_xlabel('T (K)')
#        self.ax.set_ylabel(r'Resistance ($\Omega$)')
#
#        self.notes = "{0}\nch={1}\n[timestep,meas_dur]=[{2},{3}]".format(
#                        self.timestamp, self.lakeshore_channel,
#                        self.timestep, self.meas_dur)
#
#        self.ax.annotate(self.notes,
#                    xy=(.02,.98), xycoords='axes fraction',ha='left',va='top',
#                    fontsize=10, family='monospace')
#
#        self._points = self.ax.plot([],[], marker='o', markersize=2, 
#                                             linestyle='-')[0]

    def plot(self, plotindex=0):
        '''
        Live plotting
        '''
        pass
#        # update plot
#        self._points.set_xdata(np.mean(self.Ts[plotindex]))
#        self._points.set_ydata(self.Rfit[plotindex][0])
#
#        plt.pause(0.01)
#        ax.relim()
#        ax.autoscale_view(True,True,True)
#        self.fig.tight_layout()
#        self.fig.canvas.draw()