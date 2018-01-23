# Nowack Lab Measurement Code

http://www.nowack.lassp.cornell.edu/

Python code package for measurements done in the Nowack lab at Cornell.

## Getting Started

### Requirements

Anaconda, Python 3

### Installing

Download the repository and run `python runme.py`.
This will install most required packages using pip.
Other packages that require manual installation include:
- ziPython (https://www.zhinst.com/downloads)
- NI DAQmx (http://sine.ni.com/nips/cds/view/p/lang/en/nid/10181)
- PyANC350 (https://github.com/nowacklab/PyANC350)

Installation is non-standard because the package is under constant development.
The normal mode of operation is to make edits to the local GitHub repository containing this package and always run from that version of the code.
`runme.py` will add this directory to the PYTHONPATH and enable import via `import Nowack_Lab`.
This import command runs a setup script, which can be tailored to each user.

#### Explanation of some Utilities installed by `runme.py`

##### github.pth
To allow Anaconda to import the package, we create a `github.pth` file in the Anaconda site-packages directory (C:\Anaconda3\Lib\site-packages\), containing the path to the GitHub directory (e.g. C:\Users\Hemlock\Documents\GitHub).

##### custom.css
Adds a some padding to the bottom of the jupyter notebook.

### Basic structure of Measurements

There are two main types of objects used in this package: `Instrument` and `Measurement`.

An `Instrument` is an object with methods (mainly in the form of [properties](http://stackabuse.com/python-properties/ "Looks like a decent resource, but I didn't read it thoroughly")) that handle all communication with the instrument.
For example, to read and to change the time constant on an SR830 lock-in amplifier:
```
from Nowack_Lab import *

lockin = SR830(3)  # 3 == GPIB address
lockin.frequency  # property that communicates with SR830 and returns frequency in Hz
>> 123
lockin.frequency = 456  # property that communicates with SR830 and sets frequency in Hz
lockin.frequency
>> 456
```

A `Measurement` is an object that accepts a dictionary of many different `Instrument` objects and, when it is `run()`, executes a series of commands sent to each `Instrument`. The `Measurement` will plot the results using `matplotlib` and save data using both the JSON and HDF5 formats. Specifically, the JSON file contains all information pertinent to the setup of the `Measurement`, as well as the status of all `Instruments` involved in the measurement at the time of saving. The HDF5 compresses large `numpy` arrays into a compact file size. Loading is nearly instantaneous with the `Measurement.load` command, restoring the `Measurement` object to the state it was in at the time of saving, enabling quick and easy replotting of the collected data (but no control over the `Instruments`).

The basic construction of a `Measurement` is illustrated below, in which we plot the magnitude of the signal from an SR830 lock-in amplifier versus time:
```
import Nowack_Lab
import time

class BasicMeasurement(Measurement):
    instrument_list = ['lockin']

    def __init__(self, instruments={}, t=60, delay=1):
        '''
        A basic measurement to record lockin signal versus time.

        Arguments:
        instruments (dict) - dictionary of instrument objects
        t (float) - total time to monitor lockin (s)
        delay (float) - delay (s)
        '''
        super().__init__(instruments=instruments)  # implicitly adds all instruments as attributes
        self.t = t
        self.delay = delay

        self.V = np.array([])

    def do(self):
        '''
        Do the measurement without saving.
        We do not normally call do(); it is called within run().
        '''
        tstart = time.time()
        while time.time()-tstart < self.t:
            self.V = np.append(self.V, self.lockin.R)
            time.sleep(self.delay)

```
To run this measurement, we execute the following:
```
lockin = SR830(3)
instruments = {
    'lockin': lockin
}

m = BasicMeasurement(instruments, t=30)
m.run()
```
Note that we use the `run()` command, because it contains commands always run before and after the `do()`, and because it places the `do()` in a safely-keyboard-interruptable try-except block.

For this basic example, we will see no output for 30 seconds, and then the program will terminate.
The data will be saved locally, and you can now interact with the object (in this example, examine the `m.V` array).
In most of our `Measurement`s, we have implemented live plotting.
We normally run in a Jupyter kernel, and each `Measurement` hangs up the kernel.
We are looking into ways to free up the kernel by having the `Measurements` run in the background.

### More information

Under construction...

Will include information and guidelines regarding:
* Save directory structure
* Creating new instruments and measurements
* And more...

## Authors

* Matt Ferguson - [GitHub](https://github.com/gmf57)
* Alex Jarjour - [GitHub](https://github.com/abj46)
* David Low - [GitHub](https://github.com/davidlow)
* Katja Nowack - [GitHub](https://github.com/knowack), [External Website](https://katjanowack.wordpress.com/)
* Guen Prawiroatmodjo - [GitHub](https://github.com/guenp), [External Website](https://www.rigetti.com/)
* Rachel Resnick
* Brian Schaefer - [GitHub](https://github.com/physinet)

## Other packages we like

* [PyMeasure](https://github.com/ralph-group/pymeasure)
* [Instrumental](https://github.com/mabuchilab/Instrumental)
* [PyQDInstrument](https://github.com/guenp/PyQDInstrument)
