import time, numpy as np
from ..Utilities.save import Measurement

class RvsVg(Measurement):
    instrument_list = ['keithley', 'lockin_V', 'lockin_I']
    I_compliance = 1e-6 # 1 uA

    def __init__(self, instruments = {}, Vmin = -10, Vmax = 10, Vstep=.05, delay=.1):
        super().__init__()
        self._load_instruments(instruments)

        self.Vmin = Vmin
        self.Vmax = Vmax
        self.Vstep = Vstep
        self.delay = delay

        Vup = np.arange(0, Vmax, Vstep)
        Vdown = np.arange(Vmax, Vmin, -Vstep)
        Vup2 = np.arange(Vmin, 0, Vstep)

        self.Vg = np.concatenate((Vup, Vdown, Vup2))

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

        self.keithley.output = 'on'
        for i, Vg in enumerate(self.Vg):
            self.keithley.voltage = Vg
            time.sleep(self.delay)

            self.Ig[i] = self.keithley.current
            self.Vx[i] = self.lockin_V.X
            self.Vy[i] = self.lockin_V.Y
            self.Ix[i] = self.lockin_I.X
            self.Iy[i] = self.lockin_I.Y
            self.R[i] = self.Vx[i]/self.Ix[i]

            self.plot()

        self.keithley.zero()
#         self.keithley.current = 0
        self.keithley.output = 'off'
        self.save()

    def plot(self):
        self.line.set_ydata(self.R)
        self.ax.relim()
        self.ax.autoscale_view(True,True,True)

        self.fig.tight_layout()
        self.fig.canvas.draw()

    def setup_keithley(self):
        self.keithley.zero()
        self.keithley.mode = 'voltage'
        self.keithley.compliance_current = self.I_compliance
        self.keithley.voltage_range = abs(self.Vg).max()

    def setup_lockins(self):
        self.lockin_V.input_mode = 'A-B'
        self.lockin_I.input_mode = 'I (10^8)'
        self.lockin_V.reference = 'internal'
        self.lockin_V.frequency = 11.123
        self.lockin_I.reference = 'external'

    def setup_plots(self):
        self.fig, self.ax = plt.subplots()
        self.ax.set_xlabel('Vg (V)', fontsize=20)
        self.ax.set_ylabel('R (Ohm)', fontsize=20)

#         self.ax.set_xlim(min(self.Vg), max(self.Vg))

        line = self.ax.plot(self.Vg, self.R)
        self.line = line[0]
