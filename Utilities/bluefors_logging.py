import re
import os
import datetime
import numpy as np
from scipy.optimize import curve_fit
from Nowack_Lab.Utilities import save

def getLog(filename):
    """
        Returns out= [(datetime.datetime obj, float), ...]
        one for each row of the input file filename
    """
    raw = [];
    out = [];
    with open(filename) as f:
        raw = f.readlines();
    for a in raw:
        m = re.search('(\d{2}-\d{2}-\d{2},\d{2}:\d{2}:\d{2},)([\d.eE\-\+]+)', a);
        time = datetime.datetime.strptime(m.group(1), "%d-%m-%y,%H:%M:%S,")
        val = float(m.group(2));
        out.append((time, val));
    return out;

def getClosestVals(filename, times):
    log = getLog(filename);
    vals = [];
    for t in times:
        i = int(len(log)/2);

        ub = len(log)-1; #Upper bound
        lb = 0;          #lower bound
        closest = False;
        for a in range(int(np.ceil(np.log2(len(log))))+1):
            #binary search O(log(n))
            if( np.abs((t-log[i][0]).total_seconds()) < 30 ):
                closest = True;
                break;
            if (ub - lb <= 1):
                closest = True;
                print("no more options" + str(t) + str(log[i][1]));
                break;
            if(t>log[i][0]):
                lb = i;
                i = int(np.round((ub-lb)/2 + lb));
                #print("larger");
            else:
                ub = i;
                i = int(np.round((ub-lb)/2 + lb));
                #print("smaller");
        vals.append(log[i][1]);
        if not closest:
            print("Did not find closest in O(log(n)) time for time "+ str(t));
    return [vals, log];

def getClosestVals_comp(filename1, filename2):
    log1 = getLog(filename1);
    log1times = [entry[0] for entry in log1];
    log1vals  = [entry[1] for entry in log1];
    [log2vals, log] = getClosestVals(filename2, log1times);
    return [log1vals, log2vals];

def thermometercalibration(filename_res, filename_temp, tcutoff=4):
     [rawres, rawtemp]= getClosestVals_comp(filename_res, filename_temp);
     res = [];
     temp = [];

     # remove zero entries
     for i in range(len(rawres)):
         if rawtemp[i] <= tcutoff:
             continue;
         if abs(rawtemp[i]) > 1e-16 and abs(rawres[i]) > 1e-16:
             res.append(rawres[i]);
             temp.append(rawtemp[i]);


     # remove dupes???

     print(len(res));
     print(len(temp));

     # fit
     f = lambda x, a, b: a*x + b;

     [popt, pcov] = curve_fit(f, np.log(res), np.log(temp))

     return [res, temp, f, popt, pcov]

def thermcal(datestr='17-04-10', resname=r'CH7 R ', tempname=r'CH6 T ',
             tcutoff=4, numpts = 200, binsize = 3):
    [res,temp,f,popt,pcov] =  thermometercalibration(
                                os.path.join(save.get_data_server_path(),
                                            'bluefors', 'blueforslogs',
                                            datestr, resname+datestr+'.log'),
                                os.path.join(save.get_data_server_path(),
                                            'bluefors', 'blueforslogs',
                                            datestr, tempname+datestr+'.log'),
                                tcutoff
                            )
    res = np.array(res);
    temp = np.array(temp);
    finv = lambda f: np.exp((np.log(f)-popt[1])/popt[0]);
    newf = lambda res: np.exp(f(np.log(res), *popt));

    newtemp = np.linspace(np.ceil(10*min(temp))/10, np.floor(10*max(temp))/10, 200)

    newres = [];
    for t in newtemp:
        index = np.abs(t-newf(res)).argmin();
        start = max(int(index-binsize/2), 0);
        end   = min(int(abs(index-binsize/2))+binsize, len(res)-1);
        averes = np.mean([res[i] for i in range(start, end)]);
        print("[{},{},{},{}]".format(index,start,end,averes));
        newres.append(averes);

    return [newres, newtemp, finv, newf, res, temp, f, popt, pcov];


def thermometercalibration2(datestr='17-03-03', resname=r'CH7 R ', tempname='CH6 T ', tcutoff=[4,100]):
    rawlog = [];
    for t in [resname, tempname]:
        rawlog.append(getLog(
                        os.path.join(save.get_data_server_path(),
                                    'bluefors', 'blueforslogs',
                                    datestr, t+datestr+'.log')
                    ));

    # remove zero entries
    for i in range(len(rawlog)-1,-1,-1):
        for j in range(len(rawlog[i])-1,-1,-1):
            if abs(rawlog[i][j][1]) < 1e-16:
                del rawlog[i][j];


    rawlogsep = [];
    for i in range(2):
        rawlogsep.append([  [a[0] for a in rawlog[i]],
                            [a[1] for a in rawlog[i]]
                        ]);
    log = [];
    for i in range(2):
        times = [a[0].timestamp() for a in rawlog[i]];
        vals  = [a[1] for a in rawlog[i]];
        log.append([times,vals])

    temps = np.linspace(tcutoff[0],tcutoff[1],200);
    times = np.interp(temps, log[1][1], log[1][0]);
    res   = np.interp(times, log[0][0], log[0][1]);

    f = lambda x,a,b: a*x + b;

    [popt, pcov] = curve_fit(f, np.log(temps), np.log(res));

    return [temps, res, times, f, popt, pcov, log[1], log[0]];



def plotlogs(datestr='17-03-03', extratemps = [r'CH7 T ', r'CH8 T ']):
    #filenamebase = save.get_data_server_path() + r'\bluefors\blueforslogs';

    temperatures = [r'CH1 T ',
                    r'CH2 T ',
                    r'CH5 T ',
                    r'CH6 T '];
    temperatures = temperatures + extratemps;

    rawdatasets = [];

    for t in temperatures:
        thislog = getLog(
            os.path.join(save.get_data_server_path(),
                         'bluefors',
                         'blueforslogs',
                         datestr,
                         t+datestr+'.log')
        );
        rawdatasets.append(thislog);

    datasets = [];

    for dataset in rawdatasets:
        times = [d[0] for d in dataset];
        vals  = [d[1] for d in dataset];
        datasets.append([times,vals]);

    return [datasets, temperatures]
