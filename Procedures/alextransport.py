
from Nowack_Lab.Procedures import alexsweep
import numpy as np
from Nowack_Lab.Utilities.datasaver import Saver
class zitransport():

    _measurements = ['RvsI', 'RvsGate']

    def __init__(self, rbias, lockin, currentinput = 0, dccurrentinput = 0,
                dccurrentoutput = 0, voltageinput = 1,  voltageoutput = 0,
                acamp = .01, TAchannel = 0, voltagerange = 2, currentrange = 2,
                outputrange = 1, TAgain = 1e6, freq = 17.76,
                voltagepreamp = False, voltdiff = False, externalvoltagegain = 1,
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
        self.runnumber = 0
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
['/%s/sigins/%d/diff'        % (lockin.device_id, voltageinput),int(voltdiff)],

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
['/%s/pids/%d/P'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/I'   % (lockin.device_id, 0), -1*(rbias + estdevres)/TAgain],
['/%s/pids/%d/D'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/SETPOINT'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/CENTER'   % (lockin.device_id, 0), 0],
['/%s/pids/%d/RANGE'% (lockin.device_id, 0), maxdccurrent*(rbias + estdevres)],
['/%s/pids/%d/CENTER'   % (lockin.device_id, 0), 1],
['/%s/pids/%d/ENABLE'   % (lockin.device_id, 0), 1],

['/%s/sigouts/%d/enables/*' % (lockin.device_id, voltageoutput),0],
['/%s/sigouts/%d/enables/%d'
        % (lockin.device_id, voltageoutput, out_mix_ch), 1],
['/%s/sigouts/%d/amplitudes/%d'
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
        self.recorddcbias = alexsweep.Recorder(self.lockin,'AUXINS_0_VALUES_%d'
                                    % dccurrentinput , 'Raw DC current bias')

        if gate:
            gate.I_compliance = maxgatecurrent
            self.recordgatevoltage = alexsweep.Recorder(self.gate, 'V',
                                                        'Gate voltage')
            self.recordgateleakage =  alexsweep.Recorder(self.gate,'I',
                                                        'Gate Leakage')
            self.genericrecorders = [self.recordgateleakage,
                    self.recordgatevoltage,self.record4pnt, self.recordcurrent,
                                        self.recorddcbias]
        else:
            self.genericrecorders = [self.record4pnt, self.recordcurrent,
                                        self.recorddcbias]
        self.activemeasurement = False

    @property
    def dccurrent(self):
        currentgain = getattr(self.lockin, 'ZCTRLS_0_TAMP_%i_CURRENTGAIN'
                        % self.TAchannel )*getattr(self.lockin,
                        'ZCTRLS_0_TAMP_%d_VOLTAGEGAIN' % self.TAchannel)
        return getattr(self.lockin, 'AUXINS_0_VALUES_%d'
                                            % self.dccurrentinput)/currentgain

    @dccurrent.setter
    def dccurrent(self, value):
        self.lockin.PIDS_0_CENTER = value*(self.rbias + self.estdevres)
        self.lockin.PIDS_0_SETPOINT = - getattr(self.lockin,
                'ZCTRLS_0_TAMP_%d_CURRENTGAIN' % self.TAchannel)*getattr(
                                self.lockin, 'ZCTRLS_0_TAMP_%d_VOLTAGEGAIN' %
                                                    self.TAchannel) * value


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
        if not self.gate:
            raise Exception('No gate defined!')
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
                                                        self.genericrecorders
                                                        )

    def setupRvsI(self,istart, istop, numpoints, settle = 5,
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
        curtagain = getattr(self.lockin, 'ZCTRLS_0_TAMP_%d_CURRENTGAIN'
                        % self.TAchannel)*getattr(self.lockin,
                        'ZCTRLS_0_TAMP_%d_VOLTAGEGAIN' % self.TAchannel)
        incomp = alexsweep.Wait('Ensure dc current bias is in compliance',
            self, 'dccurrent', -biascurrents, valence = 0,
            tolerance = acceptablecurrenterror, timetoaccept = .1, timeout=30)
        self.incomp = incomp
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
            sweep_data = measurementobject(n)
        else:
            raise Exception('Unknown active measurement!')
        datasvr = Saver(name = self.activemeasurement + self.desc)
        currentgain = getattr(self.lockin, 'ZCTRLS_0_TAMP_%i_CURRENTGAIN'
                        % self.TAchannel )*getattr(self.lockin,
                        'ZCTRLS_0_TAMP_%d_VOLTAGEGAIN' % self.TAchannel)
        self.acsignal = (getattr(self.lockin, 'SIGOUTS_%d_AMPLITUDES_%d'
                % (self.voltageoutput, self.out_mix_ch)) *
                getattr(self.lockin, 'SIGOUTS_%d_RANGE'
                        % self.voltageoutput))/(2.0**.5)
        for point in range(len(sweep_data)):
            sweep_data[point]['AC Two-point resistance (Ohms)'] = (self.acsignal/(
            sweep_data[point]['Raw AC current']['x']/currentgain))
            sweep_data[point]['AC Four-point resistance (Ohms)'] = (
            sweep_data[point]['Raw four point voltage'
            ]['x']/(self.externalvoltagegain*sweep_data[point]['Raw AC current'
            ]['x']/currentgain))
            sweep_data[point]['DC Current (Ampere)'] = (
            sweep_data[point]['Raw DC current bias']/currentgain)
        return sweep_data

    def run(self, plot = True, save = True):
        sweep_data = self.__call__(self.runnumber)
        self.runnumber += 1

        if save:
            datasvr = Saver(name = self.activemeasurement + self.desc)
            datasvr.append('/data/',sweep_data)
            datasvr.append('/setup/lockin/', self.lockin.__getstate__())
            datasvr.append('/setup/params', {
            'rbias': self.rbias,
            'Zurich current input': self.currentinput,
            'Zurich aux dc current input': self.dccurrentinput,
            'Zurich voltage input': self.voltageinput,
            'Zurich Lockin Output': self.voltageoutput,
            'Zurich TA Channel': self.TAchannel,
            'External voltage gain': self.externalvoltagegain,
            'Max DC current': self.maxdccurrent,
            'Max gate voltage': self.maxgate})

        if plot:
            import matplotlib.pyplot as plt
