import numpy as np
from numpy.linalg import lstsq
from . import navigation, planefit
import time, os
from scipy.interpolate import interp1d as interp
import matplotlib.pyplot as plt
from IPython import display
from numpy import ma
from ..Utilities import dummy, plotting
from ..Instruments import piezos, nidaq, montana, squidarray
from ..Utilities.save import Measurement
from scipy.interpolate import spline
from scipy import signal

class Scanplane(Measurement):
    def __init__(self, instruments=None, span=[100,100], center=[0,0], numpts=[50,50], plane=dummy.Dummy(planefit.Planefit), scanheight=5, sig_in=0, cap_in=1, sig_in_ac_x=None, sig_in_ac_y=None):
        if instruments:
            self.piezos = instruments['piezos']
            self.daq = instruments['nidaq']
            self.montana = instruments['montana']
            # self.array = instruments['squidarray']
        else:
            self.piezos = dummy.Dummy(piezos.Piezos)
            self.daq = dummy.Dummy(nidaq.NIDAQ)
            self.montana = dummy.Dummy(montana.Montana)
            # self.array = dummy.Dummy(squidarray.SquidArray)

        self.sig_in = 'ai%s' %sig_in
        self.daq.add_input(self.sig_in)

        self.sig_in_ac_x = 'ai%s' %sig_in_ac_x
        self.daq.add_input(self.sig_in_ac_x)

        self.sig_in_ac_y = 'ai%s' %sig_in_ac_y
        self.daq.add_input(self.sig_in_ac_y)

        self.cap_in = 'ai%s' %cap_in
        self.daq.add_input(self.cap_in)

        self.span = span
        self.center = center
        self.numpts = numpts

        self.plane = plane
        if scanheight < 0:
            inp = input('Scan height is negative, SQUID will ram into sample! Are you sure you want this? If not, enter \'quit.\'')
            if inp == 'quit':
                raise Exception('Terminated by user')
        self.scanheight = scanheight

        self.x = np.linspace(center[0]-span[0]/2, center[0]+span[0]/2, numpts[0])
        self.y = np.linspace(center[1]-span[1]/2, center[1]+span[1]/2, numpts[1])

        self.X, self.Y = np.meshgrid(self.x, self.y, indexing='ij') # indexing ij follows matrix indexing convention
        self.Z = self.plane.plane(self.X, self.Y) - self.scanheight

        self.V = np.full(self.X.shape, np.nan)
        self.Vac_x = np.full(self.X.shape, np.nan)
        self.Vac_y = np.full(self.X.shape, np.nan)
        self.C = np.full(self.X.shape, np.nan)

        self.last_full_out = []
        self.last_full_sweep = []
        self.last_interp_out = []
        self.last_interp_sweep = []
        self.linecuts = {}

        # self.swap = swap
        # if swap: # Will rotate scan 90 degrees? Not really tested. Got bugs if false. Keep it true for now. #20160717: just noticed kwarg default is False. Don't touch this for now...
        #     self.X = self.X.transpose()
        #     self.Y = self.Y.transpose()
        #     self.Z = self.Z.transpose()

        self.filename = ''

        home = os.path.expanduser("~")
        self.path = os.path.join(home,
                                'Dropbox (Nowack lab)',
                                'TeamData',
                                'Montana',
                                'Scans'
                            )

    def __getstate__(self):
        self.save_dict = {"timestamp": self.timestamp,
                          "piezos": self.piezos,
                          "daq": self.daq,
                          "montana": self.montana,
                          "array": self.array,
                          "linecuts": self.linecuts,
                          "V": self.V,
                          "Vac_x": self.Vac_x,
                          "Vac_y": self.Vac_y,
                          "C": self.C,
                          "plane": self.plane,
                          "span": self.span,
                          "center": self.center,
                          "numpts": self.numpts}
        return self.save_dict

    def do(self):
        self.setup_plots()

        ## Start time and temperature
        self.filename = time.strftime('%Y%m%d_%H%M%S') + '_scan'
        self.timestamp = time.strftime("%Y-%m-%d @ %I:%M:%S%p")
        tstart = time.time()
        self.temp_start = self.montana.temperature['platform']

        ## make sure all points are not out of range of piezos before starting anything
        for i in range(self.X.shape[0]):
            self.piezos.check_lim({'x':self.X[i,:],
                                    'y':self.Y[i,:],
                                    'z':self.Z[i,:]
                                    }
                                )

        ## Loop over Y values
        for i in range(self.X.shape[1]):

            ## Explicitly go to first point of scan
            self.piezos.V = {'x': self.X[0,i],
                            'y': self.Y[0,i],
                            'z': self.Z[0,i]
                            }
            # self.array.reset()
            time.sleep(3)

            ## Do the sweep
            # Vstart = {'x': self.X[0,i], 'y': self.Y[0,i], 'z': self.Z[0,i]}
            # Vend = {'x': self.X[-1,i], 'y': self.Y[-1,i], 'z': self.Z[-1,i]}
            # out, V, t = self.piezos.sweep(Vstart, Vend) # sweep over X

            ## Do the sweep with PID
            Vstart = {'x': self.X[0,i], 'y': self.Y[0,i], 'z': self.Z[0,i]}
            Vend = {'x': self.X[-1,i], 'y': self.Y[-1,i], 'z': self.Z[-1,i]}
            out = {}
            V = {self.sig_in: [], self.sig_in_ac_x: [], self.cap_in: []}

            numsteps=50
            out['x'] = np.linspace(Vstart['x'], Vend['x'], numsteps)
            out['y'] = np.linspace(Vstart['y'], Vend['y'], numsteps)
            out['z'] = np.linspace(Vstart['z'], Vend['z'], numsteps)

            ## PID STUFF
            P=0.05
            I=7
            D=0
            desired_voltage = 0
            start_voltage = 0
            pid = PID(P, I, D)
            pid.SetPoint = desired_voltage
            pid.setSampleTime(.000001)

            t0 = time.time()

            feedback_list = []
            time_list = []
            setpoint_list = []
            act_time = []
            thermo_voltage = []
            graph_voltage = []
            self.daq.ao0 = start_voltage
            pid.output = start_voltage
            pid.ITerm = desired_voltage

            err_thresh = 0.009
            pid.last_error = err_thresh*1.1 #cheating so while loop will run

            Vlim = 10

            import winsound
            winsound.Beep(457,500) # it will beep if it reaches this point


            # Initialize feedback so voltage is zero
            while pid.last_error >= err_thresh or pid.last_error <= -err_thresh:
                Vin = self.daq.ai0
                thermo_voltage.append(Vin)
                pid.update(thermo_voltage[-1])
                time.sleep(0.02)
                feedback = pid.output

                if feedback > Vlim:
                    feedback = Vlim
                elif feedback < -Vlim:
                    feedback = -Vlim
                self.daq.ao0 = feedback

            winsound.Beep(500,500) # it will beep if it reaches this point
            winsound.Beep(500,500) # it will beep if it reaches this point


            for j in range(numsteps):
                self.piezos.V = {'x':out['x'][j], 'y':out['y'][j], 'z':out['z'][j]} # move to the next step

                pid.last_error = 0

                Vin = self.daq.ai0
                graph_voltage.append(Vin)
                pid.update(graph_voltage[-1])
                time.sleep(0.02)
                feedback2 = pid.output

                if feedback2 > Vlim:
                    feedback2 = Vlim
                elif feedback2 < -Vlim:
                    feedback2 = -Vlim
                self.daq.ao0 = feedback2

                time_list.append(i)
                feedback_list.append(feedback2)
                act_time.append(pid.current_time)

                V[self.sig_in].append(feedback2) # voltage sent to mod
                V[self.sig_in_ac_x].append(Vin) # voltage input from array (want to keep at zero)
                V[self.cap_in].append(getattr(self.daq, self.cap_in))

            winsound.Beep(600,500) # it will beep if it reaches this point
            winsound.Beep(600,500) # it will beep if it reaches this point
            winsound.Beep(600,500) # it will beep if it reaches this point



            ### DONE WITH PID stuff

            V[self.sig_in_ac_y] = V[self.sig_in]

            ## Save linecuts
            self.linecuts[str(i)] = {"Vstart": Vstart,
                                "Vend": Vend,
                                "Vsquid": {"Vdc": V[self.sig_in],
                                           "Vac_x": V[self.sig_in_ac_x],
                                           "Vac_y": V[self.sig_in_ac_y]}}

            ## Interpolate to the number of lines
            interp_func = interp(out['x'], V[self.sig_in])
            self.V[:,i] = interp_func(self.X[:,i]) # changes from actual output data to give desired number of points

            interp_func = interp(out['x'], V[self.sig_in_ac_x])
            self.Vac_x[:,i] = interp_func(self.X[:,i])

            interp_func = interp(out['x'], V[self.sig_in_ac_y])
            self.Vac_y[:,i] = interp_func(self.X[:,i])

            interp_func = interp(out['x'], V[self.cap_in])
            self.C[:,i] = interp_func(self.X[:,i])

            self.last_full_out = out['x']
            self.last_full_sweep = V[self.sig_in]
            self.save_line(i, Vstart)

            self.last_interp_out = self.X[:,i]
            self.last_interp_sweep = self.V[:,i]

            self.plot()

        self.piezos.V = 0
        self.save()

        tend = time.time()
        print('Scan took %f minutes' %((tend-tstart)/60))
        return


    def plot(self):
        '''
        Update all plots.
        '''
        plotting.update2D(self.im_squid, self.V)
        plotting.update2D(self.im_cap, self.C)
        plotting.update2D(self.im_ac_x, self.Vac_x)
        plotting.update2D(self.im_ac_y, self.Vac_y)
        self.plot_line()

        self.fig.canvas.draw()


    def setup_plots(self):
        '''
        Set up all plots.
        '''
        self.fig = plt.figure(figsize=(11,11))

        ## DC magnetometry
        self.ax_squid = self.fig.add_subplot(321)
        self.im_squid = plotting.plot2D(self.ax_squid,
                                        self.X,
                                        self.Y,
                                        self.V,
                                        title = '%s\nDC SQUID signal' %self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'Voltage from %s' %self.sig_in
                                    )

        ## AC x
        self.ax_ac_x = self.fig.add_subplot(323)
        self.im_ac_x = plotting.plot2D(self.ax_ac_x,
                                        self.X,
                                        self.Y,
                                        self.Vac_x,
                                        cmap='rainbow',
                                        title = '%s\nAC x SQUID signal' %self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'Voltage from %s' %self.sig_in_ac_x
                                    )

        ## AC y
        self.ax_ac_y = self.fig.add_subplot(325)
        self.im_ac_y = plotting.plot2D(self.ax_ac_y,
                                        self.X,
                                        self.Y,
                                        self.Vac_y,
                                        cmap='rainbow',
                                        title = '%s\nAC y SQUID signal' %self.filename,
                                        xlabel = r'$X (V_{piezo})$',
                                        ylabel = r'$Y (V_{piezo})$',
                                        clabel = 'Voltage from %s' %self.sig_in_ac_y
                                    )

        ## Capacitance
        self.ax_cap = self.fig.add_subplot(324)
        self.im_cap = plotting.plot2D(self.ax_cap,
                                    self.X,
                                    self.Y,
                                    self.C,
                                    cmap='afmhot',
                                    title = '%s\nCapacitance' %self.filename,
                                    xlabel = r'$X (V_{piezo})$',
                                    ylabel = r'$Y (V_{piezo})$',
                                    clabel = 'Voltage from %s' %self.cap_in
                                )

        ## "Last full scan" plot
        self.ax_line = self.fig.add_subplot(326)
        self.ax_line.set_title('last full line scan', fontsize=8)
        self.line_full = self.ax_line.plot(self.last_full_out, self.last_full_sweep, '-.k') # commas only take first element of array? ANyway, it works.
        self.line_interp = self.ax_line.plot(self.last_interp_out, self.last_interp_sweep, '.r', markersize=12)
        self.ax_line.set_xlabel('X (a.u.)', fontsize=8)
        self.ax_line.set_ylabel('V', fontsize=8)

        self.line_full = self.line_full[0] # it is given as an array
        self.line_interp = self.line_interp[0]

        ## Draw everything in the notebook
        self.fig.canvas.draw()


    def plot_line(self):
        self.line_full.set_xdata(self.last_full_out)
        self.line_full.set_ydata(self.last_full_sweep)
        self.line_interp.set_xdata(self.last_interp_out)
        self.line_interp.set_ydata(self.last_interp_sweep)

        self.ax_line.relim()
        self.ax_line.autoscale_view()

        plotting.aspect(self.ax_line, .3)

    def save(self):
        filename = os.path.join(self.path, self.filename)

        self.fig.savefig(filename+'.pdf')

        with open(filename+'.csv', 'w') as f:
            for s in ['span', 'center', 'numpts']:
                f.write('%s = %f, %f \n' %(s, float(getattr(self, s)[0]),float(getattr(self, s)[1])))
            for s in ['a','b','c']:
                f.write('plane.%s = %f\n' %(s, float(getattr(self.plane, s))))
            f.write('scanheight = %f\n' %self.scanheight)
            f.write('Montana info: \n'+self.montana.log()+'\n')
            f.write('starting temperature: %f' %self.temp_start)

            f.write('DC signal\n')
            f.write('X (V),Y (V),V (V)\n')
            for i in range(self.X.shape[0]):
                for j in range(self.X.shape[1]):
                    if self.V[i][j] != None:
                        f.write('%f' %self.X[i][j] + ',' + '%f' %self.Y[i][j] + ',' + '%f' %self.V[i][j] + '\n')

            f.write('AC x signal\n')
            f.write('X (V),Y (V),V (V)\n')
            for i in range(self.X.shape[0]):
                for j in range(self.X.shape[1]):
                    if self.Vac_x[i][j] != None:
                        f.write('%f' %self.X[i][j] + ',' + '%f' %self.Y[i][j] + ',' + '%f' %self.Vac_x[i][j] + '\n')

            f.write('AC y signal\n')
            f.write('X (V),Y (V),V (V)\n')
            for i in range(self.X.shape[0]):
                for j in range(self.X.shape[1]):
                    if self.Vac_y[i][j] != None:
                        f.write('%f' %self.X[i][j] + ',' + '%f' %self.Y[i][j] + ',' + '%f' %self.Vac_y[i][j] + '\n')


    def save_line(self, i, Vstart):
        filename = os.path.join(self.path, self.filename)

        with open(filename+'_lines.csv', 'a') as f:
            f.write('Line %i, starting at: ' %i)
            for k in Vstart:
                f.write(str(Vstart[k])+',')
            f.write('\n Vpiezo:\n ')
            for x in self.last_full_sweep:
                f.write(str(x)+',')
            f.write('\n Vsquid:\n')
            for x in self.last_full_out:
                f.write(str(x)+',')


