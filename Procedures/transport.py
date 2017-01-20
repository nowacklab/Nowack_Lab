import time, numpy as np, matplotlib.pyplot as plt
from ..Utilities.save import Measurement

class RvsVg(Measurement):
    instrument_list = ['keithley', 'lockin_V', 'lockin_I']
    I_compliance = 1e-6 # 1 uA

    def __init__(self, instruments = {}, Vmin = -10, Vmax = 10, Vstep=.1, delay=1):
        super().__init__()
        self._load_instruments(instruments)

        self.Vmin = Vmin
        self.Vmax = Vmax
        self.Vstep = Vstep
        self.delay = delay

        self.Vg = np.linspace(Vmin, Vmax, round(abs(Vmax-Vmin)/Vstep), endpoint=False)

        ## Decided to not measure during sweeps to/from min/max
        # Vup = np.linspace(0, Vmax, round(abs(Vmax)/Vstep), endpoint=False)
        # Vdown = np.linspace(Vmax, Vmin, round(abs(Vmax-Vmin)/Vstep), endpoint=False)
        # Vup2 = np.linspace(Vmin, 0, round(abs(Vmin)/Vstep), endpoint=False)

        # self.Vg = np.concatenate((Vup, Vdown, Vup2))

        self.Ig = np.full(self.Vg.shape, np.nan)
        self.Vx = np.full(self.Vg.shape, np.nan)
        self.Vy = np.full(self.Vg.shape, np.nan)
        self.Ix = np.full(self.Vg.shape, np.nan)
        self.Iy = np.full(self.Vg.shape, np.nan)
        self.R = np.full(self.Vg.shape, np.nan)

        self.setup_keithley()
        self.setup_lockins()


    def do(self):
        self.setup_plots()

#         self.keithley.output = 'on' #NO! will cause a spike!

        ## Sweep down to Vmin
        self.keithley.sweep_V(0, self.Vmin, 1)

        ## Do the measurement sweep
        for i, Vg in enumerate(self.Vg):
            self.keithley.Vout = Vg
            time.sleep(self.delay)

            self.Ig[i] = self.keithley.I
            self.Vx[i] = self.lockin_V.X
            self.Vy[i] = self.lockin_V.Y
            self.Ix[i] = self.lockin_I.X
            self.Iy[i] = self.lockin_I.Y
            self.R[i] = self.Vx[i]/self.Ix[i]

            self.plot()

        ## Sweep back to zero at 1V/s
        self.keithley.zero_V(1)
#         self.keithley.current = 0
#         self.keithley.output = 'off'
        self.save()

    def plot(self):
        super().plot()
        
        self.line.set_ydata(self.R)
        self.lineIg.set_ydata(self.Ig*1e9)

        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.axIg.relim()
        self.axIg.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def setup_keithley(self):
        self.keithley.zero_V()
        self.keithley.source = 'V'
        self.keithley.I_compliance = self.I_compliance
        self.keithley.Vout_range = abs(self.Vg).max()

    def setup_lockins(self):
        self.lockin_V.input_mode = 'A-B'
        self.lockin_I.input_mode = 'I (10^8)'
        self.lockin_V.reference = 'internal'
#         self.lockin_V.frequency = 53.01
        self.lockin_I.reference = 'external'

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('Vg (V)', fontsize=20)
        self.ax.set_ylabel('R (Ohm)', fontsize=20)

        self.axIg = self.ax.twinx()
        self.axIg.set_ylabel('Ig (nA)', fontsize=20, color='r')

#         self.ax.set_xlim(min(self.Vg), max(self.Vg))

        line = self.ax.plot(self.Vg, self.R, 'k')
        self.line = line[0]

        lineIg = self.axIg.plot(self.Vg, self.Ig*1e9, 'r')
        self.lineIg = lineIg[0]

        self.ax.set_title(self.filename)

    def Vg_to_n(self, t_ox = 300):
        '''
        Converts gate voltage to an approximate carrier density.
        t_ox is the thickness of the oxide in nm. Default 300 nm.
        '''
        eps_SiO2 = 3.9
        eps0 = 8.854187817e-12 #F/m
        e = 1.60217662e-19 #coulombs
        self.n = self.Vg*eps0*eps_SiO2/(t*1e-9*e)/100**2 # convert to cm^-2
