
from Nowack_Lab.Procedures import alexsweep
import numpy as np
class zitransport():

    _measurements = ['RvsI', 'RvsGate']

    def __init__(self, rbias, lockin, currentinput = 0, dccurrentinput = 0,
                dccurrentoutput = 0, voltageinput = 1,  voltageoutput = 0,
                acamp = .01, TAchannel = 0, voltagerange = 2, currentrange = 2,
                outputrange = 1, TAgain = 1e6, freq = 17.76,
                voltagepreamp = False, externalvoltagegain = 1,
                maxdccurrent = 1e-3, maxgate = 110, maxgatecurrent = 20e-9,
                gate = False, estdevres = 1e5, timeconstant = 1):
        '''
        Initializes a transport measurement using a zurich HF2LI

        Args:

        rbias (float): resistance of bias resistor on SD bias.

        lockin (zurich object): a Zurich HF2LI object with which the transport
        is measured.

        currentinput (int): Zurich frontpanel number of current input. 0 or 1.

        dccurrentinput (int): Zurich auxin port for monitoring dc current.
                            0 or 1.

        voltageinput (int): Zurich frontpanel number of voltage input. 0 or 1.

        voltageoutput (int): Zurich frontpanel output for SD bias. 0 or 1.

        TAchannel (int): Zurich transimpedence amplifier channel used for monitoring
        drain current. 0 or 1.

        voltagerange (float): voltage input range

        currentrange (float): range of current lockin input, in units of
                                TAgain*current

        TAgain (float): Gain desired for Zurich HF2TA current preamp

        freq (float): lock in frequency

        voltagepreamp (float): a Stanford Research voltage preamplifier

        externalvoltagegain (float): any external gain on the voltage monitor,
                                    such as a preamp.

        maxdccurrent (float): maximum allowed dc current rbias

        maxgate (float): maximum allowed voltage on backgate

        gate (keithley or similar): must have a Vout setter, as well as
                                    V and I getters.

        estdevres (float): estimated resistance of device in ohms. Used to
                            tune PID

        '''
        self.rbias = rbias
        self.lockin = lockin
        self.currentinput = currentinput
        self.dccurrentinput = dccurrentinput
        self.voltageinput = voltageinput
        self.voltageoutput = voltageoutput
        self.TAchannel = TAchannel
        self.voltagepreamp = voltagepreamp
        self.externalvoltagegain = externalvoltagegain
        self.maxdccurrent = maxdccurrent
        self.maxgate = maxgate
        self.gate = gate
        self.estdevres = estdevres
        self.activemeasurement = None
        #configure the demods
        tampdc = 1
        if freq > 200:
            lockinac = 1
        else:
            lockinac = 0
        if voltageinput == 0 and currentinput == 1:
            self.voltagedemod = voltagedemod = 0
            self.currentdemod = currentdemod = 3
        elif voltageinput == 1 and currentinput == 0:
            self.voltagedemod = voltagedemod = 3
            self.currentdemod = currentdemod = 0
        else:
            raise Exception('Non-allowed inputs!')
        self.out_mix_ch = out_mix_ch = int(lockin.daq.listNodes(
         '/%s/sigouts/%d/amplitudes/' % (lockin.device_id, voltageinput),0)[0])
        exp_setting = [
['/%s/sigins/%d/ac'          % (lockin.device_id, voltageinput), lockinac],
['/%s/sigins/%d/ac'          % (lockin.device_id, currentinput), lockinac],
['/%s/sigins/%d/IMP50'       % (lockin.device_id, voltageinput), 0],
['/%s/sigins/%d/IMP50'       % (lockin.device_id, currentinput), 0],

['/%s/sigins/%d/range'       % (lockin.device_id, voltageinput), voltagerange],
['/%s/sigins/%d/diff'        % (lockin.device_id, voltageinput), 1],

['/%s/sigins/%d/range'       % (lockin.device_id, currentinput), currentrange],
['/%s/sigins/%d/diff'        % (lockin.device_id, currentinput), 0],


['/%s/demods/%d/enable'      % (lockin.device_id, 0), 1],
['/%s/demods/%d/enable'      % (lockin.device_id, 3), 1],
['/%s/demods/%d/timeconstant'      % (lockin.device_id, 0), timeconstant],
['/%s/demods/%d/timeconstant'      % (lockin.device_id, 3), timeconstant],
['/%s/demods/%d/rate'        % (lockin.device_id, 0), 1e3],
['/%s/demods/%d/rate'        % (lockin.device_id, 3), 1e3],
['/%s/demods/%d/order'       % (lockin.device_id, 0), 4],
['/%s/demods/%d/order'       % (lockin.device_id, 3), 4],
['/%s/demods/%d/oscselect'   % (lockin.device_id, 0), voltageoutput],
['/%s/demods/%d/oscselect'   % (lockin.device_id, 3), voltageoutput],
['/%s/demods/%d/harmonic'    % (lockin.device_id, 0), 1],
['/%s/demods/%d/harmonic'    % (lockin.device_id, 3), 1],


['/%s/demods/%d/adcselect'   % (lockin.device_id, voltagedemod), voltageinput],
['/%s/demods/%d/adcselect'   % (lockin.device_id, currentdemod), currentinput],

['/%s/pids/%d/ENABLE'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/INPUT'   % (lockin.device_id, 0), 4],
['/%s/pids/%d/INPUTCHANNEL'   % (lockin.device_id, 0), dccurrentinput],
['/%s/pids/%d/OUTPUT'   % (lockin.device_id, 0), 3],
['/%s/pids/%d/OUTPUTCHANNEL'   % (lockin.device_id, 0), dccurrentoutput],
['/%s/pids/%d/OUTPUTDEFAULTENABLE'   % (lockin.device_id, 0), 1],
['/%s/pids/%d/OUTPUTDEFAULT'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/P'   % (lockin.device_id, 0), (rbias + estdevres)/TAgain],
['/%s/pids/%d/I'   % (lockin.device_id, 0), -.1*(rbias + estdevres)/TAgain],
['/%s/pids/%d/D'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/SETPOINT'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/CENTER'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/RANGE'% (lockin.device_id, 0), maxdccurrent*(rbias + estdevres)],
['/%s/pids/%d/CENTER'   % (lockin.device_id, 0), 1],
['/%s/pids/%d/ENABLE'   % (lockin.device_id, 0), 1],

['/%s/sigouts/%d/enables/*' % (lockin.device_id, voltageoutput),0],
['/%s/sigouts/%d/enables/%d'
        % (lockin.device_id, voltageoutput, out_mix_ch), acamp/outputrange],
['/%s/oscs/%d/freq'         % (lockin.device_id, voltageoutput), freq],
['/%s/sigouts/%d/range'     % (lockin.device_id, voltageoutput), outputrange],
['/%s/sigouts/%d/add'       % (lockin.device_id, voltageoutput), 1],
['/%s/sigouts/%d/on'           % (lockin.device_id, voltageoutput), 1],
['/%s/sigouts/%d/enables/%d' % (lockin.device_id, voltageoutput, out_mix_ch),3],

['/%s/AUXOUTS/%d/OUTPUTSELECT' % (lockin.device_id, dccurrentoutput), -1],

['/%s/ZCTRLS/0/TAMP/%d/CURRENTGAIN' % (lockin.device_id, TAchannel), TAgain],
['/%s/ZCTRLS/0/TAMP/%d/DC' % (lockin.device_id, TAchannel), tampdc],
['/%s/ZCTRLS/0/TAMP/%d/VOLTAGEGAIN' % (lockin.device_id, TAchannel), 0],
['/%s/ZCTRLS/0/TAMP/%d/OFFSET' % (lockin.device_id, TAchannel), 0],

]
        lockin.daq.set(exp_setting)
        self.record4pnt = alexsweep.Recorder(self.lockin, 'DEMODS_%d_SAMPLE' %
                                voltagedemod, 'Raw four point voltage')
        self.recordcurrent = alexsweep.Recorder(self.lockin,'DEMODS_%d_SAMPLE'
                                    % currentdemod, 'Raw AC current')
        self.recorddcbias = alexsweep.Recorder(self.lockin,'AUXOUT_%d_VALUE'
                                    % dccurrentoutput , 'Raw DC current bias')
        self.recordleakage = alexsweep.Recorder(self.gate, 'I', 'Gate leakage')
        if gate:
            gate.I_compliance = maxgatecurrent
        self.genericrecorders = [self.record4pnt, self.recordcurrent,
                                        self.recorddcbias, self.recordleakage]
        self.activemeasurement = False

    @property
    def dccurrent(self):
        currentgain = getattr(self.lockin, 'ZCTRLS_0_TAMP_%i_CURRENTGAIN'
                                                            % self.TAchannel )
        return -currentgain*getattr(self.lockin, 'DEMODS_%i_SAMPLE'
                                                    % self.currentinput)['x']

    @dccurrent.setter
    def dccurrent(self, value):
        curval = (self.lockin.PIDS_0_SHIFT
                                    + self.lockin.PIDS_0_CENTER)
        self.lockin.PIDS_0_DEFAULT = curval
        self.lockin.PIDS_0_ENABLE = 0
        self.lockin.PIDS_0_SETPOINT = - getattr(self.lockin,
                'ZCTRLS_1_TAMP_%d_CURRENTGAIN' % self.TAchannel)*getattr(
                                self.lockin, 'ZCTRLS_1_TAMP_%d_VOLTAGEGAIN' %
                                                    self.TAchannel) * value
        self.lockin.PIDS_0_CENTER = value*(self.rbias + self.estdevres)
        self.lockin.PIDS_0_ENABLE = 1
        self.lockin.PIDS_0_DEFAULT = 0

    def largestTimeconstant(self):
        '''
        Returns the larger time constant between the voltage and current
        demods
        '''
        return max([
        getattr(self.lockin, 'DEMODS_%d_TIMECONSTANT' % self.voltagedemod),
        getattr(self.lockin, 'DEMODS_%d_TIMECONSTANT' % self.currentdemod)])

    def setupRvsGate(self, vstart, vstop, numpoints, settle = 5,
                                    acceptableleakage = 2e-9, bidir = True):

        '''
        Sets up a gatesweep. Must have written self.desc before running this.
        '''

        self.RvsGate = alexsweep.Sweep("RvsGate" + self.desc,
                                             saveatend = False, bi = bidir)
        settler = alexsweep.Delayer(settle*self.largestTimeconstant())
        volts = np.linspace(vstart, vstop, numpoints)
        bg = alexsweep.Active(self.gate, "Vout", 'Backgate voltage', volts)
        self.RvsGate.set_points(numpoints)
        incomp = alexsweep.Wait('Ensure backgate current is in compliance',
            self.gate, 'I',np.full(numpoints,0), valence = 0,
            tolerance = acceptableleakage, timetoaccept = .1)

        self.RvsGate.repeaters = ([bg, incomp, settler] +
                                                        self.genericrecorders)

    def setupRvsI(self,istart, istop, numpoints, settle = 5, startupwait = 10,
                                acceptablecurrenterror = 1e-9, bidir = True):
        '''
        Sets up a dc bias sweep. Must have written self.desc before running
        this.
        '''
        self.RvsI = alexsweep.Sweep("RvsI" + self.desc,
                                                saveatend = False, bi = bidir)
        settler = alexsweep.Delayer(settle*self.largestTimeconstant())
        biascurrents = np.linspace(istart, istop, numpoints)
        biases = alexsweep.Active(self, "dccurrent", 'DC Current Bias',
                                                                biascurrents)
        self.RvsI.set_points(numpoints)
        incomp = alexsweep.Wait('Ensure dc current bias is in compliance',
            self, 'dccurrent', biascurrents, valence = 0,
            tolerance = acceptablecurrenterror, timetoaccept = .1)

        self.RvsI.repeaters = ([biases, incomp, settler] +
                                                         self.genericrecorders)

    def __call__(self, n):
        '''
        Runs the active measurement. This is generally reserved for use in
        another alexsweep, if you are just running this measurement use
        .run(). Returns a dictionary with two keys, data and config. Data is
        a dictionary of data, with sweeps data and processed data. Config
        is the configuration of the Zurich and Keithley.
        '''
        if self.activemeasurement in zitransport._measurements:
            measurementobject = getattr(self, self.activemeasurement)
            sweeps_data = measurementobject(n)
        else:
            raise Exception('Unknown active measurement!')

        return sweeps_data
