# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Nowack_Lab
#     language: python
#     name: nowack_lab
# ---

from Nowack_Lab.Utilities import multih5
import numpy as np
from os.path import basename
import time
import yaml

# ## Measurement and saving

import Nowack_Lab.Instruments.zurich as zurich
zi = zurich.HF2LI1(server_port=8004, device_serial='HF2-DEV505')
instruments = {
    'zurich': zi,
}

# ## Zurich setup

from datetime import datetime
import time
import zhinst

daq = zhinst.ziPython.ziDAQServer('127.0.0.1', 8005, 1)

ziid = 'dev505'
freq = 1e3 # Hz
timeconstant = 0.00692291283
several = 10
datarate = 449.73273
clockbase = daq.getInt(f'/{ziid}/clockbase')

# +
# May need to change `ziPython` to `core`
daq.setInt(f'/{ziid}/sigouts/*/on', 0)
daq.setDouble(f'/{ziid}/sigouts/0/offset', 0)
daq.setDouble(f'/{ziid}/sigouts/0/range', 1.0)

daq.setDouble(f'/{ziid}/sigins/0/range', 0.586)
daq.setDouble(f'/{ziid}/sigins/0/ac', False)
daq.setDouble(f'/{ziid}/sigins/0/imp50', False)
daq.setDouble(f'/{ziid}/sigins/0/diff', True)

daq.setDouble(f'/{ziid}/sigins/1/range', 0.901)
daq.setDouble(f'/{ziid}/sigins/1/ac', False)
daq.setDouble(f'/{ziid}/sigins/1/imp50', False)
daq.setDouble(f'/{ziid}/sigins/1/diff', True)

daq.setDouble(f'/{ziid}/oscs/0/freq', freq)

daq.setInt(f'/{ziid}/demods/0/adcselect', 0)
daq.setInt(f'/{ziid}/demods/1/adcselect', 1)
daq.setInt(f'/{ziid}/demods/*/enable', 0)
daq.setInt(f'/{ziid}/demods/0/enable', 1)
daq.setInt(f'/{ziid}/demods/1/enable', 1)

daq.setDouble(f'/{ziid}/demods/*/timeconstant', timeconstant)
daq.setDouble(f'/{ziid}/demods/*/order', 4)
daq.setDouble(f'/{ziid}/demods/*/rate', datarate)
# -

# AC transport

daq.setDouble(f'/{ziid}/sigouts/0/range', 10.0)
daq.setDouble(f'/{ziid}/sigouts/0/amplitudes/0', 0.195) # x10V
daq.setInt(f'/{ziid}/sigouts/0/enables/*', 0)
daq.setInt(f'/{ziid}/sigouts/0/enables/0', 1)
daq.setInt(f'/{ziid}/sigouts/0/on', 1)


def daqpoll():
    # If the wait is only one timeconstant, then the second demod is omitted.
    # Given python delays, there should always be data after
    # one timeconstant and then some.
    return daq.poll(
        recording_time_s = several * timeconstant,
        timeout_ms = 500,
        flags = 0
    )


def initmeasurement():
    daq.unsubscribe('*')
    time.sleep(10 * several * timeconstant)
    daq.sync()
    beforelocaltime = datetime.now()
    # Subscribing together means that the timestamps are more
    # likely to be together.
    # That is, the data indices correspond to the same timestamps
    # between arrays and demods.
    # This is not exact, so the arrays still have to be shifted
    # to align correctly.
    daq.subscribe([
        f'/{ziid}/demods/0/sample',
        f'/{ziid}/demods/1/sample',
    ])
    data = daqpoll()
    afterlocaltime = datetime.now()

    timestamp0 = data[ziid]['demods']['0']['sample']['timestamp'][0]
    
    return data, (beforelocaltime, afterlocaltime, timestamp0)


# ## Saving

# For now, metadata must not have nested objects
metadata = yaml.safe_load('''
name: PPMS AC resistance measurement
author name: Alex Striff
author email: abs299@cornell.edu
description: >
  Resistance vs temperature
  measured with a Zurich HF2LI lock-in amplifier.
format: >
  Dataset dimension label <x> is the sweep of scales/<x>.
  Units are given in the 'unit' attribute.
''')


def add_scale(f, name, unit, x):
    path = 'scales/{}'.format(name)
    f[path] = x
    f[path].attrs['unit'] = unit
    return x


def h5_dict(group, d):
    for k, v in d.items():
        if type(v) is dict:
            h5_dict(group.create_group(k), v)
        else:
            group[k] = v


# +
initdata, inittimes = initmeasurement()
beforelocaltime, afterlocaltime, timestamp0 = inittimes

abstime_uncertainty = afterlocaltime - beforelocaltime
abstime_uncertainty_us = abstime_uncertainty.microseconds
abstime = beforelocaltime + 0.5*abstime_uncertainty
abstime_str = f'{abstime.isoformat()} ± {abstime_uncertainty_us} μs'

metadata['start_time'] = abstime_str

filenames = []
with multih5.Files('PPMS-AC-resistance', 'w',
                   libver = 'latest',
                  ) as fs:
    for f in fs[0:1]: # TODO: Fix for multiple files
        filenames.append(f.filename)
        print(f.filename)
        
        # Write metadata
        for k, v in metadata.items():
            f.attrs[k] = v
        
        zisettings = daq.get('*', settingsonly=True, flat=False)
        zigroup = f.create_group('zurich')
        h5_dict(zigroup, zisettings)
        zigroup['initial_timestamp'] = timestamp0
        zigroup[f'{ziid}/clockbase'] = daq.getInt(f'/{ziid}/clockbase')
        
        setupgroup = f.create_group('setup')
        setupgroup['bias_resistance'] = 75.1e3
        
        # Set up dataset structure
        demod_ns = ['0', '1']
        sample_keys = [
            'timestamp', 'x', 'y', 'frequency',
            'phase', 'dio', 'trigger', 'auxin0', 'auxin1',
        ]
        demods = [f.create_group(f'/data/zurich/{ziid}/demods/{n}/sample') for n in demod_ns]
        for demod, n in zip(demods, demod_ns):
            for key in sample_keys:
                example = initdata[ziid]['demods'][n]['sample'][key]
                demod.create_dataset(
                    key,
                    example.shape,
                    maxshape = (None,) * example.ndim, # Resizable up to HDF5 per-axis limit of 2**64 elements
                    dtype = example.dtype
                )
        
        # After creating datasets
        f.swmr_mode = True
        
        # Save data and extend arrays
        endindices = np.zeros(shape = (len(demods), len(sample_keys)), dtype = int)
        
        print("Taking data.")
        while True:
            data = daqpoll()
            for i, (demod, n) in enumerate(zip(demods, demod_ns)):
                for j, key in enumerate(sample_keys):
                    y = demod[key]
                    end = endindices[i, j]
                    x = data[ziid]['demods'][n]['sample'][key]
                    newend = end + len(x)
                    if len(y) - end <= len(x):
                        y.resize(end + len(x), axis = 0)
                    y[end:newend] = x
                    y.flush()
                    endindices[i, j] = newend
