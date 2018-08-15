import numpy as np
import time
import matplotlib.pyplot as plt
from Nowack_Lab.Utilities.datasaver import Saver
from IPython.display import clear_output


class dcnuke():

    def __init__(instruments, sweeprange, numpoints = 2000, sweeprate = 1000,
                sweepcount = 1, bi = True, plot = True, samplename = '',
                                                                bfield = '1mT'):
        self.sweepbidir = alexsweep.Sweep("Iterator sweep", bi = False,
                                                              saveatend = False)
        self.sweepbidir.set_points(sweepcount)
        svr = Saver()
        self.sweepname = ("Sweep of frequency on %s NQR with %s Bz"
                                                        % (samplename, bfield))
        forwardsweep = alexsweep.Sweep(self.sweepname,svr = svr, bi = bi,
                                           saveatend = False, saveasyougo=True)
        forwardsweep.set_points(numpoints)
        forwardfreqs = np.linspace(sweeprange[0],sweeprange[1],num = numpoints)
        osc1freq = alexsweep.Active(bigz,"OSCS_0_FREQ","Field Coil Frequency",
                                                                  forwardfreqs)
        forwardsweep.add_repeater(osc1freq)
        wait_each_point = alexsweep.Delayer((sweeprange[1] - sweeprange[0])/
                                                        (sweeprate * numpoints))
        forwardsweep.add_repeater(wait_each_point)
        squidname = "DC SQUID SIGNAL %sx gain" % str(instruments['preamp'].gain)
        record_dcflux = alexsweep.Recorder(daq.ai6, "V", squidname )
        forwardsweep.add_repeater(record_dcflux)
        self.sweepbidir.add_repeater(forwardsweep)

    def __call__(self, n):
        self.sweepbidir(n)        
