from Nowack_Lab.Utilities.datasaver import Saver
import numpy as np
import time

class Scanplane():


    def __init__(self, instruments={}, plane=None, xrange=[-400, 400],
                 yrange = [-400,400], numpts=[20, 20],
                 scan_height=35, line_time = 10, scan_pause = 1, fast_axis = 'x',
                 name = 'Scanplane', channelstomonitor = {}, trigaquired = {}):
        '''
        Initializes the scanplane.

        channelstomonitor (dict): keys are names of your invention describing
                                  what DAQ inputs do, values are the hardware
                                  names of those inputs. Ex: {'squid DC': 'ai0'}

        trigaquired(list): [[obj1, {name1: {'node': node2, 'dtype': dtype1},
                                        name2:{'node':....}}], [obj2, ....]]
                obj# (object): an instrument object with device_id, subscribe,
                                poll, and unsubscribe methods
                name# (string): a name of your own construction, describing the
                                data
                dtype#:  can be:
                                    'float': each trigger returns a single
                                            number. Polls return 1D arrays.
                                            Data saved as 2D arrays
                                    an int: each trigger returns a 1D array.
                                            int is the length of that array.
                                            Polls return 2D arrays. Data
                                            saved as 3D array.
                                    'dict': each trigger returns a dict. Polls
                                            return a dict. These will not
                                            be converted into an array.
        '''
        pass
        self.instruments = instruments
        self.saver = Saver(name)
        self.channelstomonitor = channelstomonitor
        self.trigaquired = trigaquired
        self.plane = plane
        self.xrange=xrange
        self.yrange=yrange
        self.numpts=numpts
        self.scan_height=scan_height
        self.line_time = line_time
        self.scan_pause =scan_pause
        self.fast_axis = fast_axis
        self.name = name

    def setupsave(self):
        '''
        Saves config and creates empty arrays to store data in. If data type is
        unspecified, no array will be created and data will be saved in
        individual datasets for each line.
        '''

        self.saver.append('config/xrange', self.xrange)
        self.saver.append('config/yrange', self.yrange)
        self.saver.append('config/numpts', self.numpts)
        self.saver.append('config/scan_height', self.scan_height)
        self.saver.append('config/scan_pause', self.scan_pause)
        self.saver.append('config/fast_axis', self.fast_axis)
        if self.fast_axis == 'x':
            datashape = self.numpts[::-1]
        else:
            datashape = self.numpts
        for channelname in self.channelstomonitor.keys():
            self.saver.append('DAQ_'+channelname, np.full(datashape,
                                                            np.float64(np.nan)))
        for oneinst in self.trigaquired:
            dictofnodes = oneinst[1]
            self.saver.append('config/triginstruments/%s/' %
                              oneinst[0].device_id, oneinst[0].__getstate__())
            for nodename in dictofnodes.keys():
                thisnode = dictofnodes[nodename]
                self.saver.append('config/'+ nodename + '/node',
                                                            thisnode['node'])
                self.saver.append('config/'+ nodename + '/device',
                                                          oneinst[0].device_id)
                if thisnode['dtype'] == 'float':
                    self.saver.append(nodename, np.full(datashape,
                                                            np.float64(np.nan)))
                elif isinstance(thisnode['dtype'], int):
                    thisdatashape = datashape.copy()
                    thisdatashape.append(thisnode['dtype'])
                    self.saver.append(nodename, np.full(
                        thisdatashape,np.float64(np.nan)))
        for instrument in self.instruments.keys():
            self.saver.append('config/instruments/%s/' % instrument,
                self.instruments[instrument].__getstate__())


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
        xstep = (self.xrange[1]-self.xrange[0])/self.numpts[0]
        ystep = (self.yrange[1]-self.yrange[0])/self.numpts[1]
        lines = []
        for i in range(self.numpts[int(self.fast_axis == 'x')]):
            if self.fast_axis == 'x':
                xstart = self.xrange[0]
                ystart = self.yrange[0]+ystep*i
                xend = self.xrange[1]
                yend = self.yrange[0]+ystep*i
                zend = self.plane.plane(xend, yend)
            elif fast_axis == 'y':
                xstart = self.xrange[0]+xstep*i
                ystart = self.yrange[0]
                xend = self.xrange[0]+xstep*i
                yend = self.yrange[1]
            else:
                raise Exception('Fast axis not recognized')
            zstart = self.plane.plane(xstart,ystart) - self.scan_height
            zend = self.plane.plane(xend, yend) - self.scan_height
            vstart = {'x': xstart,'y': ystart,'z': zstart}
            vend = {'x': xend,'y': yend,'z': zend}
            lines.append({'Vstart': vstart, 'Vend': vend})

            self.instruments['piezos'].x.check_lim([xstart,xend])
            self.instruments['piezos'].y.check_lim([ystart,yend])
            self.instruments['piezos'].z.check_lim([zstart,zend])

        return lines



    def run(self):
        '''
        Runs the scanplane
        '''
        self.setupsave()

        lines = self._setupplane()

        for inst in self.trigaquired:
            [obj, attrs] = inst
            for node in attrs.items():
                obj.subscribe({node[1]['node']:node[0]})
        for i in np.arange(len(lines)):
            line = lines[i]
            #go to beginning of line
            self.instruments['piezos'].sweep(self.instruments['piezos'].V,
                                             line['Vstart'])
            time.sleep(self.scan_pause)
            output_data, received = self.instruments['piezos'].newsweep(
                        line['Vstart'], line['Vend'], chan_in=
                        list(self.channelstomonitor.values()), numcollect =
                        self.numpts[int(self.fast_axis == 'y')],
                                    linetime = self.line_time, trigger = 'ao3')
            for inputchan in received.keys():
                for chan in self.channelstomonitor.items():
                    if chan[1] == inputchan:
                        self.saver.append('DAQ_'+ chan[0], received[inputchan],
                                                            slc = slice(i, i+1))
                        break
            for inst in self.trigaquired:
                [obj, attrs] = inst
                polleddata = obj.poll()
                for datakey in polleddata.keys():
                    for name in attrs.keys():
                        if datakey == name:
                            if (attrs[name]['dtype'] == 'float' or
                                isinstance(attrs[name]['dtype'], int)):
                                self.saver.append(name, polleddata[datakey],
                                                            slc = slice(i, i+1))
                            else:
                                self.saver.append(name + '/Line_' + str(i),
                                                            polleddata[datakey])
        for inst in self.trigaquired:
            [obj, attrs] = inst
            for node in attrs.items():
                obj.unsubscribe([node[1]['node']])
