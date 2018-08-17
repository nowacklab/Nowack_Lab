import numpy as np
import time
import matplotlib.pyplot as plt
from Nowack_Lab.Utilities.datasaver import Saver
import numpy as np
from IPython.display import clear_output
from Nowack_Lab.Procedures import alexsweep


class dcnuke():

    def __init__(self, instruments, sweeprange, svr, numpoints = 2000,
                sweeprate = 1000, sweepcount = 1, bi = True, plot = True,
                                            samplename = '', bfield = '1mT'):

        self.sweepname = ("Sweep of frequency on %s NQR with %s Bz"
                                                        % (samplename, bfield))
        self.freqsweep = alexsweep.Sweep(self.sweepname,svr = svr, bi = bi,
                                                        runcount = sweepcount)
        self.freqsweep.set_points(numpoints)
        forwardfreqs = np.linspace(sweeprange[0],sweeprange[1],num = numpoints)
        osc1freq = alexsweep.Active(instruments['lockin_squid'],"OSCS_0_FREQ",
                                        "Field Coil Frequency", forwardfreqs)
        self.freqsweep.add_repeater(osc1freq)
        wait_each_point = alexsweep.Delayer((sweeprange[1] - sweeprange[0])/
                                                        (sweeprate * numpoints))
        self.freqsweep.add_repeater(wait_each_point)
        squidname = "DC SQUID SIGNAL %sx gain" % str(instruments['preamp'].gain)
        record_dcflux = alexsweep.Recorder(instruments['daq'].ai6,
                                                                 "V", squidname)
        self.freqsweep.add_repeater(record_dcflux)

    def __call__(self, n):
        data = self.freqsweep(n)
        return data

class dcnukescan():

    def __init__(self, instruments, plane=None, span=[800, 800], movedelay =10,
                 center=[0, 0], numpts=[10, 10], sweeprange = [300e3, 400e3],
                 scanheight=15, numfreqs = 2000, sweeprate = 1000,
                             sweepcount = 1, bi = True,  samplename = '',
                              bfield = '1mT'):
            self.svr = Saver(name = 'DC_Nuke_Scan_of_%sat_%s' % (samplename,
                                                                        bfield))
            self.sweeprange = sweeprange
            self.instruments =  instruments
            self.plane = plane
            self.span = span
            self.center = center
            self.numpts = numpts
            self.scanheight = scanheight
            self.movedelay = movedelay
            self.singlenuke = dcnuke(instruments, sweeprange, self.svr,
                                   numpoints = numfreqs, sweeprate = sweeprate,
                                    sweepcount = sweepcount, bi = bi,
                                    plot = False, samplename = '',
                                                              bfield = '1mT'  )
            xs = np.linspace(center[0] - span[0]/2, center[0] + span[0]/2,
                                                                    numpts[0])
            ys = np.linspace(center[1] - span[1]/2, center[1] + span[1]/2,
                                                                    numpts[1])
            self.coords = [] #list of coords to scan
            for x in xs:
                for y in xs:
                    self.coords.append({'x': x, 'y': y, 'z':
                                                 plane.plane(x,y) - scanheight})
    def run(self):
        # Measure capacitance offset
        Vcap_offset = []
        self.svr.append('/config/zurich', self.instruments['lockin_squid'].__getstate__())
        self.svr.append('/config/pa', self.instruments['preamp'].__getstate__())
        for i in range(5):
            time.sleep(0.5)
            Vcap_offset.append(
                self.instruments['lockin_cap'].convert_output(
                self.instruments['daq'].inputs['cap'].V))
        Vcap_offset = np.mean(Vcap_offset)
        # Scan
        for i in range(len(self.coords)):
            pz = self.instruments['piezos']
            nextposition = self.coords[i]
            pz.z.V = -400
            pz.x.V = nextposition['x']
            pz.y.V = nextposition['y']
            pz.z.V = nextposition['z']
            time.sleep(self.movedelay)
            self.singlenuke(i)
            self.svr.append('/initialization: %s/coords/' % str(i), nextposition)
            self.svr.append('/initialization: %s/cap/' % str(i), self.instruments['lockin_cap']
                    .convert_output(self.instruments['daq'].inputs['cap'].V))
        return self.svr
