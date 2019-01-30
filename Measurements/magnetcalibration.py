import time, numpy as np, matplotlib.pyplot as plt
from Nowack_Lab.Measurements.measurement import Measurement

class MagnetCalibration(Measurement):
    '''
    Calibrate room temperature magnet coil constant and Hall coefficient

    Use a Lakeshore 425 Gaussmeter with Hall probe in the center of the magnet poles
    and a Hall sensor taped to one of the magnet poles.
    Hall sensor voltage leads (higher resistance) connected to Zurich Aux out 4 at 4 V
    Hall sensor current leads connected to Zurich Aux in 2
    '''
    instrument_list = ['gaussmeter', 'zurich', 'magnet']
    def __init__(self, instruments={}, Imax=10, Irate=6):
        '''
        Imax (Amperes): max current to sweep to
        Irate (Ampere/min): Sweep rate
        '''
        super().__init__(instruments=instruments)

        self.t = np.array([]) # Time
        self.VH = np.array([]) # Hall voltage
        self.B = np.array([]) # Reading from gaussmeter
        self.I = np.array([]) # Current in magnet

        self.Imax = Imax
        self.Irate = Irate

        # convert to field
        self.Bmax = self.Imax * self.magnet._coilconst
        self.Brate = self.Irate * self.magnet._coilconst


    def get_bias_voltage(self):
        '''
        Returns the voltage of Zurich Aux Out 4 used to bias the Hall probe
        '''
        z = self.zurich
        return z.daq.getDouble('/%s/auxouts/3/value' %(z.device_id))

    def get_Hall_voltage(self):
        '''
        Returns the voltage of Zurich Aux In 2 used to read the Hall voltage
        '''
        z = self.zurich
        t, V = z.get_scope_trace(self.zurich.freq_opts[10], input_ch=9) # aux in 2

        return V.mean()

    def do(self, **kwargs):

        # Start at zero
        self.magnet.ramp_to_field(0, self.Brate, wait=True)

        # Sweep down
        self.magnet.ramp_to_field(-self.Bmax, self.Brate, wait=False)

        while self.magnet.status == 'RAMPING':
            self.do_measurement()

        # Full sweep up
        self.magnet.ramp_to_field(self.Bmax, self.Brate, wait=False)

        while self.magnet.status == 'RAMPING':
            self.do_measurement()

        # Sweep back to zero
        self.magnet.ramp_to_field(0, self.Brate, wait=False)

        while self.magnet.status == 'RAMPING':
            self.do_measurement()


    def do_measurement(self):
        self.t = np.append(self.t, time.time())
        self.VH = np.append(self.VH, self.get_Hall_voltage())
        self.B = np.append(self.B, self.gaussmeter.field)
        self.I = np.append(self.I, self.magnet.I)
        self.plot()


    def plot_update(self):
        '''
        Update the data for all plots.
        '''
        self.lines[0].set_xdata(self.I)
        self.lines[0].set_ydata(self.VH)

        self.lines[1].set_xdata(self.I)
        self.lines[1].set_ydata(self.B*1000)

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.ax2.relim()
        self.ax2.autoscale_view(True,True,True)

    def setup_plots(self):
        '''
        Setup plots
        '''
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('Magnet current (A)', fontsize=20)
        self.ax.set_ylabel('Hall voltage (V)', fontsize=20, color='C0')

        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel('Field (mT)', fontsize=20, color='C1')

        self.lines = {
            0: self.ax.plot(self.I, self.VH, 'C0')[0],
            1: self.ax2.plot(self.I , self.B*1000, 'C1')[0]
        }
        self.ax.set_title(self.filename)
        self.fig.tight_layout()
