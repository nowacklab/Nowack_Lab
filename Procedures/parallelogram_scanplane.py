from Nowack_Lab.Utilities.datasaver import Saver
from Nowack_Lab.Instruments.zurich import zurichInstrument
import numpy as np
import time
from numpy import array as array
import os
import contextlib
import subprocess

class para_Scanplane():


    def __init__(self, instruments={}, plane=None, bl = [-400, -400],
                 tl = [-400,400], tr = [400, 400], numpts=[20, 20],
                 scan_height=35, line_time = 10, scan_pause = 1, fast_axis = 'x',
                 toplot = False, name = 'Scanplane', channelstomonitor = {},
                 trigaquired = {}, saveconfig = True, configfile = None):
        '''
        Initializes the scanplane.

        channelstomonitor (dict): keys are names of your invention describing
                                  what DAQ inputs do, values are the hardware
                                  names of those inputs. Ex: {'squid DC': 'ai0'}

        trigaquired(list): [[obj1, {name1: node1, name2:node2}],[obj2, ....]]
                obj# (object): an instrument object with device_id, subscribe,
                                poll, and unsubscribe methods
                name# (string): a name of your own construction, describing the
                                data
                node# (string): the node to be monitored. For SR830's this is
                                ignored and may be anything.
        '''
        pass
        self.instruments = instruments
        self.saver = Saver(name)
        self.channelstomonitor = channelstomonitor
        self.trigaquired = trigaquired
        self.plane = plane
        self.bl=bl
        self.tl=tl
        self.tr=tr
        self.br=[self.bl[0]+self.tr[0]-self.tl[0], self.bl[1]+self.tr[1]-self.tl[1]]
        self.xmin = min(self.bl[0], self.tl[0], self.tr[0], self.br[0])
        self.xmax = max(self.bl[0], self.tl[0], self.tr[0], self.br[0])
        self.ymin = min(self.bl[1], self.tl[1], self.tr[1], self.br[1])
        self.ymax = max(self.bl[1], self.tl[1], self.tr[1], self.br[1])
        self.xrange = [self.xmin, self.xmax]
        self.yrange = [self.ymin, self.ymax]
        self.numpts=numpts
        self.scan_height=scan_height
        self.line_time = line_time
        self.scan_pause =scan_pause
        self.fast_axis = fast_axis
        self.name = name
        self.toplot = toplot
        self.interrupt = False
        self.configfile = configfile
        self.saveconfig = saveconfig

    def setupsave(self):
        '''
        Saves config and creates empty arrays to store data in. If data type is
        unspecified, no array will be created and data will be saved in
        individual datasets for each line.
        '''

        self.saver.append('config/isFinished', [np.nan, np.nan])
        self.saver.append('config/bottomleft', self.bl)
        self.saver.append('config/topleft', self.tl)
        self.saver.append('config/topright', self.tr)
        self.saver.append('config/xrange', self.xrange)
        self.saver.append('config/yrange', self.yrange)
        self.saver.append('config/numpts', self.numpts)
        self.saver.append('config/scan_height', self.scan_height)
        self.saver.append('config/scan_pause', self.scan_pause)
        self.saver.append('config/fast_axis', self.fast_axis)
        planeconfig = {'a' : self.plane.a,'b' : self.plane.b,'c' : self.plane.c}
        self.saver.append('config/plane', planeconfig)
        self.saver.append('config/line_time', self.line_time)
        datashape = self.numpts[::-1]
        if self.configfile:
            self.saver.append('config/configfile', self.configfile)
        for channelname in self.channelstomonitor.keys():
            self.saver.append('/DAQ/'+channelname, np.full(datashape,
                                                            np.float64(np.nan)))
        if self.saveconfig:
            for instrument in self.instruments.keys():
                self.saver.append('config/instruments/%s/' % instrument,
                    self.instruments[instrument].__getstate__())

        for oneinst in self.trigaquired:
            dictofnodes = oneinst[1]
            if not oneinst[0]  in self.instruments.values() and self.saveconfig:
                self.saver.append('config/triginstruments/%s/' %
                              oneinst[0].device_id, oneinst[0].__getstate__())

            for nodename in dictofnodes.keys():
                self.saver.append('config/'+ nodename + '/node',
                                                        dictofnodes[nodename])
                self.saver.append('config/'+ nodename + '/device',
                                                          oneinst[0].device_id)
    def launchplotters(self):
        '''
        Uses OS to launch a plotting kernel in a seperate python thread.
        '''
        if  self.toplot:
            plotargs = ' '
            plotargs = plotargs.join(self.toplot)
            subprocess.Popen('ipython C:/Users/Hemlock/Documents/GitHub/Nowack_Lab/Procedures/'+
                    'alexplotscanplane.py ' + self.saver.datasets['local'].filename
                    + ' ' + plotargs )
            time.sleep(1)

    def _setupplane(self):
        '''
        Calculates X,Y,Z deflections for scanning the plane.

        plane (object): a planefit object

        xrange (2 element list): range of xvalues to scan over

        yrange (2 element list): range of yvalues to scan over

        numpts (2 element list): number of points in X and Y, respectively

        scan_height (float): height to scan at

        Returns:

        A list of lines, where each line is a dictionary  with two elements
        Vstart and Vend. Each of them has three elements, X, Y, Z, with the
        starting and ending voltages (respectively) of each.
        '''
        lines = []
        if self.fast_axis == 'x':
            leftlinex = np.linspace(self.bl[0], self.tl[0], self.numpts[1])
            leftliney = np.linspace(self.bl[1], self.tl[1], self.numpts[1])
            leftlinez = np.linspace(self.plane.plane(self.bl[0], self.bl[1]), self.plane.plane(self.tl[0], self.tl[1]), self.numpts[1])
            rightlinex = np.linspace(self.br[0], self.tr[0], self.numpts[1])
            rightliney = np.linspace(self.br[1], self.tr[1], self.numpts[1])
            rightlinez = np.linspace(self.plane.plane(self.br[0], self.br[1]), self.plane.plane(self.tr[0], self.tr[1]), self.numpts[1])
        elif self.fast_axis == 'y':
            toplinex = np.linspace(self.tl[0], self.tr[0], self.numpts[0])
            topliney = np.linspace(self.tl[1], self.tr[1], self.numpts[0])
            toplinez = np.linspace(self.plane.plane(self.tl[0], self.tl[1]), self.plane.plane(self.tr[0], self.tr[1]), self.numpts[0])
            bottomlinex = np.linspace(self.bl[0], self.br[0], self.numpts[0])
            bottomliney = np.linspace(self.bl[1], self.br[1], self.numpts[0])
            bottomlinez = np.linspace(self.plane.plane(self.bl[0], self.bl[1]), self.plane.plane(self.br[0], self.br[1]), self.numpts[0])
        else:
            raise Exception('Fast axis not recognized')
        for i in range(self.numpts[int(self.fast_axis == 'x')]):
            if self.fast_axis == 'x':
                xstart = leftlinex[i]
                ystart = leftliney[i]
                zstart = leftlinez[i]-self.scan_height
                xend = rightlinex[i]
                yend = rightliney[i]
                zend = rightlinez[i]-self.scan_height
                vstart = {'x': xstart,'y': ystart,'z': zstart}
                vend = {'x': xend,'y': yend,'z': zend}
                lines.append({'Vstart': vstart, 'Vend': vend})
            if self.fast_axis == 'y':
                xstart = toplinex[i]
                ystart = topliney[i]
                zstart = toplinez[i]-self.scan_height
                xend = bottomlinex[i]
                yend = bottomliney[i]
                zend = bottomlinez[i]-self.scan_height
                vstart = {'x': xstart,'y': ystart,'z': zstart}
                vend = {'x': xend,'y': yend,'z': zend}
                lines.append({'Vstart': vstart, 'Vend': vend})

            self.instruments['piezos'].x.check_lim([xstart,xend])
            self.instruments['piezos'].y.check_lim([ystart,yend])
            self.instruments['piezos'].z.check_lim([zstart,zend])

        return lines

    def dictvisititems(self,dictionary, function):
            '''
            Applies function at every node of nested dict. Modifies dictionary by
            reference.
            '''
            def recursivevisit(dictionary, function):
                for key in dictionary.keys():
                    dictionary[key] = function(dictionary[key])
                    if isinstance(dictionary[key], dict):
                        dictionary[key] = recursivevisit(dictionary[key], function)
                return dictionary
            recursivevisit(dictionary, function)

    def replacewithempty(self, dictionary):
        numlines = len(self.lines)
        if isinstance(dictionary, (list, np.ndarray)):
            a = list(np.shape(dictionary))
            a.insert(int(self.fast_axis == 'y'), numlines)
            datashape = tuple(a)
            dictionary = np.full(datashape, np.nan)
        elif isinstance(dictionary, (int,float)):
            dictionary = np.full(numlines, np.nan)
        return dictionary

    def setuptrigsave(self, dataname, data):
        '''
        Adds the empty datastructures to the hdf5 data to store data from the
        triggered instruments. Runs after the first line, because the structure
        of these returns is unknown at the beginning.

        data: polled data from one node (not instrument!).
        '''
        numlines = len(self.lines)
        if isinstance(data, (float, int)):
            self.saver.append(dataname, np.full(numlines, np.nan))
        elif isinstance(data, (np.ndarray, list)):
            a = list(np.shape(dictionary))
            a.insert(int(self.fast_axis == 'y'), numlines)
            datashape = tuple(a)
            self.saver.append(dataname, np.full(datashape, np.nan))
        elif isinstance(data, dict):
            emptydic = data.copy()
            self.dictvisititems(emptydic, self.replacewithempty)
            self.saver.append(dataname, emptydic)
        else:
            raise Exception('Unrecognized data type!')
    def run(self):
        '''
        Runs the scanplane
        '''
        #suppress saving prints
        with open(os.devnull, "w") as f, contextlib.redirect_stdout(f):
            self.setupsave()

        self.lines = self._setupplane()
        for inst in self.trigaquired:
            [obj, attrs] = inst
            for node in attrs.items():
                if (isinstance(obj, zurichInstrument)
                    and  'DEMODS' == node[1][:6]):
                    setattr(obj, node[1][:9]+'TRIGGER',0)
                    setattr(obj, node[1][:9]+'TRIGGER',1)
                    time.sleep(.1)
                obj.subscribe({node[1]:node[0]})
                if (isinstance(obj, zurichInstrument)
                    and  'DEMODS' == node[1][:6]):
                    dump = obj.poll()
        try:
            for i in np.arange(len(self.lines)):
                if self.interrupt:
                    self.saver.append('config/isFinished/', 1, slc = slice(0,1)) #let the plotting kernal know the scan is done
                    print('Interrupted by keystroke')
                    break
                line = self.lines[i]
                if self.fast_axis == 'x':
                    pos = len(self.lines) - i
                    dataslice = slice(pos-1, pos)
                else:
                    pos = i + 1
                    dataslice = (slice(0, self.numpts[1]), slice(pos-1,pos))
                #go to beginning of line

                self.instruments['piezos'].sweep(self.instruments['piezos'].V,
                                                 line['Vstart'])
                self.instruments['squidarray'].reset()
                time.sleep(self.scan_pause)
                output_data, received = self.instruments['piezos'].newsweep(
                            line['Vstart'], line['Vend'], chan_in=
                            list(self.channelstomonitor.values()), numcollect =
                            self.numpts[int(self.fast_axis == 'y')],
                                        linetime = self.line_time, trigger = 'ao3')
                for inputchan in received.keys():
                    for chan in self.channelstomonitor.items():
                        if chan[1] == inputchan:
                            self.saver.append('/DAQ/'+ chan[0], received[inputchan],
                                                                slc = dataslice)
                            break
                for inst in self.trigaquired:
                    [obj, attrs] = inst
                    polleddata = obj.poll()
                    for datakey in polleddata.keys():
                        for name in attrs.keys():
                            if datakey == name:
                                if i == 0: # is this the first loop?
                                    self.setuptrigsave('/%s/' % datakey, polleddata[datakey])
                                self.saver.append('/%s/' % datakey, polleddata[datakey],
                                                           slc = dataslice)
                if i== 0:
                    self.launchplotters()
        except KeyboardInterrupt:
            self.interrupt = True
        for inst in self.trigaquired:
            [obj, attrs] = inst
            for node in attrs.items():
                if (isinstance(obj, zurichInstrument)
                              and  'DEMODS' == node[1][:6]):
                    setattr(obj, node[1][:9]+'TRIGGER',0)
                obj.unsubscribe([node[1]])
        self.instruments['piezos'].z.V = 0
        self.instruments['piezos'].y.V = 0
        self.instruments['piezos'].x.V = 0
        self.saver.append('config/isFinished/', 1, slc = slice(0,1))
