from Nowack_Lab.Utilities.datasaver import Saver
import time
from numpy import array as array
import ast
from scipy.interpolate import interp1d
from ..Utilities.save import Measurement

class strain(Measurement):
    '''
    Control the strain put out by the strain cell.
    '''
    def __init__(self, instruments = {}, temp = 0, cap = 0, strain = 0):
        '''
        Initializes the strain controller.
        
        temp (float), cap (float), strain (float): temperature, capacitance and strain value (in um) at one moment used to calculate capacitance offset.
        '''
        self.drt = 8.85418781*5.24/(1.24-0.15)
        with open(r'C:\Users\Hemlock\Documents\GitHub\Nowack_Lab\Procedures\razorbill_capacitor_vs_temp.txt', 'r') as f:
            a = f.read()
        a = ast.literal_eval(a)
        c0_calib = 1.24-0.15+a['capacitance'][0]
        a['d0'] = [8.85418781*5.24/(c-c0_calib) for c in a['capacitance']]
        self.ttod0 = interp1d(a['temp'][::-1], a['d0'][::-1], bounds_error=False, fill_value = (a['d0'][-1], a['d0'][0]))
        self.c0 = cap-8.85418781*5.24/(strain+self.ttod0(temp))
        self.instruments = instruments
        self.cb = self.instruments['cb']
        self.razorbill = self.instruments['razorbill']
        self.montana = self.instruments['montana']
        self.razorbill.output = 1


    def update_c0(self, cap, strain, temp):
        '''
        Update the capacitance offset using new values of capacitance, strain and temperature
        '''
        self.c0 = cap-8.85418781*5.24/(strain+self.ttod0(temp))
    
    
    def captostrain(self, cap, c0, d0):
        '''
        Covert capacitance to strain.
        '''
        return 8.85418781*5.24/(cap-c0)-d0
    
    
    def straintocap(self, strain, c0, d0):
        '''
        Convert strain to anticipated capacitance value. Positive for tension strain.
        '''
        return 8.85418781*5.24/(strain+d0)+c0
    
    
    def getc(self):
        '''
        Measure capacitance. Try to read five times in case GPIB throw random errors.
        '''
        try:
            cnow = self.cb.single
            return cnow
        except:
            time.sleep(2)
            try:
                cnow = self.cb.single
                return cnow
            except:
                time.sleep(2)
                try:
                    cnow = self.cb.single
                    return cnow
                except:
                    time.sleep(2)
                    try:
                        cnow = self.cb.single
                        return cnow
                    except:
                        time.sleep(2)
                        try:
                            cnow = self.cb.single
                            return cnow
                        except:
                            print('Cannot read capacitance from capacitance bridge. Check connection!')
    
    
    def currentstrain(self):
        '''
        Return the current strain.
        '''
        cnow = self.getc()
        return self.captostrain(cnow, self.c0, self.ttod0(self.montana.temperature['platform']))
    
    
    def moveonevolt(self, cnow, cto, upperV, lowerV):
        '''
        Return new output values for the two piezo stacks.
        Change one volt towards the desired strain. This function
        will calculate which piezo stack should be changed based
        on their current voltage and maximum allowed voltage, and
        change it by one volt.
        
        cnow (float): current capacitance
        cto (float): desired capacitance
        upperV (float): upper bound of piezo voltage calculated by checkV function of razorbill
        lowerV (float): lower bound of piezo voltage calculated by checkV function of razorbill
        '''
        Vc = self.razorbill.Vcompression
        Vt = self.razorbill.Vtension
        if cnow<cto:
            if Vc>=0:
                if (Vc/upperV)<=(Vt/lowerV):
                    Vc = round(Vc)+1
                else:
                    Vt = round(Vt)-1
            else:
                if (Vc/lowerV)<=(Vt/upperV):
                    Vt = round(Vt)-1
                else:
                    Vc = round(Vc)+1
        if cnow>cto:
            if Vt>=0:
                if (Vt/upperV)<=(Vc/lowerV):
                    Vt = round(Vt)+1
                else:
                    Vc = round(Vc)-1
            else:
                if (Vt/lowerV)<=(Vc/upperV):
                    Vc = round(Vc)-1
                else:
                    Vt = round(Vt)+1
        return Vc, Vt
    
    
    def setstrain(self, strainto):
        '''
        Set strain. Move piezos by one volt each time until capacitance is within a threshold
        of 0.002pF or the measured capacitance changes to the other side of the desired capacitance.
        
        strainto (float): desired strain in um, positive for tension strain.
        '''
        cto = self.straintocap(strainto, self.c0, self.ttod0(self.montana.temperature['platform']))
        Vc = self.razorbill.Vcompression
        Vt = self.razorbill.Vtension
        upperV = self.razorbill.checkV(200)
        lowerV = self.razorbill.checkV(-200)
        threshold = 0.002
        n = 0
        cnow = self.getc()
        while n<400:
            diff = cnow-cto
            cnow = self.getc()
            if diff*(cnow-cto)<0:
                self.razorbill.Vcompression = Vc
                self.razorbill.Vtension = Vt
                time.sleep(1)
                break
            elif abs(cnow-cto)<threshold:
                break
            else:
                Vc, Vt = self.moveonevolt(cnow, cto, upperV, lowerV)
                self.razorbill.Vcompression = Vc
                self.razorbill.Vtension = Vt
                print(Vc, Vt)
                time.sleep(1)
            n = n+1
    
    
    def keepstrain(self, t, strainto):
        '''
        Change the strain. Then keep the strain at the value for a user defined time period.
        This function is used to stablize the strain when piezo stacks creep.
        '''
        self.setstrain(strainto)
        t0 = time.time()
        while time.time()-t0<t:
            self.setstrain(strainto)
            time.sleep(5)
    
    
    def keepstrainrecording(self, temp_threshold, strainto, period, channelstomonitor, otheraquired, name):
        '''
        Keep strain at one value while changing temperature. This function also allows to record data during the process.
        
        temp_threshold (float): lower bound threshold temperature to stop the function. The capacitance
        should not change much with temperature below the threshold and/or the cryostat temperature
        changes too fast below the threshold, making the capacitance measurement inaccurate.
        
        strainto (float): strain value to maintain in um.
        period (float): period for data recording.
        channelstomonitor (float): DAQ channels to monitor.
        otheraquired (float): other instruments to monitor.
        '''
        self.saver = Saver(name)
        self.channelstomonitor = channelstomonitor
        self.otheraquired = otheraquired
        self.interrupt = False
        
        self.setupsave()
        t0 = time.time()
        timecount = 0
        for inst in self.otheraquired:
            [obj, attrs] = inst
            for node in attrs.items():
                data = obj.node[1]
                self.saver.append('/'+str(node[0])+'/', data)
        for node in self.channelstomonitor.items():
            data = self.instruments['daq'].node[1]
            self.saver.append('/DAQ/'+str(node[0])+'/', data)
        self.saver.append('/Razorbill/tension_set/', array([self.razorbill.Vtension]))
        self.saver.append('/Razorbill/compression_set/', array([self.razorbill.Vcompression]))
        self.saver.append('/Razorbill/tension/', array([self.razorbill.Vtension_measured]))
        self.saver.append('/Razorbill/compression/', array([self.razorbill.Vcompression_measured]))
        capacitance = self.getc()
        self.saver.append('/capacitance/', array([capacitance]))
        self.saver.append('/temperature/', array([self.montana.temperature['platform']]))
        self.saver.append('/time/', array([time.time()-t0]))
        while self.montana.temperature['platform']>temp_threshold:
            timecount = timecount+1
            self.setstrain(strainto)
            while timecount*period>time.time()-t0:
                time.sleep(1)
            for inst in self.otheraquired:
                [obj, attrs] = inst
                for node in attrs.items():
                    data = obj.node[1]
                    self.saver.resize_append('/'+str(node[0])+'/', data)
            for node in self.channelstomonitor.items():
                data = self.instruments['daq'].node[1]
                self.saver.resize_append('/DAQ/'+str(node[0])+'/', data)
            self.saver.resize_append('/Razorbill/tension_set/', array([self.razorbill.Vtension]))
            self.saver.resize_append('/Razorbill/compression_set/', array([self.razorbill.Vcompression]))
            self.saver.resize_append('/Razorbill/tension/', array([self.razorbill.Vtension_measured]))
            self.saver.resize_append('/Razorbill/compression/', array([self.razorbill.Vcompression_measured]))
            capacitance = self.getc()
            self.saver.resize_append('/capacitance/', array([capacitance]))
            self.saver.resize_append('/temperature/', array([self.montana.temperature['platform']]))
            self.saver.resize_append('/time/', array([time.time()-t0]))
    
    
    def setupsave(self):
        '''
        Saves config for function keepstrainrecording.
        '''
        for instrument in self.instruments.keys():
            self.saver.append('config/instruments/%s/' % instrument,
                self.instruments[instrument].__getstate__())

        for oneinst in self.otheraquired:
            dictofnodes = oneinst[1]
            if not oneinst[0]  in self.instruments.values():
                self.saver.append('config/triginstruments/%s/' %
                              oneinst[0].device_id, oneinst[0].__getstate__())

            for nodename in dictofnodes.keys():
                self.saver.append('config/'+ nodename + '/node',
                                                        dictofnodes[nodename])
                self.saver.append('config/'+ nodename + '/device',
                                                          oneinst[0].device_id)        