class PID:
    def __init__(self, P=0.2, I=0.0, D=0.0):
        self.Kp = P
        self.Ki = I
        self.Kd = D

        self.sample_time = 0.0
        self.t0 = time.time()
        self.current_time = time.time()-self.t0
        self.last_time = self.current_time

        self.clear()

    def clear(self):
        self.SetPoint = 0.0

        self.PTerm = 0.0
        self.ITerm = 0.0
        self.DTerm = 0.0
        self.last_error = 0.0
#         Windup Guard
        self.int_error = 0.0
        self.windup_guard = 10.0

        self.output = 0.0

    def update(self, feedback_value):
        error = self.SetPoint - feedback_value

        self.current_time = time.time()-self.t0
        self.delta_time = self.current_time - self.last_time

        self.delta_error = self.last_error - error



        if (self.delta_time >= self.sample_time):
            self.PTerm = self.Kp * error

            self.ITerm += error * self.delta_time

            if (self.ITerm < -self.windup_guard):
                self.ITerm = -self.windup_guard
            elif (self.ITerm > self.windup_guard):
                self.ITerm = self.windup_guard

            self.DTerm = 0.0

            if self.delta_time > 0:
                self.DTerm = self.delta_error / self.delta_time
                self.last_time = self.current_time
                self.last_error = error

                self.output = self.PTerm + (self.Ki * self.ITerm) + (self.Kd * self.DTerm)


    def setKp(self, proportional_gain):
        self.Kp = proportional_gain
    def setKi(self, integral_gain):
        self.Ki = integral_gain
    def setKd(self, derivative_gain):
        self.Kd = derivative_gain

    def setWindup(self, windup):
        self.windup_guard = windup

    def setSampleTime(self, sample_time):
        self.sample_time = sample_time


if __name__ == '__main__':
    'hey'
